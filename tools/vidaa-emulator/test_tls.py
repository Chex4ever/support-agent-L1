"""Test vidaa-control client against the emulator with TLS."""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from vidaa_tv_emulator import VIDAAEmulatorBroker

ORIGINAL_CERT = os.path.expanduser(
    r"~\AppData\Roaming\Python\Python314\site-packages\vidaa\certs\vidaa_client.pem"
)
ORIGINAL_KEY = os.path.expanduser(
    r"~\AppData\Roaming\Python\Python314\site-packages\vidaa\certs\vidaa_client.key"
)
CERTS_DIR = os.path.join(os.path.dirname(__file__), "certs")


def main():
    print("Starting emulator with TLS...")
    broker = VIDAAEmulatorBroker(
        host="127.0.0.1",
        port=36669,
        server_cert=os.path.join(CERTS_DIR, "server_cert.pem"),
        server_key=os.path.join(CERTS_DIR, "server_key.pem"),
        client_auth="request",
    )
    broker.start()
    time.sleep(1)

    print("Testing with vidaa-control library (TLS)...")
    from vidaa.client import VidaaTV

    tv = VidaaTV(
        host="127.0.0.1",
        port=36669,
        use_dynamic_auth=True,
        mac_address="AA:BB:CC:DD:EE:FF",
        brand="his",
        enable_persistence=False,
        certfile=ORIGINAL_CERT,
        keyfile=ORIGINAL_KEY,
        auto_detect_protocol=False,
    )

    print("Connecting...")
    connected = tv.connect(timeout=10.0, try_fallback=False)
    print(f"  Connected: {connected}")

    if not connected:
        print("FAILED: Could not connect")
        broker.stop()
        return

    print("Getting state...")
    state = tv.get_state(timeout=5.0)
    print(f"  State: {state}")

    print("Starting pairing...")
    if tv.start_pairing():
        print("  Pairing started")
        time.sleep(0.5)
        print("  Authenticating with PIN 1234...")
        if tv.authenticate("1234", timeout=10.0):
            print("  Authenticated!")
        else:
            print("  Auth failed!")
    else:
        print("  Pairing start failed!")

    print("Getting device info...")
    info = tv.get_device_info(timeout=5.0)
    print(f"  Device info: {info}")

    print("Getting TV info...")
    tvinfo = tv.get_tv_info(timeout=5.0)
    print(f"  TV info: {tvinfo}")

    print("Sending keys...")
    tv.send_key("KEY_VOLUME_UP")
    print("  KEY_VOLUME_UP sent")
    tv.send_key("KEY_HOME")
    print("  KEY_HOME sent")

    tv.disconnect()
    broker.stop()
    print("\nAll TLS tests completed!")


if __name__ == "__main__":
    main()
