"""Build UniFi switch Inform JSON payloads."""

from __future__ import annotations

import time
from typing import Any

from unifi_tlsg.config import DeviceConfig, DeviceState
from unifi_tlsg.models import ModelProfile


def build_adoption_inform(
    device: DeviceConfig,
    state: DeviceState,
    inform_url: str,
) -> dict[str, Any]:
    """Minimal pre-adoption inform (state=0 / default=True)."""
    return {
        "hostname": device.name or "UBNT",
        "state": 0,
        "default": True,
        "inform_url": inform_url,
        "mac": device.mac,
        "ip": device.ip,
        "model": device.unifi_model,
        "model_display": device.unifi_model,
        "version": device.firmware,
        "uptime": 1,
        "required_version": "4.0.0",
    }


def build_switch_inform(
    device: DeviceConfig,
    state: DeviceState,
    profile: ModelProfile,
    *,
    inform_url: str,
    ports: list[dict[str, Any]],
    mac_table: list[dict[str, Any]],
    uptime: int = 1,
    hostname: str | None = None,
) -> dict[str, Any]:
    """Full switch status inform after adoption."""
    uplink_idx = max(0, device.uplink_port - 1)
    uplink_port = ports[uplink_idx] if ports else None

    payload: dict[str, Any] = {
        "architecture": "mips",
        "board_rev": 1,
        "bootrom_version": "unknown",
        "cfgversion": state.cfgversion or "0",
        "default": False,
        "discovery_response": False,
        "has_fan": False,
        "has_temperature": False,
        "hash_id": device.mac.replace(":", ""),
        "hostname": hostname or device.name,
        "inform_url": inform_url,
        "ip": device.ip,
        "isolated": False,
        "kernel_version": "3.6.0",
        "locating": state.locating,
        "mac": device.mac,
        "model": device.unifi_model,
        "model_display": device.unifi_model,
        "name": device.name,
        "required_version": "4.0.0",
        "selfrun_beacon": True,
        "serial": device.mac.replace(":", "").upper(),
        "state": 2,
        "time": int(time.time()),
        "uptime": uptime,
        "version": device.firmware,
        "port_table": ports,
        "mac_table": mac_table,
        "ethernet_table": [
            {
                "mac": device.mac,
                "num_port": profile.unifi_port_count,
                "name": "eth0",
            }
        ],
        "system-stats": {
            "cpu": "1",
            "mem": "10",
            "uptime": str(uptime),
        },
        "uplink": {
            "type": "wire",
            "speed": (uplink_port or {}).get("speed", 1000),
            "full_duplex": True,
            "max_speed": 1000,
            "port_idx": device.uplink_port,
            "up": bool((uplink_port or {}).get("up", True)),
        },
    }
    return payload


def empty_port(port_idx: int, *, media: str = "GE", is_uplink: bool = False) -> dict[str, Any]:
    """Skeleton UniFi port_table entry."""
    return {
        "port_idx": port_idx,
        "port_poe": False,
        "poe_enable": False,
        "poe_mode": "off",
        "media": media,
        "speed": 0,
        "full_duplex": True,
        "enable": True,
        "up": False,
        "autoneg": True,
        "tx_bytes": 0,
        "rx_bytes": 0,
        "tx_packets": 0,
        "rx_packets": 0,
        "tx_errors": 0,
        "rx_errors": 0,
        "tx_dropped": 0,
        "rx_dropped": 0,
        "tx_broadcast": 0,
        "rx_broadcast": 0,
        "tx_multicast": 0,
        "rx_multicast": 0,
        "masked": False,
        "aggregated_by": False,
        "flowctrl_tx": False,
        "flowctrl_rx": False,
        "stp_state": "disabled",
        "op_mode": "switch",
        "is_uplink": is_uplink,
        "name": f"Port {port_idx}",
    }
