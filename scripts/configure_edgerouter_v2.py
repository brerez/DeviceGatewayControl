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

def send_command(chan, cmd):
    chan.send(cmd + "\n")
    time.sleep(1)
    output = ""
    while chan.recv_ready():
        output += chan.recv(1024).decode()
    print(output)
    return output

try:
    print(f"Connecting to EdgeRouter {host} using key {key_path}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, key_filename=key_path)
    print("Connected!")

    chan = ssh.invoke_shell()
    time.sleep(2)
    while chan.recv_ready():
        chan.recv(1024)

    print("Entering configuration mode...")
    send_command(chan, "configure")

    print("Applying configuration with new group name...")
    send_command(chan, "set protocols static table 10 route 0.0.0.0/0 next-hop 172.15.0.152")
    send_command(chan, "set firewall group address-group Tailscale_Routed description 'Devices routed via Israel Tailscale'")
    send_command(chan, "set firewall modify detour rule 20 description 'Route to Ubuntu Tailscale'")
    send_command(chan, "set firewall modify detour rule 20 source group address-group Tailscale_Routed")
    send_command(chan, "set firewall modify detour rule 20 modify table 10")

    print("Commiting changes...")
    send_command(chan, "commit")
    
    print("Saving changes...")
    send_command(chan, "save")
    
    send_command(chan, "exit")
    print("EdgeRouter configuration completed!")

except Exception as e:
    print(f"Error: {e}")
finally:
    ssh.close()
