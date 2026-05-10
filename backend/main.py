from flask import Flask, jsonify, request, send_from_directory
import os
import json
import paramiko
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='../frontend')

def run_router_command(command):
    """Runs a command on the EdgeRouter via SSH using invoke_shell."""
    host = os.environ.get('ROUTER_IP')
    user = os.environ.get('ROUTER_USER')
    key_path = os.environ.get('SSH_KEY_PATH')
    
    # Resolve path relative to project root if needed
    if key_path and not os.path.isabs(key_path):
        key_path = os.path.join(os.path.dirname(__file__), '../', key_path)
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, key_filename=key_path, timeout=5)
        chan = ssh.invoke_shell()
        time.sleep(2)
        
        # Disable pager
        chan.send("terminal length 0\n")
        time.sleep(0.5)
        
        # Clear buffer
        while chan.recv_ready():
            chan.recv(1024)
            
        chan.send(command + "\n")
        time.sleep(2) # Give command time to run
        
        output = ""
        while chan.recv_ready():
            output += chan.recv(1024).decode()
            
        return output
    except Exception as e:
        print(f"Failed to connect or run command: {e}")
        return None
    finally:
        ssh.close()

def run_router_config_commands(commands):
    """Runs a list of configuration commands on the EdgeRouter."""
    host = os.environ.get('ROUTER_IP')
    user = os.environ.get('ROUTER_USER')
    key_path = os.environ.get('SSH_KEY_PATH')
    
    if key_path and not os.path.isabs(key_path):
        key_path = os.path.join(os.path.dirname(__file__), '../', key_path)
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(host, username=user, key_filename=key_path, timeout=5)
        chan = ssh.invoke_shell()
        time.sleep(2)
        
        # Clear buffer
        while chan.recv_ready():
            chan.recv(1024)
            
        chan.send("configure\n")
        time.sleep(1)
        
        for cmd in commands:
            chan.send(cmd + "\n")
            time.sleep(1)
            
        chan.send("commit\n")
        time.sleep(2)
        chan.send("save\n")
        time.sleep(1)
        chan.send("exit\n")
        
        output = ""
        while chan.recv_ready():
            output += chan.recv(1024).decode()
            
        return output
    except Exception as e:
        print(f"Failed to connect or run config commands: {e}")
        return None
    finally:
        ssh.close()

def get_routed_ips():
    output = run_router_command("show configuration commands | grep Tailscale_Routed")
    if not output:
        return []
    ips = []
    for line in output.splitlines():
        if "address" in line and not "description" in line:
            parts = line.split()
            if len(parts) >= 6:
                ips.append(parts[5])
    return ips

def parse_leases():
    output = run_router_command("show dhcp leases")
    if not output:
        return []
    devices = []
    lines = output.splitlines()
    # Find the start of data (skip headers)
    start_index = 0
    for i, line in enumerate(lines):
        if "IP address" in line and "Hardware Address" in line:
            start_index = i + 2
            break
            
    if start_index == 0:
        return []
        
    for line in lines[start_index:]:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 5:
            devices.append({"ip": parts[0], "mac": parts[1], "name": parts[4] if len(parts) > 4 else "Unknown", "static": False})
    return devices

def parse_arp():
    output = run_router_command("show arp")
    if not output:
        return []
    devices = []
    lines = output.splitlines()
    # Find start of data
    start_index = 0
    for i, line in enumerate(lines):
        if "Address" in line and "HWaddress" in line:
            start_index = i + 1
            break
            
    if start_index == 0:
        return []
        
    for line in lines[start_index:]:
        if not line.strip() or "incomplete" in line:
            continue
        parts = line.split()
        if len(parts) >= 3 and ":" in parts[2]:
            devices.append({"ip": parts[0], "mac": parts[2], "name": "Unknown", "static": True})
    return devices

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/devices', methods=['GET'])
def get_devices():
    leases = parse_leases()
    arp_entries = parse_arp()
    routed_ips = get_routed_ips()
    
    device_map = {}
    for dev in arp_entries:
        device_map[dev['mac']] = dev
    for dev in leases:
        if dev['mac'] in device_map:
            device_map[dev['mac']]['name'] = dev['name']
            device_map[dev['mac']]['static'] = False
        else:
            device_map[dev['mac']] = dev
    for mac, dev in device_map.items():
        dev['routed'] = dev['ip'] in routed_ips
        
    return jsonify(list(device_map.values()))

@app.route('/api/devices/<mac>/toggle', methods=['POST'])
def toggle_routing(mac):
    data = request.json
    enable = data.get('enable', False)
    
    devices = get_devices().json
    target_ip = None
    for dev in devices:
        if dev['mac'] == mac:
            target_ip = dev['ip']
            break
            
    if not target_ip:
        return jsonify({"status": "error", "message": "Device IP not found"}), 404
        
    commands = []
    if enable:
        commands.append(f"set firewall group address-group Tailscale_Routed address {target_ip}")
    else:
        commands.append(f"delete firewall group address-group Tailscale_Routed address {target_ip}")
        
    output = run_router_config_commands(commands)
    
    if output and "Commit failed" not in output:
        return jsonify({"status": "success", "routed": enable})
    else:
        return jsonify({"status": "error", "message": "Failed to update router config", "output": output}), 500

@app.route('/api/devices/<mac>/static', methods=['POST'])
def make_static(mac):
    devices = get_devices().json
    target_ip = None
    target_name = "unknown"
    for dev in devices:
        if dev['mac'] == mac:
            target_ip = dev['ip']
            target_name = dev['name'] if dev['name'] != "Unknown" else f"dev_{mac.replace(':', '')}"
            break
            
    if not target_ip:
        return jsonify({"status": "error", "message": "Device IP not found"}), 404
        
    commands = [
        f"set service dhcp-server shared-network-name LAN subnet 172.15.0.0/24 static-mapping {target_name} ip-address {target_ip}",
        f"set service dhcp-server shared-network-name LAN subnet 172.15.0.0/24 static-mapping {target_name} mac-address {mac}"
    ]
    
    output = run_router_config_commands(commands)
    
    if output and "Commit failed" not in output:
        return jsonify({"status": "success", "static": True})
    else:
        return jsonify({"status": "error", "message": "Failed to update router config", "output": output}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
