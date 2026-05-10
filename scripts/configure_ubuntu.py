import paramiko
import os
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

host = os.environ.get('UBUNTU_IP')
user = os.environ.get('UBUNTU_USER')
key_path = os.environ.get('SSH_KEY_PATH')

if key_path and not os.path.isabs(key_path):
    key_path = os.path.join(os.path.dirname(__file__), '../', key_path)

sudo_password = os.environ.get('SUDO_PASSWORD')
if not sudo_password:
    print("SUDO_PASSWORD environment variable not set.")
    # Fallback can be added if needed

def run_sudo_command(ssh, command, password):
    if not password:
        print("Error: No sudo password provided.")
        return 1
    full_command = f"echo '{password}' | sudo -S {command}"
    stdin, stdout, stderr = ssh.exec_command(full_command)
    exit_status = stdout.channel.recv_exit_status()
    print(f"Command: {command}")
    print(f"Exit Status: {exit_status}")
    print(f"Stdout: {stdout.read().decode()}")
    print(f"Stderr: {stderr.read().decode()}")
    print("-" * 40)
    return exit_status

try:
    print(f"Connecting to {host} using key {key_path}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, key_filename=key_path)
    print("Connected!")

    ts_interface = "tailscale0"

    print("Enabling IP forwarding...")
    run_sudo_command(ssh, "sysctl -w net.ipv4.ip_forward=1", sudo_password)
    
    print(f"Setting up MASQUERADE on {ts_interface}...")
    cmd = f"sh -c 'iptables -t nat -C POSTROUTING -o {ts_interface} -j MASQUERADE || iptables -t nat -A POSTROUTING -o {ts_interface} -j MASQUERADE'"
    run_sudo_command(ssh, cmd, sudo_password)

    # Also make IP forwarding persistent!
    print("Making IP forwarding persistent...")
    run_sudo_command(ssh, "sh -c 'echo net.ipv4.ip_forward=1 >> /etc/sysctl.conf'", sudo_password)

    print("Configuration completed successfully!")

except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
