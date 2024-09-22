import time
from flask import Flask, render_template, jsonify, request
import paramiko
import socket
import threading
import logging
import os
from datetime import datetime
from time import sleep
import csv

app = Flask(__name__)

# Setup detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SSH configuration for RPIs
USERNAME = "root"
PASSWORD = "root"
SSH_PORT = 22
rpi_hostnames = ["rpi1.local", "rpi2.local"]  # All RPIs

test_running = False  # Global flag for test status
DATA_COLUMNS = [
    "Date", "Time", "RPI", "Core Voltage", "CPU Temp", "CPU Frequency (MHz)",
    "Load Average", "Memory Usage", "Throttled Status", "Test Stage"
]

# Initialize a thread lock for graph_data
graph_data_lock = threading.Lock()
graph_data = []  # Collect all metrics here for graph display
MAX_GRAPH_DATA = 1000  # Maximum number of entries to store

def run_ssh_command(hostname, command):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=SSH_PORT, username=USERNAME, password=PASSWORD, timeout=5)
        stdin, stdout, stderr = client.exec_command(command)
        result = stdout.read().decode().strip()
        client.close()
        return result
    except Exception as e:
        logging.error(f"Error connecting to {hostname}: {e}")
        return None

# Collect metrics from RPI
def collect_metrics_rpi(hostname):
    core_voltage = run_ssh_command(hostname, "vcgencmd measure_volts core")
    core_voltage = core_voltage.split('=')[1].replace('V', '') if core_voltage else 'N/A'

    cpu_temp = run_ssh_command(hostname, "vcgencmd measure_temp")
    cpu_temp = cpu_temp.split('=')[1].replace("'C", "") if cpu_temp else 'N/A'

    cpu_freq = run_ssh_command(hostname, "vcgencmd measure_clock arm")
    cpu_freq = cpu_freq.split('=')[1] if cpu_freq else 'N/A'

    load_average = run_ssh_command(hostname, "cat /proc/loadavg")
    load_average = load_average.split()[0] if load_average else 'N/A'

    memory_usage = run_ssh_command(hostname, "free -m")
    memory_usage = memory_usage.splitlines()[1].split()[2] + "MB" if memory_usage else 'N/A'

    throttled_status = run_ssh_command(hostname, "vcgencmd get_throttled")
    throttled_status = throttled_status.split('=')[1] if throttled_status else 'N/A'

    return {
        "core_voltage": core_voltage,
        "cpu_temp": cpu_temp,
        "cpu_freq": cpu_freq,
        "load_average": load_average,
        "memory_usage": memory_usage,
        "throttled_status": throttled_status
    }

# Thread to run stress tests on RPI
def run_stress_test_rpi(hostname, stress_test_duration_seconds):
    try:
        run_ssh_command(hostname, f"stress-ng --cpu 4 --timeout {stress_test_duration_seconds}s")
    except Exception as e:
        logging.error(f"Error running stress test on {hostname}: {e}")

# Logging system parameters and saving to the output file
def log_system_parameters_to_csv(rpi_metrics, output_file, test_stage):
    global graph_data
    current_time = datetime.now()
    with open(output_file, 'a', newline='') as file:
        csv_writer = csv.writer(file)
        for rpi, metrics in rpi_metrics.items():
            row = [
                current_time.strftime("%Y-%m-%d"),
                current_time.strftime("%H:%M:%S"),
                rpi,
                metrics['core_voltage'],
                metrics['cpu_temp'],
                metrics['cpu_freq'],
                metrics['load_average'],
                metrics['memory_usage'],
                metrics['throttled_status'],
                test_stage
            ]
            csv_writer.writerow(row)
    # Append to graph data with thread safety
    with graph_data_lock:
        graph_entry = {"time": current_time.strftime("%H:%M:%S")}
        for rpi, metrics in rpi_metrics.items():
            graph_entry[rpi] = {
                "cpu_temp": metrics['cpu_temp'],
                "cpu_freq": metrics['cpu_freq'],
                "core_voltage": metrics['core_voltage'],
                "load_average": metrics['load_average']
            }
        graph_data.append(graph_entry)
        if len(graph_data) > MAX_GRAPH_DATA:
            graph_data.pop(0)

# Run stress tests for all RPIs and collect data at intervals
def run_stress_tests(duration_hours, log_frequency_seconds, save_path):
    global test_running
    test_running = True

    stress_test_duration_seconds = duration_hours * 3600  # Convert to seconds
    interval_seconds = log_frequency_seconds
    total_duration = duration_hours * 3600  # Convert hours to seconds
    end_time = time.time() + total_duration

    output_file = os.path.join(save_path, f"stress_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    # Write the header for the CSV file
    with open(output_file, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(DATA_COLUMNS)

    logging.info("Starting the stress test and logging system metrics")

    # Start stress tests on each RPI in parallel
    threads = []
    for hostname in rpi_hostnames:
        thread = threading.Thread(target=run_stress_test_rpi, args=(hostname, stress_test_duration_seconds))
        threads.append(thread)
        thread.start()

    while time.time() < end_time and test_running:
        rpi_metrics = {}
        for hostname in rpi_hostnames:
            rpi_metrics[hostname] = collect_metrics_rpi(hostname)

        # Log the metrics to the CSV file
        log_system_parameters_to_csv(rpi_metrics, output_file, "Stress Test")
        
        # Sleep until the next logging interval
        sleep(interval_seconds)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    logging.info(f"Stress test completed. Results saved to {output_file}")
    return output_file

@app.route('/')
def index():
    return render_template('index.html', active_rpis=rpi_hostnames)

@app.route('/run_tests', methods=['POST'])
def run_tests():
    global test_running
    test_running = True

    try:
        duration_hours = float(request.form.get('duration'))
        log_frequency_seconds = float(request.form.get('log_frequency', 60))
        save_path = request.form.get('save_path') or os.getcwd()  # Default to current directory
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid input parameters."}), 400

    # Run stress tests for all RPIs and collect data in a separate thread
    threading.Thread(target=run_stress_tests, args=(duration_hours, log_frequency_seconds, save_path)).start()
    
    return jsonify({"status": "success", "message": "Stress tests started."})

@app.route('/stop_test', methods=['POST'])
def stop_test():
    global test_running
    test_running = False
    return jsonify({"status": "success", "message": "Test stopped successfully"})

# Collect data for graph display
@app.route('/live_metrics', methods=['GET'])
def live_metrics():
    with graph_data_lock:
        if graph_data:
            return jsonify(graph_data[-1])  # Single entry with time and all RPIs
        else:
            return jsonify({"error": "No metrics available yet"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
