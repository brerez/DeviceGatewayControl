from flask import Flask, jsonify, request, send_from_directory
import os
import json
import re
import paramiko
import time
import threading
import urllib.request
import urllib.error
import queue
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='../frontend')

# Cache for MAC OUI to Vendor
VENDOR_CACHE = {}
VENDOR_CACHE_LOCK = threading.Lock()

# Queue for MAC lookups to respect rate limits
lookup_queue = queue.Queue()

def mac_lookup_worker():
    """Worker thread to process MAC lookups at a safe rate."""
    while True:
        try:
            mac = lookup_queue.get()
            print(f"Worker processing MAC: {mac}")
            if mac is None:
                break
                
            oui = mac.lower()[:8]
            
            with VENDOR_CACHE_LOCK:
                if oui in VENDOR_CACHE and VENDOR_CACHE[oui] != "Loading...":
                    lookup_queue.task_done()
                    continue
            
            try:
                url = f"https://api.macvendors.com/{mac}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                with urllib.request.urlopen(req, timeout=3) as response:
                    vendor = response.read().decode('utf-8')
                    with VENDOR_CACHE_LOCK:
                        VENDOR_CACHE[oui] = vendor
            except urllib.error.HTTPError as e:
                with VENDOR_CACHE_LOCK:
                    if e.code == 404:
                        VENDOR_CACHE[oui] = "Unknown Vendor"
                    elif e.code == 429:
                        VENDOR_CACHE[oui] = "Rate Limited"
                        time.sleep(5) # Backoff
                    else:
                        VENDOR_CACHE[oui] = "Error"
            except Exception as e:
                print(f"Error fetching vendor for {mac}: {e}")
                with VENDOR_CACHE_LOCK:
                    VENDOR_CACHE[oui] = "Unknown"
                    
            lookup_queue.task_done()
            time.sleep(1) # Rate limit respect
            
        except Exception as e:
            print(f"Worker error: {e}")
            time.sleep(1)

# Start the worker thread
worker_thread = threading.Thread(target=mac_lookup_worker, daemon=True)
worker_thread.start()

def read_all_output(chan, timeout=2.0):
    """Reads all available output from the channel until no more data arrives for 'timeout' seconds."""
    output = ""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if chan.recv_ready():
            output += chan.recv(1024).decode()
            start_time = time.time() # Reset timer on data
        else:
            time.sleep(0.1)
    return output


def run_router_command(command):
    """Runs a command on the EdgeRouter via SSH using exec_command."""
    host = os.environ.get('ROUTER_IP')
    user = os.environ.get('ROUTER_USER')
    key_path = os.environ.get('SSH_KEY_PATH')
    
    if key_path and not os.path.isabs(key_path):
        key_path = os.path.join(os.path.dirname(__file__), '../', key_path)
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
        ssh.connect(host, username=user, pkey=pkey, timeout=5, allow_agent=False, look_for_keys=False)
        
        # Use wrapper for show commands
        full_command = f"/opt/vyatta/bin/vyatta-op-cmd-wrapper {command}"
        stdin, stdout, stderr = ssh.exec_command(full_command)
        output = stdout.read().decode()
        
        return output
    except Exception as e:
        print(f"Failed to connect or run command: {e}", flush=True)
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
        pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
        ssh.connect(host, username=user, pkey=pkey, timeout=5, allow_agent=False, look_for_keys=False)
        chan = ssh.invoke_shell()
        output = read_all_output(chan, timeout=1.0)
        
        chan.send("configure\n")
        output += read_all_output(chan, timeout=1.0)
        
        for cmd in commands:
            chan.send(cmd + "\n")
            output += read_all_output(chan, timeout=1.0)
            time.sleep(0.5)
            
        chan.send("commit\n")
        output += read_all_output(chan, timeout=5.0) # Commit takes longer
        
        chan.send("save\n")
        output += read_all_output(chan, timeout=2.0)
        
        chan.send("exit\n")
        output += read_all_output(chan, timeout=1.0)
        
        print(f"Config Commands Output:\n{output}", flush=True)
        return output
    except Exception as e:
        print(f"Failed to connect or run config commands: {e}")
        return None
    finally:
        ssh.close()

# ... (parse_leases, parse_arp, get_routed_ips remain the same) ...
def get_routed_ips(output):
    if not output:
        return []
    ips = []
    for line in output.splitlines():
        if "address" in line and not "description" in line:
            parts = line.split()
            if len(parts) >= 7:
                ips.append(parts[6])
    return ips

