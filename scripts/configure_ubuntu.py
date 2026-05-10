import paramiko
import json
import os

# Load config
with open(os.path.join(os.path.dirname(__file__), '../config.json')) as f:
    config = json.load(f)

host = config['ubuntu_ip']
user = config['ubuntu_user']
key_path = os.path.join(os.path.dirname(__file__), '../', config['ssh_key_path'])

# Password is still needed for sudo on Ubuntu if not configured passwordless
# We should prompt for it or use a key if sudo allows it.
# For now, let's assume we need to prompt or the user can provide it.
# Wait, the user said "make sure no passwords will be in any file".
# So I should NOT hardcode the sudo password.
# I'll modify the script to ask for the sudo password if needed, or assume passwordless sudo.
# Let's prompt for it if it fails or just use the key for SSH and ask for sudo password.
# Actually, I can use `getpass` to ask interactively if running manually.
# But for automation, it's better to avoid prompting if possible.
# Let's see if we can run without sudo for some commands or if we must have it.
# We must have it for sysctl and iptables.
# I'll update the script to read the sudo password from an environment variable or prompt.
# Let's use an environment variable `SUDO_PASSWORD` and NOT save it in the file.

import getpass

sudo_password = os.environ.get('SUDO_PASSWORD')
if not sudo_password:
    print("SUDO_PASSWORD environment variable not set.")
    # Fallback to prompt if running interactively
    # sudo_password = getpass.getpass("Enter sudo password for Ubuntu: ")

def run_sudo_command(ssh, command, password):
    if not password:
        print("Error: No sudo password provided.")
        return 1
    full_command = f"echo '{password}' | sudo -S {command}"
    stdin, stdout, stderr = ssh.exec_command(full_command)
    exit_status = stdout.channel.recv_exit_status()
    print(f"Command: {command}")
    print(f"Exit Status: {exit_status}")
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

    print("Configuration completed successfully!")

except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
