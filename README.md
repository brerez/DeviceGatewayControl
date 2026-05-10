# Device Gateway Control

A system to selectively route local network devices through a Tailscale exit node (e.g., in Israel) using an EdgeRouter X and an Ubuntu server.

## Architecture

*   **EdgeRouter X**: Acts as the main router. Uses Policy-Based Routing (PBR) to direct traffic from specific devices to the Ubuntu server.
*   **Ubuntu Server**: Acts as the Tailscale gateway. Receives traffic from the EdgeRouter and forwards it through the Tailscale exit node.
*   **Web App**: Hosted on the Ubuntu server (or locally for development). Provides a UI to see connected devices and toggle their routing status.

## Project Structure

*   `backend/`: Python Flask app serving the API and frontend.
*   `frontend/`: Vanilla HTML/JS/CSS web interface.
*   `scripts/`: Automation scripts for configuring the router and server.
*   `keys/`: SSH keys used for automation (ignored by git).
*   `docs/`: Project documentation and guides.

## Setup

### 1. Key Generation

This project requires **ED25519** keys for compatibility with modern libraries and the router.

See the detailed [Setup Guide](docs/SETUP_GUIDE.md) for instructions on how to generate and install the keys.

### 2. Configure Ubuntu Server
*   Run `scripts/configure_ubuntu.py` (requires `SUDO_PASSWORD` env var).

### 3. Configure EdgeRouter
*   Run `scripts/configure_edgerouter_v2.py`.

## Running the App

1.  Initialize venv: `python3 -m venv venv`
2.  Install dependencies: `./venv/bin/pip install -r requirements.txt`
3.  Run backend: `./venv/bin/python backend/main.py`
