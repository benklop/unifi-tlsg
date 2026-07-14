from pathlib import Path

from unifi_tlsg.backend.cli import parser

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_interface_status():
    text = (FIXTURES / "show_interface_status.txt").read_text()
    ports = parser.parse_interface_status(text)
    assert ports[1].up is True
    assert ports[1].speed_mbps == 1000
    assert ports[2].up is False
    assert ports[3].speed_mbps == 100
    assert ports[22].up is True


def test_parse_interface_switchport():
    text = (FIXTURES / "show_interface_switchport.txt").read_text()
    sp = parser.parse_interface_switchport(text)
    assert sp[1]["pvid"] == 10
    assert 20 in sp[3]["tagged"]
    assert 21 in sp[3]["tagged"]
    assert 30 in sp[3]["tagged"]
    assert sp[24]["tagged"] == [10, 20, 30]


def test_parse_mac_table():
    text = (FIXTURES / "show_mac_table.txt").read_text()
    entries = parser.parse_mac_table(text)
    assert len(entries) == 3
    assert entries[0].port == 1
    assert entries[0].vlan == 10
    assert entries[1].mac == "aa:bb:cc:dd:ee:ff"


def test_vlan_ranges():
    assert parser._parse_vlan_list("2-5,10") == [2, 3, 4, 5, 10]
