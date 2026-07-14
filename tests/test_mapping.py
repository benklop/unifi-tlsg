from unifi_tlsg.backend.base import DesiredPortConfig, PortStatus, SwitchSnapshot
from unifi_tlsg.backend.cli.tlsg import TlSgCliBackend, _to_ranges
from unifi_tlsg.config import SwitchCliConfig
from unifi_tlsg.mapping.ports import parse_unifi_port_config, snapshot_to_inform
from unifi_tlsg.models import get_profile


def test_snapshot_to_inform():
    snap = SwitchSnapshot(
        hostname="sw",
        uptime=100,
        ports=[
            PortStatus(port=1, up=True, enabled=True, speed_mbps=1000, duplex="full", pvid=10),
            PortStatus(port=2, up=False, enabled=True, speed_mbps=0, duplex="full"),
        ],
        mac_table=[],
        vlans=[1, 10],
    )
    ports, _ = snapshot_to_inform(snap, uplink_port=1)
    assert ports[0]["up"] is True
    assert ports[0]["is_uplink"] is True
    assert ports[1]["up"] is False


def test_parse_port_overrides():
    blob = {
        "port_overrides": [
            {
                "port_idx": 3,
                "name": "ap",
                "native_vlan": 10,
                "tagged_vlan_ids": [20, 30],
                "enable": True,
            }
        ]
    }
    desired = parse_unifi_port_config(blob)
    assert len(desired) == 1
    assert desired[0].port == 3
    assert desired[0].native_vlan == 10
    assert desired[0].tagged_vlans == [20, 30]
    assert desired[0].mode == "trunk"


def test_parse_system_cfg_ports():
    blob = {
        "system_cfg": "\n".join(
            [
                "port.1.name=Uplink",
                "port.1.vlan_native=1",
                "port.1.vlan_tagged=10,20",
                "port.2.vlan_native=30",
                "port.2.enabled=false",
            ]
        )
    }
    desired = {p.port: p for p in parse_unifi_port_config(blob)}
    assert desired[1].tagged_vlans == [10, 20]
    assert desired[2].native_vlan == 30
    assert desired[2].enabled is False


def test_apply_port_config_dry_run_commands():
    profile = get_profile("sg2424")
    backend = TlSgCliBackend(
        SwitchCliConfig(host="192.0.2.1", password="x"),
        profile,
        dry_run=True,
    )
    backend.connect()
    # Capture via monkeypatch of logger would be heavy; just ensure no crash.
    backend.apply_port_config(
        [
            DesiredPortConfig(port=1, native_vlan=10, tagged_vlans=[], mode="access"),
            DesiredPortConfig(port=24, native_vlan=1, tagged_vlans=[10, 20], mode="trunk"),
        ]
    )


def test_to_ranges():
    assert _to_ranges([1, 2, 3, 5, 7, 8]) == ["1-3", "5", "7-8"]


def test_profiles_include_sg2424():
    p = get_profile("sg2424")
    assert p.copper_ports == 24
    assert p.is_combo(22)
    assert p.cli_ifname(4) == "1/0/4"
