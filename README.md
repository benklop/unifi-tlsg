# unifi-tlsg

UniFi Inform proxy for TP-Link **TL-SG** smart switches (tested on **TL-SG2424 V2**).

The daemon speaks the UniFi Inform protocol so a physical TL-SG appears in a UniFi Network controller (as e.g. `US24`), polls switch state over **SSH CLI**, and applies VLAN / port configuration pushed by the controller.

> The modern TL-SG2424 web UI is painful in current browsers. This project uses the [CLI Reference](https://static.tp-link.com/resources/document/TL-SG2424_V2_CLI.pdf) instead.

## Status (roadmap to 1.0)

| Phase | Capability | Status |
|------:|------------|--------|
| 1 | Discovery, adopt, inform heartbeat | Implemented (needs lab validation) |
| 2 | Port status + MAC table telemetry | Implemented (CLI parsers + fixtures) |
| 3 | VLAN / port config apply from UniFi | Implemented (dry-run supported) |

Additional model profiles (`sg2216`, `sg2424p`, `sg2452`) are declared for CLI-family compatibility; only SG2424 hardware is available for live testing.

## Quick start

```bash
# clone + install
git clone https://github.com/benklop/unifi-tlsg.git
cd unifi-tlsg
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# configure
cp config/unifi-tlsg.example.yaml config/unifi-tlsg.yaml
$EDITOR config/unifi-tlsg.yaml

# sanity-check CLI access
unifi-tlsg -c config/unifi-tlsg.yaml snapshot

# first adoption (then click Adopt in UniFi UI, run adopt again if needed)
unifi-tlsg -c config/unifi-tlsg.yaml adopt --url http://CONTROLLER:8080/inform

# run proxy
unifi-tlsg -c config/unifi-tlsg.yaml run
```

Enable `dry_run_apply: true` while bringing a site up — config sync is logged without writing to the switch.

## Architecture

```text
UniFi Controller  <--- Inform (TNBU/AES/zlib JSON) --->  unifi-tlsg
                                                         |
                                                         | SSH CLI
                                                         v
                                                      TL-SG2424
```

- `inform/` — TNBU encode/decode, discovery TLV, adoption + switch payloads, response handlers
- `backend/cli/` — Paramiko SSH session, `show` parsers, VLAN/port apply via `switchport general`
- `models/` — hardware profiles (port counts, combo ports, CLI if naming)
- `mapping/` — UniFi `port_overrides` / `system_cfg` → `DesiredPortConfig`

## UniFi model choice

Devices default to UniFi model `US24`. Override with `unifi_model` if a different switch SKU behaves better with your controller version. The controller is relatively forgiving about missing optional fields.

## Config apply mapping

| UniFi intent | TL-SG CLI |
|--------------|-----------|
| Create VLAN | `vlan <id\|range>` |
| Access port | `switchport pvid N` + untagged membership |
| Trunk port | `pvid` native + `switchport general allowed vlan … tagged` |
| Disable port | `shutdown` / `no shutdown` |
| Persist | `copy running-config startup-config` |

Controller network **IDs** vs VLAN **IDs** can differ depending on UniFi version; if trunks look wrong, inspect `state/*.json` `extra` fields from `setparam` and adjust mapping.

## Roadmap

See [docs/plans/](docs/plans/README.md) for remaining work and linked GitHub issues (`0.2` / `0.3` / `1.0` milestones).

## Development

```bash
pytest
ruff check src tests
```

## References

- [TL-SG2424 V2 User Guide](https://static.tp-link.com/res/down/doc/TL-SG2424(UN)_V2_UG.pdf)
- [TL-SG2424 V2 CLI Reference](https://static.tp-link.com/resources/document/TL-SG2424_V2_CLI.pdf)
- [UniFi Inform protocol notes](https://jrjparks.github.io/unofficial-unifi-guide/protocols/inform.html)
- Prior art: [unifi-gateway](https://github.com/amd989/unifi-gateway), [unifi-stubd](https://github.com/konstruktor1/unifi-stubd), [Unifiction](https://github.com/ArmedGuy/unifiction)

## License

MIT
