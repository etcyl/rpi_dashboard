# Raspberry Pi Dashboard - Flask App

This project is a Flask-based web dashboard to monitor and run commands on multiple Raspberry Pi devices remotely. The dashboard allows users to view key metrics, run custom commands, and run stress tests on all connected RPIs. This guide provides a step-by-step walkthrough of setting up the RPIs, the Flask app, and running it from a Windows PC.
Features

    Monitor Raspberry Pi metrics (CPU Temp, Core Voltage, CPU Frequency, etc.)
    Run custom commands on all connected RPIs
    Run stress tests for a specified number of hours and track progress
    Log test outputs to Excel files

Setup Instructions
1. Raspberry Pi Setup - Run the static ip and hostname script

Use the provided rpi_static_ip.sh script to set up each Raspberry Pi with a static IP and hostname.

Run the script with the hostname, static IP, and router gateway:
    sudo ./rpi_static_ip.sh <hostname> <static_ip> <router_gateway>

Example usage for first rpi:
    sudo ./rpi_static_ip.sh rpi1 192.168.0.10 192.168.0.1

Example usage for second rpi:
    sudo ./rpi_static_ip.sh rpi2 192.168.0.11 192.168.0.1

The script will:
    Set the hostname
    Enable SSH
    Configure a static IP
    Install required packages like net-tools
    Create a log directory (/home/pi/logs)

    Once the script completes, reboot the Raspberry Pi to apply the changes.

2. Setting Up the Flask App on Windows
Step 1: Install Python
    Download and install Python for Windows.
    Ensure you check "Add Python to PATH" during the installation.

Step 2: Clone the Repository
    Open PowerShell or Command Prompt and navigate to the folder where you want to place the project.
    Clone the project repository:
        git clone <https://github.com/your-repository/link>
        cd your-repository/link

Step 3: Setup Virtual Environment
    Create a Python virtual environment:
        python -m venv venv

Activate the virtual environment:
    On Windows:
        .\venv\Scripts\activate

On macOS/Linux:
        source venv/bin/activate

Step 4: Install Dependencies

    Install the dependencies from requirements.txt:

    pip install -r requirements.txt

Minimal requirements.txt

Flask==2.3.2
Jinja2==3.1.2
MarkupSafe==2.1.2
paramiko==3.2.0
pandas==2.1.0

3. Running the Flask App

    Start the Flask development server:

    flask run --host=0.0.0.0 --port=5000

    Open a browser and go to http://localhost:5000.

You should see the Raspberry Pi Dashboard. It will list the available RPIs and allow you to run custom commands and tests.
4. Configuring the Raspberry Pi List

To change or add Raspberry Pis, modify the rpi_hostnames variable in the app.py file:

rpi_hostnames = ["rpi1.local", "rpi2.local"]

Replace rpi1.local and rpi2.local with the hostnames or IP addresses of your Pis.

5. Usage
Run vcgencmd Test
    The dashboard will list all connected RPIs.
    Click on Run vcgencmd test next to any RPI to retrieve and display metrics such as CPU Temp, Core Voltage, and more.

Run Custom Commands
    Enter any Linux command in the Run Command on All RPIs field.
    Click Run All Command to execute the command across all connected RPIs and view the output.

Run All Tests
    Enter a duration (in hours) for the test.
    Optionally specify a save path for the log files.
    Click Run All Tests to start the tests. The test progress will be displayed on the dashboard, and logs will be saved to the specified location.
    
Troubleshooting
    If you cannot connect to your RPIs via hostname (rpi1.local), ensure that avahi-daemon is installed on the Raspberry Pi:

sudo apt install avahi-daemon

Ensure that your Flask app is running on the correct port (default is 5009). You can change this in the app.py file:

python

app.run(host='0.0.0.0', port=5009)

Check your firewall settings on Windows if you cannot access the Flask app from another device on the network.
