Raspberry Pi Dashboard - Flask App

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

6. Additional Bash Script for RPi Setup (Optional)

If you want to automate most of the Raspberry Pi setup, including hostname, static IP, and SSH, here is the rpi_static_ip.sh script you can use:

#!/bin/bash

# RPI Setup Script to automate configuration for Flask app
# Run as: sudo ./rpi_static_ip.sh <hostname> <static_ip> <router_gateway>

# Step 1: Check for sudo/root access
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root. Use sudo."
    exit 1
fi

# Step 2: Parse inputs
HOSTNAME=$1
STATIC_IP=$2
GATEWAY_IP=$3
LOG_DIR="/home/pi/logs"

# Validate inputs
if [ -z "$HOSTNAME" ] || [ -z "$STATIC_IP" ] || [ -z "$GATEWAY_IP" ]; then
    echo "Usage: sudo $0 <hostname> <static_ip> <router_gateway>"
    exit 1
fi

# Step 3: Set Hostname
CURRENT_HOSTNAME=$(cat /etc/hostname | tr -d " \t\n\r")
if [[ "$CURRENT_HOSTNAME" == "$HOSTNAME" ]]; then
    echo "Hostname is already set to $HOSTNAME. Skipping this step."
else
    echo "Setting hostname to $HOSTNAME"
    echo "$HOSTNAME" > /etc/hostname || error_exit "Failed to set hostname"
    sed -i "s/127.0.1.1.*/127.0.1.1 $HOSTNAME/" /etc/hosts || error_exit "Failed to update /etc/hosts"
    hostnamectl set-hostname "$HOSTNAME" || error_exit "Failed to apply hostname with hostnamectl"
    echo "Hostname successfully set to $HOSTNAME"
fi

# Step 4: Enable SSH
SSH_STATUS=$(systemctl is-enabled ssh 2>/dev/null)
if [[ "$SSH_STATUS" == "enabled" ]]; then
    echo "SSH is already enabled. Skipping this step."
else
    echo "Enabling SSH"
    systemctl enable ssh || error_exit "Failed to enable SSH"
    systemctl start ssh || error_exit "Failed to start SSH service"
    echo "SSH enabled successfully"
fi

# Step 5: Configure Static IP
# Check if the static IP is already configured
STATIC_IP_CONFIGURED=$(grep -F "$STATIC_IP" /etc/dhcpcd.conf 2>/dev/null)
if [[ ! -z "$STATIC_IP_CONFIGURED" ]]; then
    echo "Static IP $STATIC_IP is already configured. Skipping this step."
else
    echo "Configuring static IP: $STATIC_IP"
    cp /etc/dhcpcd.conf /etc/dhcpcd.conf.bak || error_exit "Failed to back up dhcpcd.conf"
    
    cat <<EOF >> /etc/dhcpcd.conf
interface eth0
static ip_address=$STATIC_IP/24
static routers=$GATEWAY_IP
static domain_name_servers=8.8.8.8 8.8.4.4

interface wlan0
static ip_address=$STATIC_IP/24
static routers=$GATEWAY_IP
static domain_name_servers=8.8.8.8 8.8.4.4
EOF
    echo "Static IP $STATIC_IP successfully configured."
fi

# Step 6: Install Required Packages
REQUIRED_PACKAGES=("net-tools")
for package in "${REQUIRED_PACKAGES[@]}"; do
    if dpkg -l | grep -q $package; then
        echo "Package $package is already installed. Skipping."
    else
        echo "Installing package $package"
        apt-get install -y $package || error_exit "Failed to install $package"
    fi
done

# Step 7: Create Log Directory
if [ -d "$LOG_DIR" ]; then
    echo "Log directory $LOG_DIR already exists. Skipping."
else
    echo "Creating log directory at $LOG_DIR"
    mkdir -p "$LOG_DIR" || error_exit "Failed to create log directory"
    chown $USER:$USER "$LOG_DIR" || error_exit "Failed to set ownership for log directory"
    echo "Log directory created successfully at $LOG_DIR"
fi

# Step 8: Reboot
read -p "Do you want to reboot now to apply changes? (y/n): " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    echo "Rebooting to apply changes..."
    reboot
else
    echo "Reboot skipped. Please reboot manually for changes to take effect."
fi

echo "RPI Setup Completed."

Troubleshooting
    If you cannot connect to your RPIs via hostname (rpi1.local), ensure that avahi-daemon is installed on the Raspberry Pi:

sudo apt install avahi-daemon

Ensure that your Flask app is running on the correct port (default is 5009). You can change this in the app.py file:

python

app.run(host='0.0.0.0', port=5009)

Check your firewall settings on Windows if you cannot access the Flask app from another device on the network.

# Create an executable
Before creating the executable, make sure all required Python packages are installed. You can install them using pip and the provided requirements.txt file:

```pip install -r requirements.txt```

Run the following command from the root directory to create an executable that includes the Flask app, templates, and static files:

pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" app.py

Once the build is complete, the executable will be located in the dist folder. You can find the executable named app.exe (on Windows).

```cd dist```
```./app.exe  # On Windows```

Upon running the executable:
    The Flask server will start.
    Your default web browser will open automatically to the address http://127.0.0.1:5000/.

Once the web browser opens, you should see the Raspberry Pi monitoring dashboard. You can interact with the application as described above, running tests and commands on your Raspberry Pi devices.

```> .\app.exe
2024-09-25 22:30:02,959 - INFO - Starting discovery of RPIs...
2024-09-25 22:30:03,057 - INFO - Discovered RPI: rpi1.local
2024-09-25 22:30:03,149 - INFO - Discovered RPI: rpi2.local
2024-09-25 22:30:05,751 - INFO - Discovered RPIs: ['rpi1.local', 'rpi2.local']
 * Serving Flask app 'app'
 * Debug mode: off
2024-09-25 22:30:05,883 - INFO - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.0.7:5000
2024-09-25 22:30:05,884 - INFO - Press CTRL+C to quit
2024-09-25 22:30:06,072 - INFO - 127.0.0.1 - - [25/Sep/2024 22:30:06] "GET / HTTP/1.1" 200 -
2024-09-25 22:30:06,214 - INFO - 127.0.0.1 - - [25/Sep/2024 22:30:06] "GET /favicon.ico HTTP/1.1" 404 -
2024-09-25 22:30:11,240 - INFO - 127.0.0.1 - - [25/Sep/2024 22:30:11] "GET /live_metrics HTTP/1.1" 200 -```
