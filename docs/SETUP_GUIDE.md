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
