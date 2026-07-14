"""Parsers for TL-SG `show` command output.

Real firmware output varies slightly by revision; parsers are intentionally
forgiving and covered by fixtures in tests/.
"""

from __future__ import annotations

import re
from typing import Iterable

from unifi_tlsg.backend.base import MacEntry, PortStatus


# Gi1/0/1 or 1/0/1 or just Port column variants.
PORT_RE = re.compile(r"(?:Gi(?:gabitEthernet)?)?(?P<slot>\d+)/(?P<mod>\d+)/(?P<port>\d+)|^(?P<bare>\d+)$")


def parse_port_token(token: str) -> int | None:
    token = token.strip()
    m = PORT_RE.search(token.replace("gigabitEthernet", "").replace("GigabitEthernet", ""))
    if not m:
        # Try trailing /N
        m2 = re.search(r"/(\d+)$", token)
        return int(m2.group(1)) if m2 else None
    if m.group("bare"):
        return int(m.group("bare"))
    return int(m.group("port"))


def parse_interface_status(text: str) -> dict[int, PortStatus]:
    """Parse `show interface status` into port -> PortStatus."""
    ports: dict[int, PortStatus] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("port") or line.startswith("---"):
            continue
        parts = re.split(r"\s+", line)
        if len(parts) < 3:
            continue
        port = parse_port_token(parts[0])
        if port is None:
            continue
        # Heuristic columns: Port Status ... Speed Duplex ...
        joined = " ".join(parts).lower()
        up = "up" in joined and "down" not in parts[1].lower()
        enabled = "disable" not in joined
        speed = 0
        for p in parts:
            if p.isdigit():
                speed = int(p)
                break
            m = re.match(r"(\d+)([MG])", p, re.I)
            if m:
                speed = int(m.group(1)) * (1000 if m.group(2).upper() == "G" else 1)
                break
        duplex = "full"
        for p in parts:
            if p.lower() in {"full", "half"}:
                duplex = p.lower()
        ports[port] = PortStatus(
            port=port,
            up=up,
            enabled=enabled,
            speed_mbps=speed if up else 0,
            duplex=duplex,
        )
    return ports


def parse_interface_switchport(text: str) -> dict[int, dict]:
    """Parse `show interface switchport` VLAN membership.

    Returns port -> {pvid, tagged, untagged}.
    """
    result: dict[int, dict] = {}
    current: int | None = None
    for line in text.splitlines():
        raw = line.rstrip()
        line = raw.strip()
        if not line:
            continue
        # Port heading
        m_port = re.search(r"(?:Port|Interface)\s*[:=]?\s*(.+)$", line, re.I)
        if m_port and "vlan" not in line.lower():
            p = parse_port_token(m_port.group(1).split()[0])
            if p is not None:
                current = p
                result.setdefault(current, {"pvid": 1, "tagged": [], "untagged": []})
                continue
        # Compact table rows: Port PVID ... 
        parts = re.split(r"\s+", line)
        maybe = parse_port_token(parts[0])
        if maybe is not None and len(parts) >= 2 and parts[1].isdigit():
            current = maybe
            result[current] = {
                "pvid": int(parts[1]),
                "tagged": _parse_vlan_list(" ".join(parts[2:])),
                "untagged": [],
            }
            continue
        if current is None:
            continue
        low = line.lower()
        if "pvid" in low:
            nums = re.findall(r"\d+", line)
            if nums:
                result[current]["pvid"] = int(nums[-1])
        elif "tagged" in low and "untagged" not in low:
            result[current]["tagged"] = _parse_vlan_list(line)
        elif "untagged" in low:
            result[current]["untagged"] = _parse_vlan_list(line)
    return result


def parse_vlan_brief(text: str) -> list[int]:
    vlans: list[int] = []
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+)\b", line)
        if m:
            vid = int(m.group(1))
            if 1 <= vid <= 4094:
                vlans.append(vid)
    return sorted(set(vlans))


def parse_mac_table(text: str) -> list[MacEntry]:
    entries: list[MacEntry] = []
    mac_re = re.compile(r"([0-9a-f]{2}(?:[:\-][0-9a-f]{2}){5})", re.I)
    for line in text.splitlines():
        m = mac_re.search(line)
        if not m:
            continue
        mac = m.group(1).lower().replace("-", ":")
        parts = re.split(r"\s+", line.strip())
        vlan = 1
        port = 0
        for p in parts:
            if p.isdigit() and 1 <= int(p) <= 4094:
                # Prefer a VLAN-looking number before port if both exist.
                if vlan == 1:
                    vlan = int(p)
                else:
                    port = int(p)
            pt = parse_port_token(p)
            if pt is not None and "/" in p or p.lower().startswith("gi"):
                port = pt
        # Last integer often is port on some firmwares.
        ints = [int(p) for p in parts if p.isdigit()]
        if port == 0 and ints:
            port = ints[-1]
        if vlan == 1 and len(ints) >= 2:
            vlan = ints[0]
        entries.append(MacEntry(mac=mac, port=port, vlan=vlan))
    return entries


def _parse_vlan_list(text: str) -> list[int]:
    """Expand strings like '2-5,10,20-21' or 'VLAN 2-5'."""
    ids: list[int] = []
    for token in re.findall(r"\d+(?:\s*-\s*\d+)?", text):
        token = token.replace(" ", "")
        if "-" in token:
            a, b = token.split("-", 1)
            ids.extend(range(int(a), int(b) + 1))
        else:
            ids.append(int(token))
    # Filter out accidental captures of port numbers in prose by keeping vlan range.
    return sorted({i for i in ids if 1 <= i <= 4094})


def merge_port_views(
    status: dict[int, PortStatus],
    switchport: dict[int, dict],
    port_numbers: Iterable[int],
) -> list[PortStatus]:
    out: list[PortStatus] = []
    for n in port_numbers:
        base = status.get(
            n,
            PortStatus(port=n, up=False, enabled=True, speed_mbps=0, duplex="full"),
        )
        sp = switchport.get(n, {})
        if sp:
            base.pvid = int(sp.get("pvid", base.pvid))
            base.tagged_vlans = list(sp.get("tagged", []))
            base.untagged_vlans = list(sp.get("untagged", []))
        out.append(base)
    return out
