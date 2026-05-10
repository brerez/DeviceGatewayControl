import paramiko
import json
import os
import time

# Load config from .env
from dotenv import load_dotenv
load_dotenv()

host = os.environ.get('ROUTER_IP')
user = os.environ.get('ROUTER_USER')
key_path = os.environ.get('SSH_KEY_PATH')

if key_path and not os.path.isabs(key_path):
    key_path = os.path.join(os.path.dirname(__file__), '../', key_path)

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

    # Check Leases
    print("Checking DHCP leases...")
    chan.send("show dhcp leases\n")
    time.sleep(2)
    
    output = ""
    while chan.recv_ready():
        output += chan.recv(1024).decode()
    print("Leases Output:")
    print(output)

except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
