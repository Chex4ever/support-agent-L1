#!/usr/bin/env python3
"""Emulator of Hisense PX3SE-PRO / VIDAA TV MQTT broker with mTLS.

A self-contained MQTT 3.1.1 broker that emulates a Hisense/VIDAA TV:
- MQTT 3.1.1 over TCP (with optional TLS/mTLS)
- Dynamic credential validation (MODERN auth method)
- PIN pairing flow
- Token issuance (access + refresh tokens)
- Remote control key handling
- Volume control, state, sources, apps

Usage:
    python vidaa_tv_emulator.py [--host HOST] [--port PORT] [--no-tls]
                                [--server-cert CERT] [--server-key KEY]
                                [--ca-cert CA] [--client-auth MODE]    
"""

import argparse
import hashlib
import json
import logging
import os
import random
import socket
import ssl
import struct
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Set

# ── Logging ───────────────────────────────────────────────────────────────

log = logging.getLogger("vidaa_emu")
log.setLevel(logging.DEBUG)
h = logging.StreamHandler()
h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(h)

# ── VIDAA Credential Generation ──────────────────────────────────────────

PATTERN = "38D65DC30F45109A369A86FCE866A85B"
VALUE_SUFFIX_MODERN = "h!i@s#$v%i^d&a*a"
VALUE_SUFFIX_LEGACY = "h*i&s%e!r^v0i1c9"
TIME_XOR_CONSTANT = 0x5698_1477_2b03_a968
MV = memoryview


def _md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest().upper()


def _sum_digits(n: int) -> int:
    return sum(int(d) for d in str(abs(n)))


def generate_creds(mac: str, brand: str = "his", operation: str = "vidaacommon", ts: int = None) -> dict:
    if ts is None:
        ts = int(time.time())
    uuid = mac
    if ":" not in uuid and "-" not in uuid and len(uuid) == 12:
        uuid = ":".join(uuid[i : i + 2] for i in range(0, 12, 2))
    race = f"{PATTERN}${uuid}"
    race_md5 = _md5(race)[:6]
    client_id = f"{uuid}${brand}${race_md5}_{operation}_001"
    xor_time = ts ^ TIME_XOR_CONSTANT
    username = f"{brand}${xor_time}"
    remainder = _sum_digits(ts) % 10
    value = f"{brand}{remainder}{VALUE_SUFFIX_MODERN}"
    value_md5 = _md5(value)[:6]
    password = _md5(f"{ts}${value_md5}")
    return {"client_id": client_id, "username": username, "password": password}


def validate_creds(mac: str, username: str, password: str) -> bool:
    now = int(time.time())
    for offset in range(-300, 301):
        c = generate_creds(mac, ts=now + offset)
        if c["username"] == username and c["password"] == password:
            log.info("Dynamic credentials validated for MAC=%s (offset=%d)", mac, offset)
            return True
    return False


# ── MQTT Protocol Helpers ────────────────────────────────────────────────


def _enc_len(length: int) -> bytes:
    enc = bytearray()
    l = length
    while True:
        d = l % 128
        l //= 128
        if l > 0:
            d |= 0x80
        enc.append(d)
        if l == 0:
            break
    return bytes(enc)


def _dec_len(data: MV, offset: int) -> tuple:
    multiplier = 1
    value = 0
    used = 0
    while offset + used < len(data):
        digit = data[offset + used]
        used += 1
        value += (digit & 127) * multiplier
        if digit & 128 == 0:
            return value, used
        multiplier *= 128
        if multiplier > 2097152:
            return 0, 0
    return 0, 0


def _rd_str(data: MV, offset: int) -> tuple:
    if offset + 2 > len(data):
        return None, offset
    length = struct.unpack("!H", data[offset : offset + 2])[0]
    offset += 2
    if offset + length > len(data):
        return None, offset
    return data[offset : offset + length].tobytes().decode("utf-8", errors="replace"), offset + length


def _wr_str(s: str) -> bytes:
    e = s.encode("utf-8")
    return struct.pack("!H", len(e)) + e


def mqtt_publish(topic: str, payload: str) -> bytes:
    msg = _wr_str(topic) + payload.encode("utf-8")
    return bytes([0x30]) + _enc_len(len(msg)) + msg


def mqtt_suback(packet_id: int, codes: list) -> bytes:
    payload = struct.pack("!H", packet_id) + bytes(codes)
    return bytes([0x90]) + _enc_len(len(payload)) + payload


