"""YAML configuration loading and device state persistence."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_AUTHKEY = "ba86f2bbe107c7c57eb5f2690775c712"


@dataclass
class ControllerConfig:
    inform_url: str = "http://unifi:8080/inform"
    adopt_url: str | None = None


@dataclass
class SwitchCliConfig:
    host: str
    username: str = "admin"
    password: str = ""
    port: int = 22
    transport: str = "ssh"  # ssh | telnet
    enable_password: str | None = None
    timeout: float = 15.0


@dataclass
class DeviceConfig:
    """One emulated UniFi switch backed by a physical TL-SG."""

    name: str
    mac: str
    ip: str
    model_profile: str = "sg2424"
    unifi_model: str = "US24"
    firmware: str = "6.6.0.15156"
    uplink_port: int = 1
    cli: SwitchCliConfig = field(default_factory=lambda: SwitchCliConfig(host=""))
    state_dir: str = "state"

    def __post_init__(self) -> None:
        if isinstance(self.cli, dict):
            self.cli = SwitchCliConfig(**self.cli)
        self.mac = normalize_mac(self.mac)


@dataclass
class AppConfig:
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    devices: list[DeviceConfig] = field(default_factory=list)
    inform_interval: float = 10.0
    dry_run_apply: bool = False
    log_level: str = "INFO"

    @classmethod
    def load(cls, path: str | Path) -> AppConfig:
        raw = yaml.safe_load(Path(path).read_text()) or {}
        controller = ControllerConfig(**(raw.get("controller") or {}))
        devices = [DeviceConfig(**d) for d in raw.get("devices") or []]
        return cls(
            controller=controller,
            devices=devices,
            inform_interval=float(raw.get("inform_interval", 10.0)),
            dry_run_apply=bool(raw.get("dry_run_apply", False)),
            log_level=str(raw.get("log_level", "INFO")),
        )


@dataclass
class DeviceState:
    """Persisted UniFi adoption / provision state for one device."""

    adopted: bool = False
    authkey: str = DEFAULT_AUTHKEY
    use_aes_gcm: bool = False
    cfgversion: str = ""
    inform_url: str | None = None
    mgmt_url: str | None = None
    locating: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def path_for(self, state_dir: Path, mac: str) -> Path:
        return state_dir / f"{mac.replace(':', '')}.json"

    @classmethod
    def load(cls, state_dir: Path, mac: str) -> DeviceState:
        path = state_dir / f"{mac.replace(':', '')}.json"
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        known = set(cls.__dataclass_fields__)  # type: ignore[attr-defined]
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)

    def save(self, state_dir: Path, mac: str) -> None:
        state_dir.mkdir(parents=True, exist_ok=True)
        path = state_dir / f"{mac.replace(':', '')}.json"
        path.write_text(json.dumps(asdict(self), indent=2, sort_keys=True) + "\n")


def normalize_mac(mac: str) -> str:
    hex_only = "".join(c for c in mac.lower() if c in "0123456789abcdef")
    if len(hex_only) != 12:
        raise ValueError(f"invalid MAC address: {mac!r}")
    return ":".join(hex_only[i : i + 2] for i in range(0, 12, 2))


def mac_bytes(mac: str) -> bytes:
    return bytes.fromhex(normalize_mac(mac).replace(":", ""))
