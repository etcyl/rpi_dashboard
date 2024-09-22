from flask import Flask, render_template, jsonify, request
import paramiko
import socket
import threading
import logging
import os
import pandas as pd
from datetime import datetime
from time import sleep

app = Flask(__name__)

# Setup detailed logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SSH configuration for RPIs
USERNAME = "fleetroot"
PASSWORD = "root"
SSH_PORT = 22
rpi_hostnames = ["rpi1.local", "rpi2.local"]  # All RPIs

test_running = False  # Global flag for test status

# Columns for Excel Data
DATA_COLUMNS = [
    "Date", "Time", "Core Voltage", "CPU Temp", "CPU Frequency (MHz)",
    "Load Average", "Memory Usage", "Throttled Status"
]

def check_hostname(hostname):
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.error:
        logging.error(f"Hostname resolution failed for {hostname}")
        return False

def run_ssh_command(hostname, command):
    if not check_hostname(hostname):
        return None
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

def collect_data(rpi, num_runs, run_interval_seconds):
    """ Collects metrics from the RPI at set intervals """
    data = []
    for run in range(num_runs):
        if not test_running:
            break  # Exit early if the test is stopped
        current_time = datetime.now()
        entry = {
            "Date": current_time.strftime("%m/%d/%Y"),
            "Time": current_time.strftime("%H:%M:%S"),
            "Core Voltage": "0.97",  # Simulated data
            "CPU Temp": "33.1",
            "CPU Frequency (MHz)": "2000.478",
            "Load Average": "0.13",
            "Memory Usage": "Used: 356MB, Free: 284MB",
            "Throttled Status": "0x0"
        }
        data.append(entry)
        sleep(run_interval_seconds)  # Simulate a pause between data collection intervals
    return data

@app.route('/')
def index():
    """ Render the main dashboard with active RPIs """
    threads = []
    results = {}

    def update_result(hostname):
        if run_ssh_command(hostname, "echo 'ping'"):
            results[hostname] = run_ssh_command(hostname, "hostname")

    for hostname in rpi_hostnames:
        thread = threading.Thread(target=update_result, args=(hostname,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return render_template('index.html', active_rpis=results)

@app.route('/run_tests', methods=['POST'])
def run_tests():
    """ Run tests for all RPIs for the selected duration and log progress """
    global test_running
    test_running = True

    duration_hours = int(request.form.get('duration'))
    save_path = request.form.get('save_path') or os.getcwd()  # Default to current directory
    run_interval_seconds = 60  # Collect data every minute (adjust as needed)
    total_seconds = duration_hours * 3600
    num_runs = total_seconds // run_interval_seconds

    results = []
    threads = []

    # Collect data for all RPIs in parallel
    def collect_for_rpi(hostname):
        rpi_data = collect_data(hostname, num_runs, run_interval_seconds)
        df = pd.DataFrame(rpi_data, columns=DATA_COLUMNS)
        output_path = os.path.join(save_path, f"{hostname}_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        df.to_excel(output_path, index=False)
        results.append({"rpi": hostname, "path": output_path})

    for hostname in rpi_hostnames:
        thread = threading.Thread(target=collect_for_rpi, args=(hostname,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    return jsonify({"status": "success", "results": results})

@app.route('/stop_test', methods=['POST'])
def stop_test():
    """ Stops the running test """
    global test_running
    test_running = False
    return jsonify({"status": "Test stopped successfully"})

@app.route('/progress/<duration>')
def get_progress(duration):
    """ Provides the current progress for a test """
    duration_seconds = int(duration) * 3600
    total_seconds = duration_seconds
    progress_data = []

    for elapsed_time in range(0, total_seconds, 60):  # Update every minute
        if not test_running:
            break  # Stop the progress if the test is halted
        progress = (elapsed_time / total_seconds) * 100
        progress_data.append({"progress": progress})
        sleep(1)

    if not progress_data:
        return jsonify({"progress": 0})  # Return 0 if the test is stopped early

    return jsonify({"progress": progress_data[-1]["progress"]})

@app.route('/metrics/<hostname>')
def get_rpi_metrics_route(hostname):
    """ Returns metrics for a specific RPI """
    metrics = get_rpi_metrics(hostname)
    return jsonify(metrics)

def get_rpi_metrics(hostname):
    """ Gathers various metrics from an RPI """
    metrics = {
        'core_voltage': run_ssh_command(hostname, "vcgencmd measure_volts core").split('=')[1].replace('V', ''),
        'cpu_temp': run_ssh_command(hostname, "vcgencmd measure_temp").split('=')[1].replace("'C", ""),
        'cpu_freq_mhz': str(float(run_ssh_command(hostname, "vcgencmd measure_clock arm").split('=')[1]) / 1000000),
        'load_average': run_ssh_command(hostname, "cat /proc/loadavg").split()[0],
        'memory_usage': run_ssh_command(hostname, "free -m").splitlines()[1].split()[2] + "MB",
        'throttled_status': run_ssh_command(hostname, "vcgencmd get_throttled").split('=')[1]
    }
    return metrics

@app.route('/run_command', methods=['POST'])
def run_command():
    """Run a custom command on all RPIs and return the result."""
    command = request.form.get('command')
    results = {}

    def run_on_rpi(hostname):
        result = run_ssh_command(hostname, command)
        if result:
            results[hostname] = result
        else:
            results[hostname] = "No result or connection error"

    # Create threads for each RPI to run commands in parallel
    threads = []
    for hostname in rpi_hostnames:
        thread = threading.Thread(target=run_on_rpi, args=(hostname,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    return jsonify(results)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