def parse_leases(output):
    if not output:
        return []
    devices = []
    lines = output.splitlines()
    start_index = 0
    for i, line in enumerate(lines):
        if "IP address" in line and "Hardware Address" in line:
            start_index = i + 1
            break
            
    if start_index == 0:
        return []
        
    for line in lines[start_index:]:
        if not line.strip() or line.startswith("shikua@"):
            continue
        parts = line.split()
        if len(parts) >= 5:
            name = parts[5] if len(parts) > 5 else "Unknown"
            devices.append({"ip": parts[0], "mac": parts[1], "name": name, "static": False})
    return devices

def parse_arp(output):
    if not output:
        return []
    devices = []
    lines = output.splitlines()
    start_index = 0
    for i, line in enumerate(lines):
        if "Address" in line and "HWaddress" in line:
            start_index = i + 1
            break
            
    if start_index == 0:
        return []
        
    for line in lines[start_index:]:
        if not line.strip() or "incomplete" in line or line.startswith("shikua@"):
            continue
        parts = line.split()
        if len(parts) >= 3 and ":" in parts[2]:
            devices.append({"ip": parts[0], "mac": parts[2], "name": "Unknown", "static": True})
    return devices

def get_static_macs(output):
    if not output:
        return set()
    
    mappings = re.findall(r'static-mapping\s+\S+\s+\{[^}]+\}', output)
    macs = set()
    for m in mappings:
        mac_match = re.search(r'mac-address\s+([0-9a-fA-F:]{17})', m)
        if mac_match:
            macs.add(mac_match.group(1).lower())
    return macs

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/devices', methods=['GET'])
def get_devices():
    host = os.environ.get('ROUTER_IP')
    user = os.environ.get('ROUTER_USER')
    key_path = os.environ.get('SSH_KEY_PATH')
    
    if key_path and not os.path.isabs(key_path):
        key_path = os.path.join(os.path.dirname(__file__), '../', key_path)
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(key_path)
        ssh.connect(host, username=user, pkey=pkey, timeout=5, allow_agent=False, look_for_keys=False)
        
        combined_command = "vbash -c '/opt/vyatta/bin/vyatta-op-cmd-wrapper show dhcp leases; echo ===ARP===; /opt/vyatta/bin/vyatta-op-cmd-wrapper show arp; echo ===ROUTED===; /opt/vyatta/bin/vyatta-op-cmd-wrapper show configuration commands | grep Tailscale_Routed_Devices; echo ===CONFIG===; /opt/vyatta/bin/vyatta-op-cmd-wrapper show configuration'"
        stdin, stdout, stderr = ssh.exec_command(combined_command)
        combined_output = stdout.read().decode()
        
        parts = combined_output.split("===ARP===")
        leases_output = parts[0]
        
        parts = parts[1].split("===ROUTED===")
        arp_output = parts[0]
        
        parts = parts[1].split("===CONFIG===")
        routed_output = parts[0]
        config_output = parts[1]
        
        leases = parse_leases(leases_output)
        arp_entries = parse_arp(arp_output)
        routed_ips = get_routed_ips(routed_output)
        static_macs = get_static_macs(config_output)
        
    except Exception as e:
        print(f"Failed to connect or get data in get_devices: {e}", flush=True)
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        ssh.close()
    
    device_map = {}
    for dev in arp_entries:
        device_map[dev['mac']] = dev
        
    for dev in leases:
        if dev['mac'] in device_map:
            device_map[dev['mac']]['name'] = dev['name']
        else:
            device_map[dev['mac']] = dev
            
    for mac, dev in device_map.items():
        dev['routed'] = dev['ip'] in routed_ips
        dev['static'] = mac.lower() in static_macs
        
        oui = mac.lower()[:8]
        with VENDOR_CACHE_LOCK:
            if oui in VENDOR_CACHE:
                dev['hardware'] = VENDOR_CACHE[oui]
            else:
                dev['hardware'] = "Loading..."
                VENDOR_CACHE[oui] = "Loading..."
                lookup_queue.put(mac)
        
    return jsonify(list(device_map.values()))

# ... (toggle_routing and make_static remain the same) ...
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
        commands.append(f"set firewall group address-group Tailscale_Routed_Devices address {target_ip}")
    else:
        commands.append(f"delete firewall group address-group Tailscale_Routed_Devices address {target_ip}")
        
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
        
    # Sanitize name for EdgeOS (alphanumeric and underscores only)
    target_name = re.sub(r'[^a-zA-Z0-9_]', '_', target_name)
        
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
