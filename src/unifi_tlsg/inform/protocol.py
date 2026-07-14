"""UniFi Inform (TNBU) binary codec.

Packet layout (big-endian):
  magic(4)=TNBU | version(4) | mac(6) | flags(2) | iv(16) | payload_ver(4) | len(4) | payload

Flags:
  0x01 encrypted
  0x02 zlib
  0x04 snappy (legacy; we only emit zlib)
  0x08 AES-GCM (else AES-CBC)

Default authkey is MD5("ubnt") = ba86f2bbe107c7c57eb5f2690775c712.
"""

from __future__ import annotations

import json
import os
import struct
import zlib
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from unifi_tlsg.config import DEFAULT_AUTHKEY, mac_bytes

MAGIC = b"TNBU"
FLAG_ENCRYPTED = 0x01
FLAG_ZLIB = 0x02
FLAG_SNAPPY = 0x04
FLAG_GCM = 0x08
HEADER_LEN = 40


def encode_inform(
    payload: dict[str, Any] | str | bytes,
    mac: str,
    authkey: str = DEFAULT_AUTHKEY,
    *,
    use_gcm: bool = False,
    packet_version: int = 1,
    payload_version: int = 1,
) -> bytes:
    if isinstance(payload, dict):
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    elif isinstance(payload, str):
        raw = payload.encode("utf-8")
    else:
        raw = payload

    compressed = zlib.compress(raw)
    iv = os.urandom(16)
    key = bytes.fromhex(authkey)

    flags = FLAG_ENCRYPTED | FLAG_ZLIB
    if use_gcm:
        flags |= FLAG_GCM
        # Length field includes the 16-byte GCM tag.
        header = _pack_header(mac, flags, iv, packet_version, payload_version, len(compressed) + 16)
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        encryptor.authenticate_additional_data(header)
        ciphertext = encryptor.update(compressed) + encryptor.finalize()
        body = ciphertext + encryptor.tag
        return header + body

    padder = PKCS7(128).padder()
    padded = padder.update(compressed) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    body = encryptor.update(padded) + encryptor.finalize()
    header = _pack_header(mac, flags, iv, packet_version, payload_version, len(body))
    return header + body


def decode_inform(
    packet: bytes,
    authkey: str = DEFAULT_AUTHKEY,
) -> dict[str, Any]:
    if len(packet) < HEADER_LEN:
        raise ValueError("inform packet too short")
    if packet[:4] != MAGIC:
        raise ValueError(f"bad magic {packet[:4]!r}")
    flags = struct.unpack(">H", packet[14:16])[0]
    iv = packet[16:32]
    payload_len = struct.unpack(">I", packet[36:40])[0]
    payload = packet[40 : 40 + payload_len]
    header = packet[:HEADER_LEN]
    key = bytes.fromhex(authkey)

    if flags & FLAG_ENCRYPTED:
        if flags & FLAG_GCM:
            if len(payload) < 16:
                raise ValueError("GCM payload missing tag")
            ciphertext, tag = payload[:-16], payload[-16:]
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
            decryptor = cipher.decryptor()
            decryptor.authenticate_additional_data(header)
            payload = decryptor.update(ciphertext) + decryptor.finalize()
        else:
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            padded = decryptor.update(payload) + decryptor.finalize()
            unpadder = PKCS7(128).unpadder()
            payload = unpadder.update(padded) + unpadder.finalize()

    if flags & FLAG_SNAPPY:
        try:
            import snappy  # type: ignore

            payload = snappy.decompress(payload)
        except ImportError as exc:
            raise RuntimeError("snappy-compressed inform requires python-snappy") from exc
    elif flags & FLAG_ZLIB:
        payload = zlib.decompress(payload)

    return json.loads(payload.decode("utf-8"))


def _pack_header(
    mac: str,
    flags: int,
    iv: bytes,
    packet_version: int,
    payload_version: int,
    payload_len: int,
) -> bytes:
    return (
        MAGIC
        + struct.pack(">I", packet_version)
        + mac_bytes(mac)
        + struct.pack(">H", flags)
        + iv
        + struct.pack(">I", payload_version)
        + struct.pack(">I", payload_len)
    )
