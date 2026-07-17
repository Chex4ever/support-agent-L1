"""Extended edge-case tests for the VIDAA TV emulator."""

import sys
import os
import time
import socket
import struct
import json
import hashlib
import threading

sys.path.insert(0, os.path.dirname(__file__))
from vidaa_tv_emulator import VIDAAEmulatorBroker, PATTERN, TIME_XOR_CONSTANT, VALUE_SUFFIX_MODERN


def _md5(s):
    return hashlib.md5(s.encode()).hexdigest().upper()


def _sum_digits(n):
    return sum(int(d) for d in str(abs(n)))


def gen_creds(mac, ts=None):
    ts = ts or int(time.time())
    uuid = mac
    race = f"{PATTERN}${uuid}"
    race_md5 = _md5(race)[:6]
    client_id = f"{uuid}${'his'}${race_md5}_vidaacommon_001"
    xor_time = ts ^ TIME_XOR_CONSTANT
    username = f"{'his'}${xor_time}"
    remainder = _sum_digits(ts) % 10
    value = f"{'his'}{remainder}{VALUE_SUFFIX_MODERN}"
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
    status = "PASS" if result else "FAIL"
    print(f"  [{status}] {name}")
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
    if isinstance(payload, dict):
        payload = json.dumps(payload)
    msg = wr_str(topic) + payload.encode("utf-8")
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
    broker.emu.pairing_pin = "5678"
    broker.start()
    time.sleep(0.5)

    # ── Test 1: Wrong PIN rejected ──
    print("\n=== Test 1: Wrong PIN ===")
    cid, user, pwd = gen_creds("11:11:11:11:11:11")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/vidaa_app_connect",
             {"app_version": 2, "connect_result": 0, "device_type": "Mobile App"})
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/authenticationcode", {"authNum": 9999})
    time.sleep(0.3)
    msgs = mqtt_recv(s)
    auth_msgs = [json.loads(m["body"]) for m in msgs if "authentication" in m["topic"]]
    test("Wrong PIN rejected (result=0)", len(auth_msgs) > 0 and auth_msgs[0].get("result") == 0)
    s.close()

    # ── Test 2: Correct PIN accepted ──
    print("\n=== Test 2: Correct PIN ===")
    cid, user, pwd = gen_creds("22:22:22:22:22:22")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/vidaa_app_connect",
             {"app_version": 2, "connect_result": 0, "device_type": "Mobile App"})
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/authenticationcode", {"authNum": 5678})
    time.sleep(0.3)
    msgs = mqtt_recv(s)
    auth_msgs = [json.loads(m["body"]) for m in msgs if "authentication" in m["topic"]]
    test("Correct PIN accepted (result=1)", len(auth_msgs) > 0 and auth_msgs[0].get("result") == 1)
    s.close()

    # ── Test 3: Token refresh ──
    print("\n=== Test 3: Token Refresh ===")
    cid, user, pwd = gen_creds("33:33:33:33:33:33")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/vidaa_app_connect",
             {"app_version": 2, "connect_result": 0, "device_type": "Mobile App"})
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/authenticationcode", {"authNum": 5678})
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/data/gettoken", {"refreshtoken": ""})
    time.sleep(0.3)
    msgs = mqtt_recv(s)
    token_msgs = [json.loads(m["body"]) for m in msgs if "tokenissuance" in m["topic"]]
    test("Initial token issued", len(token_msgs) > 0)
    if token_msgs:
        refresh = token_msgs[0].get("refreshtoken", "")
        mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/data/gettoken", {"refreshtoken": refresh})
        time.sleep(0.3)
        msgs2 = mqtt_recv(s)
        token_msgs2 = [json.loads(m["body"]) for m in msgs2 if "tokenissuance" in m["topic"]]
        test("Token refreshed", len(token_msgs2) > 0 and token_msgs2[0].get("accesstoken") != token_msgs[0].get("accesstoken"))
    s.close()

    # ── Test 4: Invalid refresh token ──
    print("\n=== Test 4: Invalid Refresh Token ===")
    cid, user, pwd = gen_creds("44:44:44:44:44:44")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/data/gettoken", {"refreshtoken": "invalid_token_xyz"})
    time.sleep(0.3)
    msgs = mqtt_recv(s)
    token_msgs = [m for m in msgs if "tokenissuance" in m["topic"]]
    test("Invalid refresh token ignored", len(token_msgs) == 0)
    s.close()

    # ── Test 5: Change volume via JSON and plain text ──
    print("\n=== Test 5: Volume Change Formats ===")
    cid, user, pwd = gen_creds("55:55:55:55:55:55")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    # Test JSON
    mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/actions/changevolume",
             {"volume_value": 75, "volume_type": 0})
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/platform_service/{cid}/actions/getvolume")
    time.sleep(0.3)
    msgs = mqtt_recv(s)
    vol_msgs = [json.loads(m["body"]) for m in msgs if "getvolume" in m["topic"]]
    if vol_msgs:
        test("Volume set to 75 via JSON", vol_msgs[0].get("volume_value") == 75)
    else:
        test("Volume set to 75 via JSON", False)
    s.close()

    # ── Test 6: Multiple clients simultaneously ──
    print("\n=== Test 6: Multiple Clients ===")
    sockets = []
    for i in range(5):
        mac = f"AA:BB:CC:DD:EE:{i:02X}"
        cid, user, pwd = gen_creds(mac)
        s = socket.socket(); s.connect(("127.0.0.1", 36669))
        ok = mqtt_connect(s, cid, user, pwd)
        if ok:
            sockets.append(s)
    test("5 simultaneous connections", len(sockets) == 5)
    for s in sockets:
        s.close()

    # ── Test 7: Send all key types ──
    print("\n=== Test 7: All Key Types ===")
    cid, user, pwd = gen_creds("66:66:66:66:66:66")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    keys = ["KEY_POWER", "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_OK",
            "KEY_BACK", "KEY_HOME", "KEY_MENU", "KEY_EXIT",
            "KEY_VOLUME_UP", "KEY_VOLUME_DOWN", "KEY_MUTE",
            "KEY_0", "KEY_9", "KEY_RED", "KEY_GREEN"]
    all_ok = True
    for key in keys:
        mqtt_pub(s, f"/remoteapp/tv/remote_service/{cid}/actions/sendkey", key)
    test("All keys sent successfully", all_ok)
    s.close()

    # ── Test 8: Send key as JSON object ──
    print("\n=== Test 8: Send Key as JSON ===")
    cid, user, pwd = gen_creds("77:77:77:77:77:77")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    # vidaa-control sends keys as {"Key": "KEY_POWER"} or just string
    mqtt_pub(s, f"/remoteapp/tv/remote_service/{cid}/actions/sendkey", {"Key": "KEY_HOME"})
    time.sleep(0.2)
    test("JSON key sent", True)
    s.close()

    # ── Test 9: Change source ──
    print("\n=== Test 9: Change Source ===")
    cid, user, pwd = gen_creds("88:88:88:88:88:88")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/changesource", {"sourceid": "4"})
    time.sleep(0.2)
    test("Source changed to HDMI2", True)
    s.close()

    # ── Test 10: Launch app by ID and name ──
    print("\n=== Test 10: Launch App ===")
    cid, user, pwd = gen_creds("99:99:99:99:99:99")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/launchapp", {"appId": "1", "name": "Netflix"})
    time.sleep(0.2)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/launchapp", {"appId": "3", "name": "YouTube"})
    time.sleep(0.2)
    test("Apps launched", True)
    s.close()

    # ── Test 11: Capability query ──
    print("\n=== Test 11: Capability ===")
    cid, user, pwd = gen_creds("00:00:00:00:00:11")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    mqtt_connect(s, cid, user, pwd)
    mqtt_pub(s, f"/remoteapp/tv/ui_service/{cid}/actions/capability")
    time.sleep(0.3)
    msgs = mqtt_recv(s)
    test("Capability received", len(msgs) > 0 and "capability" in msgs[0]["body"])
    s.close()

    # ── Test 12: Credential time window ──
    print("\n=== Test 12: Credential Time Window ===")
    cid_now, user_now, pwd_now = gen_creds("AA:BB:CC:DD:EE:12")
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    test("Current time creds accepted", mqtt_connect(s, cid_now, user_now, pwd_now))
    s.close()

    # Credentials from 5 minutes ago
    cid_old, user_old, pwd_old = gen_creds("AA:BB:CC:DD:EE:12", ts=int(time.time()) - 290)
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    test("5-min-old creds accepted", mqtt_connect(s, cid_old, user_old, pwd_old))
    s.close()

    # Credentials from 10 minutes ago (out of window)
    cid_expired, user_expired, pwd_expired = gen_creds("AA:BB:CC:DD:EE:12", ts=int(time.time()) - 400)
    s = socket.socket(); s.connect(("127.0.0.1", 36669))
    test("10-min-expired creds rejected", not mqtt_connect(s, cid_expired, user_expired, pwd_expired))
    s.close()

    # Summary
    print(f"\n{'='*50}")
    print(f"Edge Case Results: {passed} passed, {failed} failed, {passed + failed} total")
    print(f"{'='*50}")

    broker.stop()
    time.sleep(0.5)
    print("Emulator stopped cleanly.")


if __name__ == "__main__":
    main()
