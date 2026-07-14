"""Map between TL-SG snapshots and UniFi inform/config structures."""

from __future__ import annotations

import logging
import re
from typing import Any

from unifi_tlsg.backend.base import DesiredPortConfig, MacEntry, PortStatus, SwitchSnapshot
from unifi_tlsg.inform.payloads import empty_port

logger = logging.getLogger(__name__)


def snapshot_to_inform(
    snap: SwitchSnapshot,
    *,
    uplink_port: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ports = [_port_status_to_inform(p, is_uplink=(p.port == uplink_port)) for p in snap.ports]
    macs = [_mac_to_inform(m) for m in snap.mac_table if m.port > 0]
    return ports, macs


def _port_status_to_inform(p: PortStatus, *, is_uplink: bool) -> dict[str, Any]:
    media = "SFP" if p.media == "sfp" else "GE"
    entry = empty_port(p.port, media=media, is_uplink=is_uplink)
    entry.update(
        {
            "enable": p.enabled,
            "up": p.up,
            "speed": p.speed_mbps if p.up else 0,
            "full_duplex": p.duplex != "half",
            "name": p.description or f"Port {p.port}",
            "tx_bytes": p.tx_bytes,
            "rx_bytes": p.rx_bytes,
            "tx_packets": p.tx_packets,
            "rx_packets": p.rx_packets,
            "tx_errors": p.tx_errors,
            "rx_errors": p.rx_errors,
        }
    )
    return entry


def _mac_to_inform(m: MacEntry) -> dict[str, Any]:
    return {
        "mac": m.mac,
        "vlan": m.vlan,
        "age": 0,
        "port_idx": m.port,
        "uptime": 0,
    }


def parse_unifi_port_config(blob: dict[str, Any]) -> list[DesiredPortConfig]:
    """Extract DesiredPortConfig from a controller setparam blob.

    Supports:
      - system_cfg key=value lines (port.N.* style used by many UniFi devices)
      - JSON-ish port_overrides list if present
    """
    desired: dict[int, DesiredPortConfig] = {}

    overrides = blob.get("port_overrides")
    if isinstance(overrides, list):
        for item in overrides:
            if not isinstance(item, dict):
                continue
            idx = int(item.get("port_idx") or item.get("port") or 0)
            if idx <= 0:
                continue
            tagged = item.get("tagged_networks") or item.get("tagged_vlan_ids") or []
            if isinstance(tagged, str):
                tagged = _ints_from_text(tagged)
            native = int(
                item.get("native_network_id")
                or item.get("native_vlan")
                or item.get("pvid")
                or 1
            )
            # UniFi sometimes uses network IDs not VLAN IDs; callers may remap later.
            mode = "trunk" if tagged else "access"
            desired[idx] = DesiredPortConfig(
                port=idx,
                enabled=bool(item.get("enable", True)),
                name=item.get("name"),
                native_vlan=native,
                tagged_vlans=[int(v) for v in tagged],
                mode=mode,  # type: ignore[arg-type]
            )

    system_cfg = blob.get("system_cfg")
    if isinstance(system_cfg, str):
        desired.update(_parse_system_cfg_ports(system_cfg))

    # Flat keys: port.1.native_vlan=10 etc.
    flat_lines = []
    for key, value in blob.items():
        if key.startswith("port."):
            flat_lines.append(f"{key}={value}")
    if flat_lines:
        desired.update(_parse_system_cfg_ports("\n".join(flat_lines)))

    result = sorted(desired.values(), key=lambda p: p.port)
    if result:
        logger.info("parsed %d port configs from controller", len(result))
    return result


def _parse_system_cfg_ports(text: str) -> dict[int, DesiredPortConfig]:
    # port.<idx>.<field>=value
    kv = re.compile(r"^port\.(\d+)\.([A-Za-z0-9_]+)=(.*)$")
    tmp: dict[int, dict[str, str]] = {}
    for line in text.splitlines():
        line = line.strip()
        m = kv.match(line)
        if not m:
            continue
        idx = int(m.group(1))
        tmp.setdefault(idx, {})[m.group(2)] = m.group(3)

    out: dict[int, DesiredPortConfig] = {}
    for idx, fields in tmp.items():
        tagged = _ints_from_text(fields.get("vlan_tagged", fields.get("tagged", "")))
        native = int(fields.get("vlan_native", fields.get("native", fields.get("pvid", "1"))) or 1)
        enabled = fields.get("enabled", fields.get("enable", "true")).lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        name = fields.get("name") or fields.get("label")
        out[idx] = DesiredPortConfig(
            port=idx + 1 if idx == 0 else idx,  # tolerate 0-based
            enabled=enabled,
            name=name,
            native_vlan=native,
            tagged_vlans=tagged,
            mode="trunk" if tagged else "access",
        )
    return out


def _ints_from_text(text: str) -> list[int]:
    if not text:
        return []
    return [int(x) for x in re.findall(r"\d+", text)]
