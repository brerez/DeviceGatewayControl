# Selective Routing via Tailscale Exit Node

Plan a solution to selectively route devices on a home network through a Tailscale exit node in Israel, using an EdgeRouter X and an Ubuntu server.

## User Review Required

> [!WARNING]
> **IP Address Note**: Your LAN IP range `172.15.0.0/24` is technically in the **public** IP space (Private Class B is `172.16.0.0` to `172.31.255.255`). It will work fine for your local network as long as you don't need to access public internet services that actually use the `172.15.x.x` range. If you ever experience weird connectivity issues to random internet sites, this might be why.

> [!IMPORTANT]
> **Packet Flow Confirmation**: You got it right! The flow for a routed device (like the TV) will be:
> 1. **TV** sends traffic to the internet.
> 2. **EdgeRouter** intercepts it (via PBR) and sends it to the **Ubuntu Server** (`172.15.0.152`).
> 3. **Ubuntu Server** encapsulates the traffic in Tailscale and sends it back to the **EdgeRouter** destined for the Israeli Exit Node.
> 4. **EdgeRouter** sees this as normal traffic from the Ubuntu server and sends it out to the **WAN** (`eth4`).
> This flow works perfectly and keeps the heavy crypto lifting on the Ubuntu server.

## Configuration Details

*   **EdgeRouter IP**: `172.15.0.1`
*   **Ubuntu Server IP**: `172.15.0.152`
*   **LAN Interface**: `switch0`
*   **WAN Interface**: `eth4`

---

## Proposed Changes

### Component 1: EdgeRouter X Configuration
*   We need to create a custom routing table (e.g., table 10) with a default route pointing to `172.15.0.152`.
*   We need to create a firewall modify ruleset on `switch0` to match specific source IPs and use table 10.
*   We need an address group (e.g., `Israeli_Routed`) to easily manage which IPs are routed.

### Component 2: Ubuntu Server Configuration
*   Enable IP forwarding.
*   Configure iptables for MASQUERADE on the Tailscale interface.

### Component 3: Gateway Control Web App
*   **Backend**: Python or Node.js to handle SSH commands to the EdgeRouter.
*   **Frontend**: HTML/JS dashboard to see devices and toggle status.
*   **New Feature**: Ability to create a DHCP reservation for a device directly from the app if it doesn't have one!

---

## Suggested Tasks

### Automated Tasks (Via SSH from your Mac)
*I can run these for you once you provide the credentials or set up SSH keys.*

1.  **[ ] Configure Ubuntu Server**:
    *   Enable IP forwarding.
    *   Set up NAT/MASQUERADE for traffic entering from LAN and leaving via Tailscale.
2.  **[ ] Configure EdgeRouter X**:
    *   Create the PBR routing table and firewall rules.
    *   Create the `Israeli_Routed` address group.

### Development Tasks (Antigravity)
1.  **[ ] Backend Development**:
    *   Implement EdgeRouter SSH communication (reading leases, updating groups, adding static leases).
    *   Create API endpoints for the frontend.
2.  **[ ] Frontend Development**:
    *   Build the UI to list devices, show status, and toggle routing.
    *   Add "Make Static" button for dynamic leases.

---

## Verification Plan

1.  **Manual Check**: From a controlled device, verify IP changes to Israel when toggled on.
2.  **Stat Check**: Check ER-X firewall statistics to ensure packets are hitting the modify rule.
