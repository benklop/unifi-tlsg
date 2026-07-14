"""Hardware profiles for TL-SG family members."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelProfile:
    """Describes a physical TL-SG switch and how it maps into UniFi."""

    id: str
    product_name: str
    copper_ports: int
    combo_ports: int
    dedicated_sfp_ports: int
    # CLI interface naming: "1/0/{n}" for SG2424 V2 family.
    if_format: str = "1/0/{n}"
    # Ports that support media-type {rj45|sfp} (1-based).
    combo_port_numbers: tuple[int, ...] = ()
    max_vlans: int = 512
    notes: str = ""

    @property
    def total_ports(self) -> int:
        return self.copper_ports + self.dedicated_sfp_ports

    @property
    def unifi_port_count(self) -> int:
        """Ports exposed to UniFi (copper view; combo SFP shares copper index)."""
        return self.copper_ports + self.dedicated_sfp_ports

    def cli_ifname(self, port: int) -> str:
        return self.if_format.format(n=port)

    def is_combo(self, port: int) -> bool:
        return port in self.combo_port_numbers


_PROFILES: dict[str, ModelProfile] | None = None


def _load_profiles() -> dict[str, ModelProfile]:
    global _PROFILES
    if _PROFILES is not None:
        return _PROFILES

    profiles: dict[str, ModelProfile] = {}
    pkg = resources.files("unifi_tlsg.models")
    for entry in pkg.iterdir():
        if entry.name.endswith(".yaml") or entry.name.endswith(".yml"):
            data = yaml.safe_load(entry.read_text()) or {}
            for pid, raw in data.items():
                profiles[pid] = _from_raw(pid, raw)

    # Also allow user-defined overrides next to CWD.
    override = Path("models")
    if override.is_dir():
        for path in override.glob("*.y*ml"):
            data = yaml.safe_load(path.read_text()) or {}
            for pid, raw in data.items():
                profiles[pid] = _from_raw(pid, raw)

    _PROFILES = profiles
    return profiles


def _from_raw(pid: str, raw: dict[str, Any]) -> ModelProfile:
    combo = tuple(raw.get("combo_port_numbers") or [])
    return ModelProfile(
        id=pid,
        product_name=raw.get("product_name", pid),
        copper_ports=int(raw["copper_ports"]),
        combo_ports=int(raw.get("combo_ports", len(combo))),
        dedicated_sfp_ports=int(raw.get("dedicated_sfp_ports", 0)),
        if_format=str(raw.get("if_format", "1/0/{n}")),
        combo_port_numbers=combo,
        max_vlans=int(raw.get("max_vlans", 512)),
        notes=str(raw.get("notes", "")),
    )


def get_profile(profile_id: str) -> ModelProfile:
    profiles = _load_profiles()
    if profile_id not in profiles:
        known = ", ".join(sorted(profiles)) or "(none)"
        raise KeyError(f"unknown model profile {profile_id!r}; known: {known}")
    return profiles[profile_id]


def list_profiles() -> list[str]:
    return sorted(_load_profiles())
