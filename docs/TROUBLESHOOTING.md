# Troubleshooting & EdgeOS Quirks

This document records issues encountered during the setup and operation of the Device Gateway Control project, along with their solutions.

## Issue: Video Streaming (Sting TV) Times Out
**Symptom**: Metadata loads, but video playback fails or times out when routed through the Tailscale VPN.
**Cause**: MTU (Maximum Transmission Unit) mismatch. Tailscale uses an MTU of 1280, while standard Ethernet uses 1500. Large packets (like video streams) exceeding 1280 bytes are dropped.
**Solution**: Added MSS (Maximum Segment Size) clamping on the EdgeRouter for the specific device IP to force smaller packet negotiation.

### Applied Configuration:
```bash
configure
set firewall modify detour rule 4 action modify
set firewall modify detour rule 4 modify tcp-mss 1240
set firewall modify detour rule 4 source address 172.15.0.56
commit
save
exit
```

---

## EdgeOS Quirks & Workarounds

### 1. Modifying Rulesets "In Use" Fails
**Symptom**: Error `Firewall config error: Cannot delete rule set "detour" (still in use)` when trying to add or modify rules via non-interactive scripts.
**Cause**: EdgeOS often refuses to modify a ruleset that is currently bound to an interface in a non-interactive session.
**Workaround**: Use an interactive SSH session with a pseudo-terminal (`ssh -tt`) to run the commands. This forces EdgeOS to handle the commit correctly.

### 2. Group Resolution Fails in Scripts
**Symptom**: Error `group [GroupName] is of type [Invalid] not [address]` when referencing a firewall group in a script.
**Cause**: The script environment sometimes fails to resolve group names correctly during commit.
**Workaround**: Use the specific IP address in the rule instead of the group name if it fails, or apply the configuration interactively.

---

## Current Active Configuration (Manual Override)
The `detour` ruleset on the EdgeRouter currently applies directly to IP `172.15.0.56` (Xiaomi) instead of using the `Tailscale_Routed_Devices` group due to the resolution bug mentioned above.

If more devices need to be added, you can add them specifically by IP or try to fix the group issue in the live config.
