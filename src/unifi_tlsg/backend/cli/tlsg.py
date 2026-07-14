"""TP-Link TL-SG CLI backend (SG2424 V2 family and siblings)."""

from __future__ import annotations

import logging

from unifi_tlsg.backend.base import (
    DesiredPortConfig,
    SwitchBackend,
    SwitchSnapshot,
)
from unifi_tlsg.backend.cli import parser
from unifi_tlsg.backend.cli.session import CliSession
from unifi_tlsg.config import SwitchCliConfig
from unifi_tlsg.models import ModelProfile

logger = logging.getLogger(__name__)


class TlSgCliBackend(SwitchBackend):
    def __init__(self, cli: SwitchCliConfig, profile: ModelProfile, *, dry_run: bool = False) -> None:
        self.cli_cfg = cli
        self.profile = profile
        self.dry_run = dry_run
        self._session: CliSession | None = None

    def connect(self) -> None:
        self._session = CliSession(self.cli_cfg)
        if not self.dry_run:
            self._session.connect()

    def close(self) -> None:
        if self._session is not None:
            self._session.close()
            self._session = None

    def snapshot(self) -> SwitchSnapshot:
        sess = self._require()
        status_txt = sess.cmd("show interface status")
        sw_txt = sess.cmd("show interface switchport")
        vlan_txt = sess.cmd("show vlan brief")
        mac_txt = sess.cmd("show mac address-table all")
        # Hostname / uptime are best-effort.
        hostname = self.cli_cfg.host
        uptime = 1
        try:
            sys_txt = sess.cmd("show system-info")
            for line in sys_txt.splitlines():
                if "name" in line.lower() and ":" in line:
                    hostname = line.split(":", 1)[1].strip() or hostname
                if "uptime" in line.lower() and ":" in line:
                    uptime = _parse_uptime(line.split(":", 1)[1])
        except Exception:
            logger.debug("show system-info unavailable", exc_info=True)

        status = parser.parse_interface_status(status_txt)
        switchport = parser.parse_interface_switchport(sw_txt)
        ports = parser.merge_port_views(
            status, switchport, range(1, self.profile.copper_ports + 1)
        )
        for p in ports:
            if self.profile.is_combo(p.port):
                # Media type not always in status; default copper until probed.
                p.media = p.media or "rj45"

        return SwitchSnapshot(
            hostname=hostname,
            uptime=uptime,
            ports=ports,
            mac_table=parser.parse_mac_table(mac_txt),
            vlans=parser.parse_vlan_brief(vlan_txt) or [1],
        )

    def ensure_vlans(self, vlan_ids: list[int]) -> None:
        needed = sorted({v for v in vlan_ids if v != 1 and 2 <= v <= 4094})
        if not needed:
            return
        # Create as ranges for fewer commands.
        ranges = _to_ranges(needed)
        lines = [f"vlan {r}" for r in ranges]
        self._configure(lines)

    def apply_port_config(self, ports: list[DesiredPortConfig]) -> None:
        """Apply UniFi-desired port modes via general switchport CLI.

        Mapping:
          access: PVID=native, untagged native, no tagged
          trunk:  PVID=native, untagged native, tagged = tagged_vlans
        """
        lines: list[str] = []
        vlan_ids = {1}
        for pc in ports:
            vlan_ids.add(pc.native_vlan)
            vlan_ids.update(pc.tagged_vlans)
        self.ensure_vlans(sorted(vlan_ids))

        for pc in ports:
            ifname = self.profile.cli_ifname(pc.port)
            lines.append(f"interface gigabitEthernet {ifname}")
            if pc.name:
                # CLI limit 16 chars.
                lines.append(f"description {pc.name[:16]}")
            if pc.enabled:
                lines.append("no shutdown")
            else:
                lines.append("shutdown")

            # Reset membership then re-add.
            # Keep VLAN 1 handling conservative: always ensure native untagged.
            native = pc.native_vlan
            tagged = [v for v in pc.tagged_vlans if v != native]
            lines.append(f"switchport pvid {native}")
            if native != 1:
                lines.append(f"switchport general allowed vlan {native} untagged")
            if tagged:
                lines.append(
                    "switchport general allowed vlan "
                    + ",".join(_to_ranges(tagged))
                    + " tagged"
                )
            lines.append("exit")

        self._configure(lines)

    def save_config(self) -> None:
        sess = self._require()
        if self.dry_run:
            logger.info("dry-run: copy running-config startup-config")
            return
        sess.cmd("copy running-config startup-config")

    def _configure(self, lines: list[str]) -> None:
        if self.dry_run:
            logger.info("dry-run configure:\n  %s", "\n  ".join(lines))
            return
        sess = self._require()
        logger.info("applying %d CLI lines", len(lines))
        sess.configure(lines)

    def _require(self) -> CliSession:
        if self._session is None:
            raise RuntimeError("backend not connected")
        return self._session


def _to_ranges(ids: list[int]) -> list[str]:
    if not ids:
        return []
    ids = sorted(set(ids))
    ranges: list[str] = []
    start = prev = ids[0]
    for n in ids[1:]:
        if n == prev + 1:
            prev = n
            continue
        ranges.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = n
    ranges.append(str(start) if start == prev else f"{start}-{prev}")
    return ranges


def _parse_uptime(text: str) -> int:
    """Best-effort uptime to seconds."""
    text = text.strip().lower()
    total = 0
    for num, unit in re_findall_uptime(text):
        if unit.startswith("day"):
            total += num * 86400
        elif unit.startswith("hour"):
            total += num * 3600
        elif unit.startswith("min"):
            total += num * 60
        elif unit.startswith("sec"):
            total += num
    return total or 1


def re_findall_uptime(text: str) -> list[tuple[int, str]]:
    import re

    return [(int(n), u) for n, u in re.findall(r"(\d+)\s*([a-z]+)", text)]
