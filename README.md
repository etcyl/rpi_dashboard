![alt text](https://github.com/etcyl/rpi_dashboard/blob/main/Screenshot%202024-09-21%20221403.png)
![alt text](https://github.com/etcyl/rpi_dashboard/blob/main/Screenshot%202024-09-22%20020506.png)
![alt text](https://github.com/etcyl/rpi_dashboard/blob/main/Screenshot%202024-09-22%20020601.png)

# RaspberryPi Status Control Dashboard

Flask-based web dashboard to monitor and run commands on multiple Raspberry Pi devices remotely. 
The dashboard allows users to view specified metrics, run commands, and run stress tests on all connected RPIs. 
This guide provides a step-by-step walkthrough of setting up the RPIs, the Flask app, and running it from a Windows PC.

## Features:
-  **Monitor Raspberry Pi metrics** (CPU Temp, Core Voltage, CPU Frequency, etc.)
-   **Run custom commands on all connected RPIs**
-   **Run stress tests** for a specified number of hours and track progress
-   **Log test outputs** to Excel files

Windows 11 users can try downloading and running the executable from the GitHub app.exe file [here](https://github.com/etcyl/rpi_dashboard/blob/main/windows_exe/app.exe).

Use the provided ```rpi_static_ip.sh``` [here](https://github.com/etcyl/rpi_dashboard/blob/main/rpi_static_ip.sh) script to setup each Raspberry Pi with a static IP and hostname.
This will follow a naming convention for dynamically detecting all of the RPIs on the network.

### Run the script with the hostname, static IP, and router gateway:
    sudo ./rpi_static_ip.sh <hostname> <static_ip> <router_gateway

### Example usage for first rpi:
    sudo ./rpi_static_ip.sh rpi1 192.168.0.10 192.168.0.1

### Example usage for second rpi:
    sudo ./rpi_static_ip.sh rpi2 192.168.0.11 192.168.0.1

The script will:
*   Set the hostname
*   Enable SSH
*   Configure a static IP
*   Install required packages like net-tools
*   Create a log directory (/home/pi/logs)

Once the script completes, reboot the Raspberry Pi (the script will ask if you want to reboot) to apply the changes.

### Download and install Python for Windows
*   Ensure you check "Add Python to PATH" during the installation.

Open PowerShell or Command Prompt and navigate to the folder where you want to place the project.

Clone the project repository and create a Python venv:

        git clone <https://github.com/etcyl/rpi_dashboard>
        cd rpi_dashboard
        python -m venv venv
        .\venv\Scripts\activate

On macOS/Linux:
        
        source venv/bin/activate

### Install dependencies for the machine running the flask app
        
        pip install -r requirements.txt

## Run the app
        
        python app.py

The app should automatically open in the default browser (it may prompt you to allow the app).
If not, then open a browser and go to ```http://localhost:5000.```

You should see the Raspberry Pi Dashboard. It will list the available RPIs and allow you to run custom commands and tests.
The rpis following the bash script naming convention will be periodically scanned for and any new devices will be added to the dashboard.

## Run vcgencmd Test
*    The dashboard will list all connected RPIs.
*    Click on Run vcgencmd test next to any RPI to retrieve and display vcgencmd metrics.

## Run Custom Commands
*    Enter any Linux command in the Run Command on All RPIs field.
*    Click Run All Command to execute the command across all connected RPIs and view the output.

## Run All Tests
*    Enter a duration (in hours) for the test.
*    Click Run All Tests to start the tests. The test progress will be displayed on the dashboard, and logs will be saved to the local root directory.

If you cannot connect to your RPIs via hostname (rpi1.local), ensure that avahi-daemon is installed on the Raspberry Pi:

    sudo apt install avahi-daemon

Ensure that your Flask app is running on the correct port (default is 5000). You can change this in the app.py file:

    app.run(host='0.0.0.0', port=5000)

Check your firewall settings on Windows if you cannot access the Flask app from another device on the network.

## Create an executable
Before creating the executable, make sure all required Python packages are installed.
(A prebuilt Windows 11 app.exe file can be tried [here](https://github.com/etcyl/rpi_dashboard/blob/main/windows_exe/app.exe).)
You can install them using pip and the provided requirements.txt file:

    pip install -r requirements.txt

This command will will run from the root directory to create an executable that includes the Flask app, templates, and static files:

    pyinstaller --onefile --add-data "templates;templates" --add-data "static;static" app.py

Once the build is complete, the executable will be located in the dist folder. You can find the executable named app.exe (on Windows).

    cd dist
    ./app.exe  # On Windows

Upon running the executable:

    1. The Flask server will start.
    2. Your default web browser will open automatically to the address ```http://127.0.0.1:5000/```.

Once the web browser opens, you should see the Raspberry Pi monitoring dashboard. 
You can interact with the application as described above, running tests and commands on your Raspberry Pi devices.

```
.\app.exe
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
