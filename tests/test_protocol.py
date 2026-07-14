from unifi_tlsg.inform.protocol import decode_inform, encode_inform


def test_roundtrip_cbc():
    payload = {"_type": "noop", "interval": 10, "mac": "00:11:22:33:44:55"}
    packet = encode_inform(payload, "00:11:22:33:44:55", use_gcm=False)
    assert packet[:4] == b"TNBU"
    decoded = decode_inform(packet)
    assert decoded["_type"] == "noop"
    assert decoded["interval"] == 10


def test_roundtrip_gcm():
    payload = {"hostname": "sw1", "state": 2}
    packet = encode_inform(payload, "aa:bb:cc:dd:ee:ff", use_gcm=True)
    decoded = decode_inform(packet)
    assert decoded["hostname"] == "sw1"
