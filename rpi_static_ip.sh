#!/bin/bash

# RPI Setup Script to automate configuration for Flask app
# Run as: sudo ./rpi_setup.sh <hostname> <static_ip> <router_gateway>
# Example usage: sudo ./rpi_setup.sh rpi1 192.168.0.10 192.168.0.1

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

# Utility function for error handling
error_exit() {
    echo "Error: $1" 1>&2
    exit 1
}

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
    # Backup the original dhcpcd.conf file before editing
    cp /etc/dhcpcd.conf /etc/dhcpcd.conf.bak || error_exit "Failed to back up dhcpcd.conf"

    cat <<EOF >> /etc/dhcpcd.conf

# Custom static IP configuration for RPI
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

# Step 6: Install Required Packages (if not already installed)
REQUIRED_PACKAGES=("net-tools")
for package in "${REQUIRED_PACKAGES[@]}"; do
    if dpkg -l | grep -q $package; then
        echo "Package $package is already installed. Skipping."
    else
        echo "Installing package $package"
        apt-get install -y $package || error_exit "Failed to install $package"
    fi
done

# Step 7: Create Log Directory for System Metrics
if [ -d "$LOG_DIR" ]; then
    echo "Log directory $LOG_DIR already exists. Skipping this step."
else
    echo "Creating log directory at $LOG_DIR"
    mkdir -p "$LOG_DIR" || error_exit "Failed to create log directory"
    chown $USER:$USER "$LOG_DIR" || error_exit "Failed to set ownership for log directory"
    echo "Log directory created successfully at $LOG_DIR with $USER credentials"
fi

# Step 8: Check for Reboot Necessity and Confirm
read -p "Do you want to reboot now to apply changes? (y/n): " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    echo "Rebooting to apply changes..."
    reboot
else
    echo "Reboot skipped. Please reboot manually for changes to take effect."
fi

echo "RPI Setup Completed."