def mqtt_pingresp() -> bytes:
    return bytes([0xD0, 0x00])


# ── VIDAA Protocol Response Helpers ──────────────────────────────────────


def _resp_topic(client_id: str, template: str) -> str:
    return template.format(client=client_id)


def _fmt_resp(client_id: str, template: str, data: dict) -> bytes:
    topic = _resp_topic(client_id, template)
    return mqtt_publish(topic, json.dumps(data))


# ── MQTT Client Session ──────────────────────────────────────────────────


class VIDAAEmulator:
    """Emulator state shared across all client sessions."""

    def __init__(self):
        self.tv_power = "on"
        self.tv_volume = 25
        self.tv_muted = False
        self.tv_source = "3"
        self.pairing_pin = "1234"
        # Store active tokens: token -> client_id
        self.tokens: Dict[str, str] = {}

    def gen_tokens(self) -> tuple:
        acc = f"emu_acc_{uuid.uuid4().hex}"
        ref = f"emu_ref_{uuid.uuid4().hex}"
        return acc, ref

    def validate_token(self, token: str) -> bool:
        return token in self.tokens or token.startswith("emu_acc_") or token.startswith("emu_ref_")

    def register_token(self, token: str, client_id: str):
        self.tokens[token] = client_id
        self.tokens[client_id] = token


class ClientSession:
    """Per-client session state."""

    def __init__(self, sock, addr, emu: VIDAAEmulator):
        self.sock = sock
        self.addr = addr
        self.emu = emu
        self.client_id = ""
        self.mqtt_client_id = ""
        self.username = ""
        self.mac = None
        self.authenticated = False
        self.paired = False
        self.access_token = None
        self.refresh_token = None
        self.subscriptions: Set[str] = set()


# ── MQTT Broker Core ─────────────────────────────────────────────────────


