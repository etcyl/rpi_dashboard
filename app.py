import time
from flask import Flask, render_template, jsonify, request
import paramiko
import socket
import threading
import logging
from pathlib import Path
from datetime import datetime
from time import sleep
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

# Setup detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SSH configuration for RPIs
USERNAME = "fleetroot"
PASSWORD = "root"
SSH_PORT = 22

# Dynamically discover RPIs
MAX_RPIS = 20  # Maximum number of RPIs to discover
RPI_NAME_PREFIX = "rpi"  # Prefix for RPI hostnames
DOMAIN_SUFFIX = ".local"  # Domain suffix

rpi_hostnames = []  # Dynamic list of discovered RPIs

test_running = False  # Global flag for test status
DATA_COLUMNS = [
    "Date", "Time", "RPI", "Core Voltage (V)", "CPU Temp (°C)", "CPU Frequency (MHz)",
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
    if cpu_freq:
        try:
            # Extract the numeric value and convert to MHz
            cpu_freq_value = int(cpu_freq.split('=')[1])
            cpu_freq_mhz = round(cpu_freq_value / 1_000_000, 2)  # Convert Hz to MHz with 2 decimal places
            cpu_freq = f"{cpu_freq_mhz} MHz"
        except (IndexError, ValueError):
            cpu_freq = 'N/A'
    else:
        cpu_freq = 'N/A'

    load_average = run_ssh_command(hostname, "cat /proc/loadavg")
    load_average = load_average.split()[0] if load_average else 'N/A'

    memory_usage = run_ssh_command(hostname, "free -m")
    if memory_usage:
        try:
            memory_used = memory_usage.splitlines()[1].split()[2]
            memory_usage = f"{memory_used} MB"
        except IndexError:
            memory_usage = 'N/A'
    else:
        memory_usage = 'N/A'

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
    try:
        with output_file.open('a', newline='') as file:
            csv_writer = csv.writer(file)
            for rpi, metrics in rpi_metrics.items():
                row = [
                    current_time.strftime("%Y-%m-%d"),
                    current_time.strftime("%H:%M:%S"),
                    rpi,
                    metrics['core_voltage'],
                    metrics['cpu_temp'],
                    metrics['cpu_freq'].replace(' MHz', '') if metrics['cpu_freq'] != 'N/A' else 'N/A',  # Store numeric value
                    metrics['load_average'],
                    metrics['memory_usage'],
                    metrics['throttled_status'],
                    test_stage
                ]
                csv_writer.writerow(row)
    except Exception as e:
        logging.error(f"Failed to write to CSV file {output_file}: {e}")
        return  # Early exit if writing fails

    # Append to graph data with thread safety
    with graph_data_lock:
        graph_entry = {"time": current_time.strftime("%H:%M:%S")}
        for rpi, metrics in rpi_metrics.items():
            if metrics['cpu_freq'] != 'N/A':
                # Store numeric value for graphing
                try:
                    cpu_freq_numeric = float(metrics['cpu_freq'].replace(' MHz', ''))
                except ValueError:
                    cpu_freq_numeric = None
            else:
                cpu_freq_numeric = None
            try:
                cpu_temp_numeric = float(metrics['cpu_temp']) if metrics['cpu_temp'] != 'N/A' else None
                core_voltage_numeric = float(metrics['core_voltage']) if metrics['core_voltage'] != 'N/A' else None
                load_average_numeric = float(metrics['load_average']) if metrics['load_average'] != 'N/A' else None
            except ValueError:
                cpu_temp_numeric = core_voltage_numeric = load_average_numeric = None

            graph_entry[rpi] = {
                "cpu_temp": cpu_temp_numeric,
                "cpu_freq": cpu_freq_numeric,
                "core_voltage": core_voltage_numeric,
                "load_average": load_average_numeric
            }
        graph_data.append(graph_entry)
        if len(graph_data) > MAX_GRAPH_DATA:
            graph_data.pop(0)

# Function to discover RPIs dynamically
def discover_rpi_hostnames():
    global rpi_hostnames
    discovered = []
    logging.info("Starting discovery of RPIs...")

    def check_hostname(index):
        hostname = f"{RPI_NAME_PREFIX}{index}{DOMAIN_SUFFIX}"
        try:
            socket.gethostbyname(hostname)
            logging.info(f"Discovered RPI: {hostname}")
            return hostname
        except socket.error:
            return None

    with ThreadPoolExecutor(max_workers=20) as executor:
        # Submit all hostname checks concurrently
        future_to_hostname = {executor.submit(check_hostname, i): i for i in range(1, MAX_RPIS + 1)}
        for future in as_completed(future_to_hostname):
            hostname = future.result()
            if hostname:
                discovered.append(hostname)
            if len(discovered) >= MAX_RPIS:
                break  # Limit to MAX_RPIS

    rpi_hostnames = discovered
    logging.info(f"Discovered RPIs: {rpi_hostnames}")

# Run hostname discovery at startup
discover_rpi_hostnames()

# Run stress tests for all RPIs and collect data at intervals
def run_stress_tests(duration_hours, log_frequency_seconds, save_path):
    global test_running
    test_running = True

    stress_test_duration_seconds = duration_hours * 3600  # Convert to seconds
    interval_seconds = log_frequency_seconds
    total_duration = duration_hours * 3600  # Convert hours to seconds
    end_time = time.time() + total_duration

    # Use the current working directory as the save_path
    save_path = Path.cwd()

    try:
        # Ensure the save_path exists (it should, since it's the current directory)
        save_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to access directory {save_path}: {e}")
        test_running = False
        return

    # Log the save_path being used
    logging.info(f"Using save_path: {save_path}")

    output_file = save_path / f"stress_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    try:
        # Write the header for the CSV file
        with output_file.open('w', newline='') as file:
            csv_writer = csv.writer(file)
            csv_writer.writerow(DATA_COLUMNS)
    except Exception as e:
        logging.error(f"Failed to write header to CSV file {output_file}: {e}")
        test_running = False
        return

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

@app.route('/')
def index():
    return render_template('index.html', active_rpis=rpi_hostnames, default_directory=str(Path.cwd()))

@app.route('/run_tests', methods=['POST'])
def run_tests():
    global test_running
    test_running = True

    try:
        duration_hours = float(request.form.get('duration'))
        log_frequency_seconds = float(request.form.get('log_frequency', 60))
        # No need to get 'save_path' from the form anymore
    except (ValueError, TypeError) as e:
        logging.error(f"Invalid input parameters: {e}")
        return jsonify({"status": "error", "message": "Invalid input parameters."}), 400

    # Run stress tests for all RPIs and collect data in a separate thread
    threading.Thread(target=run_stress_tests, args=(duration_hours, log_frequency_seconds, None), daemon=True).start()
    
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

# New endpoint to run vcgencmd commands on a specific RPI
@app.route('/run_vcg_cmd', methods=['POST'])
def run_vcg_cmd():
    hostname = request.form.get('hostname')
    if hostname not in rpi_hostnames:
        return jsonify({"status": "error", "message": "Invalid hostname."}), 400
    metrics = collect_metrics_rpi(hostname)
    if metrics:
        return jsonify({"status": "success", "data": metrics})
    else:
        return jsonify({"status": "error", "message": "Failed to collect metrics."}), 500

# New endpoint to run custom commands on all RPIs
@app.route('/run_command', methods=['POST'])
def run_command():
    command = request.form.get('command')
    if not command:
        return jsonify({"status": "error", "message": "No command provided."}), 400
    results = {}
    for hostname in rpi_hostnames:
        result = run_ssh_command(hostname, command)
        results[hostname] = result if result else "Failed to run command."
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
