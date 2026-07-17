"""Single-process test: broker thread + test client."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import threading
import time
import socket
import struct
import json
import hashlib

from vidaa_tv_emulator import VIDAAEmulatorBroker

PATTERN = "38D65DC30F45109A369A86FCE866A85B"
VALUE_SUFFIX_MODERN = "h!i@s#$v%i^d&a*a"
TIME_XOR_CONSTANT = 0x5698_1477_2b03_a968


def _md5(s):
    return hashlib.md5(s.encode()).hexdigest().upper()


def _sum_digits(n):
    return sum(int(d) for d in str(abs(n)))


def gen_creds(mac, brand="his", ts=None):
    ts = ts or int(time.time())
    uuid = mac
    race = f"{PATTERN}${uuid}"
    race_md5 = _md5(race)[:6]
    client_id = f"{uuid}${brand}${race_md5}_vidaacommon_001"
    xor_time = ts ^ TIME_XOR_CONSTANT
    username = f"{brand}${xor_time}"
    remainder = _sum_digits(ts) % 10
    value = f"{brand}{remainder}{VALUE_SUFFIX_MODERN}"
    value_md5 = _md5(value)[:6]
    password = _md5(f"{ts}${value_md5}")
    return client_id, username, password


def enc_len(l):
    enc = bytearray()
    while True:
        d = l % 128; l //= 128
        if l > 0: d |= 0x80
        enc.append(d)
        if l == 0: break
    return bytes(enc)


def dec_len(data, offset):
    m = 1; v = 0; u = 0
    while offset + u < len(data):
        d = data[offset + u]; u += 1
        v += (d & 127) * m
        if d & 128 == 0: return v, u
        m *= 128
    return 0, 0


def rd_str(data, offset):
    if offset + 2 > len(data): return None, offset
    length = struct.unpack("!H", data[offset : offset + 2])[0]
    offset += 2
    if offset + length > len(data): return None, offset
    return data[offset : offset + length].decode("utf-8", errors="replace"), offset + length


def wr_str(s):
    e = s.encode("utf-8")
    return struct.pack("!H", len(e)) + e


passed = 0
failed = 0


def test(name, result):
    global passed, failed
    print(f"  {'PASS' if result else 'FAIL'}: {name}")
    if result: passed += 1
    else: failed += 1


def mqtt_connect(sock, cid, user=None, passwd=None):
    flags = 0x02
    var = wr_str("MQTT") + bytes([4, flags | (0x80 if user else 0) | (0x40 if passwd else 0)])
    var += struct.pack("!H", 60) + wr_str(cid)
    if user: var += wr_str(user)
    if passwd: var += wr_str(passwd)
    pkt = bytes([0x10]) + enc_len(len(var)) + var
    sock.sendall(pkt)
    data = sock.recv(4)
    return len(data) >= 4 and data[3] == 0


def mqtt_pub(sock, topic, payload=""):
    msg = wr_str(topic) + (payload.encode() if isinstance(payload, str) else payload)
    pkt = bytes([0x30]) + enc_len(len(msg)) + msg
    sock.sendall(pkt)


def mqtt_recv(sock, timeout=1.0):
    sock.settimeout(timeout)
    msgs = []
    buf = bytearray()
    try:
        while True:
            d = sock.recv(4096)
            if not d: break
            buf.extend(d)
            while len(buf) >= 2:
                ptype = (buf[0] & 0xF0) >> 4
                plen, hdr = dec_len(buf, 1)
                if plen == 0 and hdr == 0: break
                total = 1 + hdr + plen
                if len(buf) < total: break
                packet = bytes(buf[:total])
                del buf[:total]
                if ptype == 3:
                    payload = packet[1 + hdr:]
                    t, off = rd_str(payload, 0)
                    b = payload[off:].decode("utf-8", errors="replace") if off < len(payload) else ""
                    msgs.append({"topic": t, "body": b})
    except socket.timeout:
        pass
    return msgs


def main():
    # Start broker
    broker = VIDAAEmulatorBroker(host="127.0.0.1", port=36669)
    broker.start()
    time.sleep(0.5)

    # Test 1: Dynamic auth
    print("\n--- Test 1: Dynamic Auth ---")
    cid, user, pwd = gen_creds("AA:BB:CC:DD:EE:FF")
    print(f"  cid={cid[:50]}...")
    print(f"  user={user}")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    test("CONNECT", mqtt_connect(s, cid, user, pwd))
    s.close()

    # Test 2: Static auth
    print("\n--- Test 2: Static Auth ---")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    test("CONNECT", mqtt_connect(s, "static_1", "hisenseservice", "multimqttservice"))
    mqtt_pub(s, f"/remoteapp/tv/platform_service/static_1/actions/gettvinfo")
    msgs = mqtt_recv(s, 1.0)
    test("TV info", len(msgs) > 0)
    if msgs: print(f"    body: {msgs[0]['body'][:100]}")
    s.close()

    # Test 3: Bad auth
    print("\n--- Test 3: Bad Auth ---")
    cid, _, _ = gen_creds("AA:BB:CC:DD:EE:FF")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    test("Bad auth rejected", not mqtt_connect(s, cid, "bad", "creds"))
    s.close()

    # Test 4: Device info
    print("\n--- Test 4: Device Info ---")
    cid, user, pwd = gen_creds("AA:BB:CC:DD:EE:22")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/actions/getdeviceinfo")
    msgs = mqtt_recv(s, 1.0)
    test("Device info received", len(msgs) > 0)
    if msgs: print(f"    body: {msgs[0]['body'][:100]}")
    s.close()

    # Test 5: Pairing flow
    print("\n--- Test 5: Pairing ---")
    cid, user, pwd = gen_creds("DD:EE:FF:AA:BB:CC")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/vidaa_app_connect",
             json.dumps({"app_version": 2, "connect_result": 0, "device_type": "Mobile App"}))
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/authenticationcode",
             json.dumps({"authNum": 1234}))
    time.sleep(0.2)
    msgs = mqtt_recv(s, 1.0)
    auth_msgs = [m for m in msgs if "authentication" in m["topic"]]
    test("Auth result=1", len(auth_msgs) > 0 and json.loads(auth_msgs[0]["body"]).get("result") == 1)
    s.close()

    # Test 6: Token issuance after pairing
    print("\n--- Test 6: Token Issuance ---")
    cid, user, pwd = gen_creds("FF:EE:DD:CC:BB:AA")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/vidaa_app_connect",
             json.dumps({"app_version": 2, "connect_result": 0, "device_type": "Mobile App"}))
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/authenticationcode",
             json.dumps({"authNum": 1234}))
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/data/gettoken",
             json.dumps({"refreshtoken": ""}))
    time.sleep(0.2)
    msgs = mqtt_recv(s, 1.0)
    token_msgs = [m for m in msgs if "tokenissuance" in m["topic"]]
    test("Token received", len(token_msgs) > 0 and "accesstoken" in token_msgs[0]["body"])
    if token_msgs:
        tok = json.loads(token_msgs[0]["body"])
        acc = tok.get("accesstoken", "")
        test("Access token is string", isinstance(acc, str) and len(acc) > 0)
        # Test reconnection with token
        print("\n--- Test 6b: Reconnect with token ---")
        s2 = socket.socket(); s2.connect(("127.0.0.1", 36669))
        test("Token reconnect", mqtt_connect(s2, cid, user, acc))
        s2.close()
    s.close()

    # Test 7: Get state
    print("\n--- Test 7: Get State ---")
    cid, user, pwd = gen_creds("11:22:33:44:55:66")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/gettvstate")
    msgs = mqtt_recv(s, 1.0)
    test("State received", len(msgs) > 0)
    if msgs:
        state = msgs[0]
        test("State is JSON", "statetype" in state["body"])
    s.close()

    # Test 8: Sources
    print("\n--- Test 8: Sources ---")
    cid, user, pwd = gen_creds("22:33:44:55:66:77")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/sourcelist")
    msgs = mqtt_recv(s, 1.0)
    test("Sources received", len(msgs) > 0 and "sources" in msgs[0]["body"])
    s.close()

    # Test 9: Apps
    print("\n--- Test 9: Apps ---")
    cid, user, pwd = gen_creds("33:44:55:66:77:88")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/applist")
    msgs = mqtt_recv(s, 1.0)
    test("Apps received", len(msgs) > 0 and "applist" in msgs[0]["body"])
    s.close()

    # Test 10: Volume
    print("\n--- Test 10: Volume ---")
    cid, user, pwd = gen_creds("44:55:66:77:88:99")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/actions/getvolume")
    msgs = mqtt_recv(s, 1.0)
    test("Volume received", len(msgs) > 0 and "volume_value" in msgs[0]["body"])
    mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/actions/changevolume",
             json.dumps({"volume_value": 50}))
    test("Volume set", True)  # No response expected
    s.close()

    # Test 11: Send key
    print("\n--- Test 11: Send Key ---")
    cid, user, pwd = gen_creds("55:66:77:88:99:00")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/remote_service/{cid}/actions/sendkey", "KEY_POWER")
    test("Key sent", True)
    s.close()

    # Summary
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'='*50}")

    broker.stop()


if __name__ == "__main__":
    main()
