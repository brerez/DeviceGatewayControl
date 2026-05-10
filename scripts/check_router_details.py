import paramiko
import json
import os
import time

# Load config
with open(os.path.join(os.path.dirname(__file__), '../config.json')) as f:
    config = json.load(f)

host = config['router_ip']
user = config['router_user']
key_path = os.path.join(os.path.dirname(__file__), '../', config['ssh_key_path'])

try:
    print(f"Connecting to EdgeRouter {host}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, key_filename=key_path)
    print("Connected!")

    chan = ssh.invoke_shell()
    time.sleep(2)
    
    # Disable pager
    chan.send("terminal length 0\n")
    time.sleep(1)
    
    # Clear buffer
    while chan.recv_ready():
        chan.recv(1024)

    # Check ARP
    print("Checking ARP table...")
    chan.send("show arp\n")
    time.sleep(2)
    
    output = ""
    while chan.recv_ready():
        output += chan.recv(1024).decode()
    print("ARP Output:")
    print(output)

except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
