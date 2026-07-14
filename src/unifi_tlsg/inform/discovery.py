"""UDP UniFi discovery (multicast 233.89.188.1:10001) TLV helper."""

from __future__ import annotations

import socket
import struct
import time

from unifi_tlsg.config import mac_bytes


DISCOVERY_ADDR = ("233.89.188.1", 10001)


class UnifiTLV:
    def __init__(self) -> None:
        self._parts: list[bytes] = []

    def add(self, type_id: int, value: bytes) -> None:
        self._parts.append(struct.pack(">BB", type_id, len(value)) + value)

    def build(self, version: int = 2, command: int = 6) -> bytes:
        body = b"".join(self._parts)
        return struct.pack(">BBH", version, command, len(body)) + body


def build_discovery_packet(
    mac: str,
    ip: str,
    model: str,
    firmware: str,
    *,
    index: int = 1,
    platform: str = "USW",
) -> bytes:
    mac_b = mac_bytes(mac)
    ip_b = bytes(int(x) for x in ip.split("."))
    tlv = UnifiTLV()
    tlv.add(1, mac_b)
    tlv.add(2, mac_b + ip_b)
    tlv.add(3, f"{model}.v{firmware}".encode("ascii"))
    tlv.add(10, struct.pack("!I", int(time.time()) % (2**32)))
    tlv.add(11, platform.encode("ascii"))
    tlv.add(12, model.encode("ascii"))
    tlv.add(19, mac_b)
    tlv.add(18, struct.pack("!I", index))
    tlv.add(21, model.encode("ascii"))
    tlv.add(27, firmware.encode("ascii"))
    tlv.add(22, firmware.encode("ascii"))
    return tlv.build()


def send_discovery(packet: bytes, ttl: int = 20) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
        sock.sendto(packet, DISCOVERY_ADDR)
    finally:
        sock.close()
