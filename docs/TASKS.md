# Task List - Selective Routing Gateway

- [x] Configure Ubuntu Server
    - [x] Enable IP forwarding
    - [x] Set up NAT/MASQUERADE on Tailscale interface
- [x] Configure EdgeRouter X
    - [x] Create PBR routing table (pointing to Ubuntu)
    - [x] Create firewall modify ruleset (Integrated into existing 'detour' ruleset)
    - [x] Create `Tailscale_Routed` address group
- [x] Backend Development
    - [x] Initialize project in workspace
    - [x] Implement SSH client to talk to ER-X
    - [x] Implement DHCP lease parser
    - [x] Create API for toggling routing and adding static leases
- [x] Frontend Development
    - [x] Create dashboard UI (Vanilla CSS, dark mode)
    - [x] Connect frontend to API
