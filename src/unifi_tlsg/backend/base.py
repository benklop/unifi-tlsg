"""Abstract switch backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal


PortMode = Literal["access", "trunk", "general"]


@dataclass
class PortStatus:
    port: int
    up: bool
    enabled: bool
    speed_mbps: int
    duplex: str
    description: str = ""
    pvid: int = 1
    tagged_vlans: list[int] = field(default_factory=list)
    untagged_vlans: list[int] = field(default_factory=list)
    mode: PortMode = "general"
    media: str = "rj45"  # rj45 | sfp
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_packets: int = 0
    tx_packets: int = 0
    rx_errors: int = 0
    tx_errors: int = 0


@dataclass
class MacEntry:
    mac: str
    port: int
    vlan: int
    entry_type: str = "dynamic"


@dataclass
class DesiredPortConfig:
    """UniFi-facing desired state for one port."""

    port: int
    enabled: bool = True
    name: str | None = None
    native_vlan: int = 1
    tagged_vlans: list[int] = field(default_factory=list)
    # access = only native untagged; trunk = native + tagged list
    mode: PortMode = "access"


@dataclass
class SwitchSnapshot:
    hostname: str
    uptime: int
    ports: list[PortStatus]
    mac_table: list[MacEntry]
    vlans: list[int]


class SwitchBackend(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def snapshot(self) -> SwitchSnapshot: ...

    @abstractmethod
    def ensure_vlans(self, vlan_ids: list[int]) -> None: ...

    @abstractmethod
    def apply_port_config(self, ports: list[DesiredPortConfig]) -> None: ...

    @abstractmethod
    def save_config(self) -> None: ...
