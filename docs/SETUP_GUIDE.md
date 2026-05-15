# Setup Guide - SSH Keys

This project requires secure, passwordless SSH access to both the EdgeRouter X and the Ubuntu Server.

Due to compatibility issues between modern SSH libraries (like Paramiko) and older router software, we use **ED25519** keys instead of standard RSA keys.

## Generating Keys

On your development machine, generate an ED25519 key pair:

```bash
mkdir -p keys
ssh-keygen -t ed25519 -f ./keys/id_ed25519 -N ""
```

This will create:
*   `keys/id_ed25519` (Private key - **DO NOT COMMIT**)
*   `keys/id_ed25519.pub` (Public key)

## Adding Keys to Devices

### 1. Ubuntu Server
Add the content of `keys/id_ed25519.pub` to `~/.ssh/authorized_keys` on the Ubuntu server.

```bash
ssh-copy-id -i keys/id_ed25519.pub user@ubuntu_ip
```

### 2. EdgeRouter X
Add the key via the EdgeOS CLI:

```bash
configure
set system login user <your_user> authentication public-keys devicegateway_ed25519 type ssh-ed25519
set system login user <your_user> authentication public-keys devicegateway_ed25519 key <key_string>
commit
save
exit
```

*Note: `<key_string>` is the content of the `.pub` file without the `ssh-ed25519` prefix and the comment.*

## Project Configuration

Create a `.env` file in the project root with the following variables. **DO NOT COMMIT THIS FILE.**

```env
ROUTER_IP=your_router_ip
ROUTER_USER=your_router_user
UBUNTU_IP=your_ubuntu_ip
UBUNTU_USER=your_ubuntu_user
SSH_KEY_PATH=keys/id_ed25519
```

## EdgeRouter Firewall Configuration (PBR)

To set up the policy-based routing on the EdgeRouter X, run the following commands in the EdgeOS CLI.

### 1. Create Routing Table
This table directs traffic to the Ubuntu server (`172.15.0.152`).
```bash
configure
set protocols static table 10 route 0.0.0.0/0 next-hop 172.15.0.152
commit
```

### 2. Create Modify Ruleset
This ruleset matches traffic from the toggled devices and applies the routing table.

**Intended Setup (Using Groups)**:
```bash
set firewall modify detour description 'PBR for Toggled Devices'
set firewall modify detour rule 5 action modify
set firewall modify detour rule 5 modify table 10
set firewall modify detour rule 5 source group address-group Tailscale_Routed_Devices
commit
```

**Apply to Interface**:
```bash
set interfaces switch switch0 firewall in modify detour
commit
save
exit
```

## Ubuntu Server Configuration

The Ubuntu server acts as the gateway and handles the Tailscale connection.

### 1. Enable IP Forwarding
Ensure IP forwarding is enabled in `/etc/sysctl.conf`:
```text
net.ipv4.ip_forward=1
```

### 2. Set up NAT and MSS Clamping
Run the following commands to set up NAT and fix the video streaming timeout issue (MTU/MSS mismatch):

```bash
# NAT/MASQUERADE on Tailscale interface
sudo iptables -t nat -A POSTROUTING -o tailscale0 -j MASQUERADE

# MSS Clamping to fix video streaming timeouts
sudo iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1240
```

---

## EdgeOS Quirks & Troubleshooting

### 1. Group Resolution Bug
If you encounter an error like `group [Tailscale_Routed_Devices] is of type [Invalid]` when applying rules via scripts on the router, you can apply the rule directly to specific IPs as a fallback:
```bash
set firewall modify detour rule 5 source address 172.15.0.56
```

### 2. "In Use" Ruleset Error
If you cannot modify the `detour` ruleset because it is in use, use an interactive SSH session with a pseudo-terminal (`ssh -tt`) to run the commands, or briefly unbind it:
```bash
delete interfaces switch switch0 firewall in modify detour
commit
# ... make changes ...
set interfaces switch switch0 firewall in modify detour
commit
```

### 3. Multiple Modify Actions in One Rule
EdgeOS may not support applying both `modify table` and `modify tcp-mss` in the same ruleset effectively if they conflict or terminate. That is why MSS clamping was moved to the Ubuntu server.