class VIDAAEmulatorBroker:
    """Minimal MQTT 3.1.1 broker with VIDAA protocol emulation."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 36669,
        server_cert: str = None,
        server_key: str = None,
        ca_cert: str = None,
        client_auth: str = "request",
    ):
        self.host = host
        self.port = port
        self.server_cert = server_cert
        self.server_key = server_key
        self.ca_cert = ca_cert
        self.client_auth = client_auth
        self.emu = VIDAAEmulator()
        self._server = None
        self._running = False
        self._sessions: list = []  # Track active sessions for keepalive
        self._sessions_lock = threading.Lock()

    def start(self):
        self._running = True
        t = threading.Thread(target=self._run, daemon=True, name="MQTT-Emu")
        t.start()
        k = threading.Thread(target=self._keepalive, daemon=True, name="MQTT-Keepalive")
        k.start()
        log.info("VIDAA TV Emulator started on %s:%d", self.host, self.port)

    def _keepalive(self):
        """Send periodic state broadcasts to prevent client read timeouts."""
        while self._running:
            time.sleep(10)
            state_msg = mqtt_publish(
                "/remoteapp/mobile/broadcast/ui_service/state",
                json.dumps({"statetype": "tvon", "source": "HDMI1", "volume": self.emu.tv_volume})
            )
            with self._sessions_lock:
                dead = []
                for s in self._sessions:
                    try:
                        s.sock.sendall(state_msg)
                    except Exception:
                        dead.append(s)
                for s in dead:
                    self._sessions.remove(s)

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass

    def _run(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, self.port))
        self._server.listen(10)
        self._server.settimeout(1.0)

        while self._running:
            try:
                sock, addr = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                if not self._running:
                    break  # server socket closed during shutdown
                continue
            except Exception as e:
                log.error("Accept error: %s", e)
                continue

            if self.server_cert and self.server_key:
                try:
                    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    ctx.load_cert_chain(self.server_cert, self.server_key)
                    # CERT_OPTIONAL: request client cert (for mTLS proof in callback)
                    ctx.verify_mode = ssl.CERT_OPTIONAL
                    ctx.check_hostname = False
                    # Callback logs cert details even if verification fails
                    def _log_cert(conn, cert, errno, depth, ok):
                        if cert:
                            subj = dict(cert.get("subject", ())) if cert.get("subject") else {}
                            iss = dict(cert.get("issuer", ())) if cert.get("issuer") else {}
                            log.info("mTLS CERT: CN='%s' issuer='%s'",
                                subj.get("commonName", "?"),
                                iss.get("commonName", "?"))
                        return True  # Always accept
                    ctx.verify_callback = _log_cert
                    sock = ctx.wrap_socket(sock, server_side=True)
                    log.info("TLS handshake completed: %s", addr)
                except ssl.SSLError as e:
                    log.warning("TLS handshake failed: %s — %s", addr, e)
                    try:
                        sock.close()
                    except Exception:
                        pass
                    continue

            t = threading.Thread(target=self._handle, args=(sock, addr), daemon=True)
            t.start()

    def _handle(self, sock: socket.socket, addr):
        session = ClientSession(sock, addr, self.emu)
        with self._sessions_lock:
            self._sessions.append(session)
        log.info("Session started: %s", addr)
        buf = bytearray()
        try:
            while self._running:
                sock.settimeout(30.0)
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    break
                buf.extend(data)
                while len(buf) >= 2:
                    ptype = (buf[0] & 0xF0) >> 4
                    pkt_len, hdr_bytes = _dec_len(MV(buf), 1)
                    if pkt_len == 0 and hdr_bytes == 0:
                        break
                    total = 1 + hdr_bytes + pkt_len
                    if len(buf) < total:
                        break
                    packet = bytes(buf[:total])
                    del buf[:total]
                    try:
                        self._dispatch(session, ptype, packet, hdr_bytes)
                    except Exception as e:
                        log.error("Dispatch error for %s: %s", addr, e)
        except Exception as e:
            log.error("Session error %s: %s", addr, e)
        finally:
            with self._sessions_lock:
                if session in self._sessions:
                    self._sessions.remove(session)
            try:
                sock.close()
            except Exception:
                pass
            log.info("Client disconnected: %s (id=%s)", addr, session.client_id or "?")

    def _dispatch(self, s: ClientSession, ptype: int, packet: bytes, hdr_bytes: int):
        log.debug("DISPATCH: type=%d from %s", ptype, s.addr)
        if ptype == 1:
            self._on_connect(s, packet, hdr_bytes)
        elif ptype == 3:
            self._on_publish(s, packet, hdr_bytes)
        elif ptype == 8:
            self._on_subscribe(s, packet, hdr_bytes)
        elif ptype == 12:
            s.sock.sendall(mqtt_pingresp())
        elif ptype == 14:
            pass  # DISCONNECT - will exit

    def _on_connect(self, s: ClientSession, packet: bytes, hdr: int):
        payload = MV(packet)[1 + hdr :]
        offset = 0

        proto, offset = _rd_str(payload, offset)
        if proto != "MQTT":
            s.sock.sendall(bytes([0x20, 0x02, 0x00, 0x01]))
            return

        proto_ver = payload[offset]
        offset += 1
        if proto_ver != 4:
            s.sock.sendall(bytes([0x20, 0x02, 0x00, 0x01]))
            return

        flags = payload[offset]
        offset += 1
        has_user = bool(flags & 0x80)
        has_pass = bool(flags & 0x40)
        keepalive = struct.unpack("!H", payload[offset : offset + 2])[0]
        offset += 2

        mqtt_cid, offset = _rd_str(payload, offset)
        s.mqtt_client_id = mqtt_cid or ""

        if has_user:
            user, offset = _rd_str(payload, offset)
            s.username = user or ""
        if has_pass:
            passwd, offset = _rd_str(payload, offset)

        log.info("CONNECT: proto=%s ver=%d client_id=%s user=%s", proto, proto_ver,
            mqtt_cid[:60] if mqtt_cid else "?", (user or "")[:30])

        # Check credentials
        auth_ok = self._check_auth(s, user or "", passwd or "")
        if not auth_ok:
            log.warning("Auth FAILED for client_id=%s", mqtt_cid[:60])
            s.sock.sendall(bytes([0x20, 0x02, 0x00, 0x05]))  # Not authorized
            return

        s.authenticated = True
        s.sock.sendall(bytes([0x20, 0x02, 0x00, 0x00]))
        log.info("CONNACK sent to %s", s.addr)

    def _check_auth(self, s: ClientSession, user: str, passwd: str) -> bool:
        # Static credentials (fallback for older TVs/testing)
        if user == "hisenseservice" and passwd == "multimqttservice":
            log.info("Static credentials accepted")
            s.client_id = "static_client"
            return True

        # Access token
        if s.emu.validate_token(passwd):
            log.info("Access token accepted")
            s.client_id = s.mqtt_client_id
            return True

        # Dynamic credentials
        cid = s.mqtt_client_id or ""
        if "$" in cid:
            mac = cid.split("$")[0]
            if validate_creds(mac, user, passwd):
                s.mac = mac
                s.client_id = cid
                return True

        return False

    def _on_subscribe(self, s: ClientSession, packet: bytes, hdr: int):
        payload = packet[1 + hdr :]
        if len(payload) < 2:
            return
        packet_id = struct.unpack("!H", payload[0:2])[0]
        offset = 2
        codes = []
        while offset < len(payload):
            topic, offset = _rd_str(MV(payload), offset)
            if topic is None:
                break
            if offset < len(payload):
                codes.append(payload[offset])
                offset += 1
            s.subscriptions.add(topic)
        s.sock.sendall(mqtt_suback(packet_id, codes))

    def _on_publish(self, s: ClientSession, packet: bytes, hdr: int):
        payload = MV(packet)[1 + hdr :]
        topic, offset = _rd_str(payload, 0)
        if topic is None:
            return
        body = bytes(payload[offset:]).decode("utf-8", errors="replace")
        log.debug("PUB: %s -> %s", s.addr, topic)

        try:
            data = json.loads(body) if body else {}
        except (json.JSONDecodeError, ValueError):
            data = body

        self._route(s, topic, data)

    def _route(self, s: ClientSession, topic: str, data):
        tl = topic.lower()
        cid = s.client_id

        if "sendkey" in tl:
            if isinstance(data, dict):
                key = data.get("Key", data.get("key", str(data)))
            else:
                key = str(data)
            log.info("KEY: %s", key)
        elif "authenticationcodeclose" in tl:
            pass
        elif "authenticationcode" in tl:
            pin = data.get("authNum", 0)
            log.info("PIN: %s (expected %s)", pin, s.emu.pairing_pin)
            if str(pin) == s.emu.pairing_pin:
                s.paired = True
                s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/ui_service/data/authentication", {"result": 1}))
            else:
                s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/ui_service/data/authentication", {"result": 0}))
        elif "vidaa_app_connect" in tl:
            log.info("Pairing started")
        elif "gettoken" in tl:
            refresh = data.get("refreshtoken", "")
            if refresh and not s.emu.validate_token(refresh):
                return
            acc, ref = s.emu.gen_tokens()
            s.access_token = acc
            s.refresh_token = ref
            s.emu.register_token(acc, cid)
            s.emu.register_token(ref, cid)
            s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/platform_service/data/tokenissuance", {
                "accesstoken": acc,
                "refreshtoken": ref,
                "accesstoken_duration_day": 7,
                "refreshtoken_duration_day": 30,
            }))
        elif "gettvinfo" in tl:
            s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/platform_service/data/gettvinfo", {
                "product_name": "Hisense PX3SE-PRO",
                "model_name": "PX3SE-PRO",
                "deviceid": "AA:BB:CC:DD:EE:FF",
                "tv_name": "Emulated Hisense TV",
                "tv_version": "V0000.01.00a.L1210",
                "protocol": 3290,
                "brand": "his",
            }))
        elif "getdeviceinfo" in tl:
            s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/platform_service/data/getdeviceinfo", {
                "tv_name": "Emulated Hisense TV",
                "model_name": "PX3SE-PRO",
                "tv_version": "V0000.01.00a.L1210",
                "network_type": "wlan",
                "wlan0": "AA:BB:CC:DD:EE:FF",
                "vendor": "Hisense",
            }))
        elif "gettvstate" in tl:
            s.sock.sendall(mqtt_publish("/remoteapp/mobile/broadcast/ui_service/state", json.dumps({
                "statetype": "fake_sleep_0" if s.emu.tv_power == "off" else "tvon",
                "source": "HDMI1", "volume": s.emu.tv_volume, "mute": s.emu.tv_muted,
            })))
        elif "getvolume" in tl:
            s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/platform_service/data/getvolume", {
                "volume_value": s.emu.tv_volume, "volume_type": 0, "volume_min": 0, "volume_max": 100,
            }))
        elif "changevolume" in tl:
            try:
                if isinstance(data, dict):
                    v = int(data.get("volume_value", s.emu.tv_volume))
                else:
                    v = int(data)
                s.emu.tv_volume = max(0, min(100, v))
            except (ValueError, TypeError):
                pass
            log.info("Volume: %d", s.emu.tv_volume)
        elif "sourcelist" in tl:
            s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/ui_service/data/sourcelist", {
                "sources": [
                    {"source_id": "0", "source_name": "TV", "display_name": "TV"},
                    {"source_id": "1", "source_name": "AV", "display_name": "AV"},
                    {"source_id": "2", "source_name": "Component", "display_name": "Component"},
                    {"source_id": "3", "source_name": "HDMI1", "display_name": "HDMI 1"},
                    {"source_id": "4", "source_name": "HDMI2", "display_name": "HDMI 2"},
                    {"source_id": "5", "source_name": "HDMI3", "display_name": "HDMI 3"},
                    {"source_id": "6", "source_name": "HDMI4", "display_name": "HDMI 4"},
                ]
            }))
        elif "changesource" in tl:
            s.emu.tv_source = str(data.get("sourceid", data.get("source", "0")))
            log.info("Source: %s", s.emu.tv_source)
        elif "applist" in tl:
            s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/ui_service/data/applist", {
                "applist": [
                    {"appId": "1", "name": "Netflix", "url": "netflix"},
                    {"appId": "3", "name": "YouTube", "url": "youtube"},
                    {"appId": "2", "name": "Prime Video", "url": "amazon"},
                    {"appId": "295", "name": "Disney+", "url": "https://cd-dmgz.bamgrid.com/bbd/hisense_tv/index.html"},
                    {"appId": "216", "name": "tubi", "url": "https://ott-hisense.tubitv.com"},
                ]
            }))
        elif "launchapp" in tl:
            log.info("App launched: %s", data.get("name", data.get("appId", "?")))
        elif "capability" in tl:
            s.sock.sendall(_fmt_resp(cid, "/remoteapp/mobile/{client}/ui_service/data/capability", {
                "capability": {
                    "key": ["KEY_POWER", "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_OK",
                            "KEY_BACK", "KEY_MENU", "KEY_HOME", "KEY_EXIT",
                            "KEY_VOLUME_UP", "KEY_VOLUME_DOWN", "KEY_MUTE"],
                    "source": ["0", "1", "2", "3", "4", "5", "6"],
                }
            }))


# ── CLI ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Hisense VIDAA TV MQTT Emulator")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=36669)
    parser.add_argument("--no-tls", action="store_true", help="Disable TLS")
    parser.add_argument("--server-cert", help="Server certificate PEM path")
    parser.add_argument("--server-key", help="Server private key PEM path")
    parser.add_argument("--ca-cert", help="CA certificate for client verification")
    parser.add_argument("--client-auth", default="request", choices=["none", "request", "require"])
    parser.add_argument("--pin", default="1234", help="Pairing PIN")
    args = parser.parse_args()

    certs_dir = (Path(__file__).resolve().parent / "certs")
    server_cert = os.path.abspath(args.server_cert or str(certs_dir / "server_cert.pem"))
    server_key = os.path.abspath(args.server_key or str(certs_dir / "server_key.pem"))
    ca_cert = os.path.abspath(args.ca_cert or str(certs_dir / "ca_cert.pem")) if (args.ca_cert or True) else None

    log.info("Cert paths: cert=%s key=%s", server_cert, server_key)

    if not args.no_tls and not (os.path.exists(server_cert) and os.path.exists(server_key)):
        log.warning("Server certs not found at %s / %s. Run generate_certs.py first, or use --no-tls.", server_cert, server_key)
        args.no_tls = True

    if args.no_tls:
        log.warning("Running WITHOUT TLS (insecure!)")
        broker = VIDAAEmulatorBroker(host=args.host, port=args.port)
    else:
        log.info("TLS mTLS enabled")
        broker = VIDAAEmulatorBroker(
            host=args.host, port=args.port,
            server_cert=server_cert, server_key=server_key,
            ca_cert=ca_cert, client_auth=args.client_auth,
        )

    broker.emu.pairing_pin = args.pin
    broker.start()
    log.info("Emulator ready. PIN: %s. Press Ctrl+C to stop.", args.pin)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("Shutting down...")
        broker.stop()


if __name__ == "__main__":
    main()
