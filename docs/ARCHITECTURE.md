# Architecture

## Goals (1.0)

1. Adopt and keep a TL-SG switch online in a UniFi Network controller.
2. Report port link/speed/counters and MAC table for topology.
3. Apply port VLAN membership (access/trunk) when the controller provisions.

## Components

### Inform agent (`daemon.py` / `inform/`)

Runs an Inform loop per configured device:

1. If not adopted: UDP discovery + minimal Inform (`default=true`).
2. On `setparam`/`mgmt_cfg`: persist `authkey`, `cfgversion`, GCM flag.
3. After adoption: poll the switch backend, emit a US24-like Inform JSON.
4. On config-bearing `setparam`: map to `DesiredPortConfig` and apply via CLI.

Encryption follows the TNBU flags used by real UniFi devices (AES-CBC initially, AES-GCM after the controller enables it).

### Switch backend (`backend/cli/`)

CLI is the supported management plane for TL-SG2424 V2:

- SSH via Paramiko interactive shell
- Privilege escalation with `enable`
- `show interface status`, `show interface switchport`, `show mac address-table all`, `show vlan brief`
- Config via `configure` → `interface gigabitEthernet 1/0/N` → `switchport …`

Parsers are fixture-tested and intentionally loose; capture real `show` output from your firmware into `tests/fixtures/` when something doesn't match.

### Model profiles (`models/profiles.yaml`)

Different SG SKUs share the same CLI dialect. Profiles encode:

- copper / combo / dedicated SFP counts
- combo port numbers (media-type rj45|sfp)
- interface name format (`1/0/{n}`)

## Safety

- `dry_run_apply: true` logs intended CLI without writing.
- Config apply always ends with optional `copy running-config startup-config`.
- Controllers can send network **object** IDs rather than 802.1Q IDs; treat early mapping as suspect until verified against a packet capture of `setparam`.
