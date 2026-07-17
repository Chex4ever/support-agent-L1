"""Final verification: full pairing + commands cycle via TLS with vidaa-control library."""

import sys, os, time, threading
sys.path.insert(0, os.path.dirname(__file__))
from vidaa_tv_emulator import VIDAAEmulatorBroker

CERT = os.path.expanduser(r"~\AppData\Roaming\Python\Python314\site-packages\vidaa\certs\vidaa_client.pem")
KEY  = os.path.expanduser(r"~\AppData\Roaming\Python\Python314\site-packages\vidaa\certs\vidaa_client.key")
CERTS_DIR = os.path.join(os.path.dirname(__file__), "certs")

def test_with_vidaa_lib():
    """Full test using the real vidaa-control library (TLS)."""
    from vidaa.client import VidaaTV

    tv = VidaaTV(
        host="127.0.0.1", port=36669,
        use_dynamic_auth=True, mac_address="AA:BB:CC:DD:EE:FF", brand="his",
        enable_persistence=False, certfile=CERT, keyfile=KEY,
        auto_detect_protocol=False,
    )

    print("1. Connecting via TLS mTLS...")
    assert tv.connect(timeout=10.0, try_fallback=False), "CONNECT failed"
    print("   OK")

    print("2. Getting state...")
    state = tv.get_state(timeout=5.0)
    assert state and state.get("statetype") == "tvon", f"State unexpected: {state}"
    print(f"   OK: {state}")

    print("3. Getting volume...")
    vol = tv.get_volume(timeout=5.0)
    assert vol is not None, "Volume None"
    print(f"   OK: {vol}")

    print("4. Setting volume to 50...")
    tv.set_volume(50)
    time.sleep(0.3)
    vol2 = tv.get_volume(timeout=5.0)
    print(f"   OK: {vol2}")

    print("5. Starting pairing...")
    assert tv.start_pairing(), "Pairing start failed"
    time.sleep(0.5)

    print("6. Authenticating with PIN 1234...")
    assert tv.authenticate("1234", timeout=10.0), "Auth failed"
    time.sleep(1.0)  # Wait for token response to fully process
    print("   OK")

    print("7. Getting device info...")
    info = tv.get_device_info(timeout=5.0)
    assert info and "model_name" in info, f"Device info missing: {info}"
    print(f"   OK: model={info.get('model_name')}")

    print("8. Getting TV info...")
    tvinfo = tv.get_tv_info(timeout=5.0)
    assert tvinfo and "product_name" in tvinfo, f"TV info missing: {tvinfo}"
    print(f"   OK: product={tvinfo.get('product_name')}")

    print("9. Getting sources...")
    sources = tv.get_sources()
    print(f"   OK: {sources}")

    print("10. Getting apps...")
    apps = tv.get_apps()
    print(f"   OK: {apps}")

    print("11. Sending key up...")
    tv.send_key("KEY_UP")
    time.sleep(0.1)

    print("12. Sending key power...")
    tv.send_key("KEY_POWER")
    time.sleep(0.1)

    print("13. Sending JSON key...")
    tv.send_key("KEY_HOME")
    time.sleep(0.1)

    print("14. Setting source...")
    tv.set_source("hdmi2")
    time.sleep(0.1)

    print("15. Disconnecting...")
    tv.disconnect()
    print("    OK")

    print("\n=== ALL TESTS PASSED ===")
    return True


def main():
    broker = VIDAAEmulatorBroker(
        host="127.0.0.1", port=36669,
        server_cert=os.path.join(CERTS_DIR, "server_cert.pem"),
        server_key=os.path.join(CERTS_DIR, "server_key.pem"),
        client_auth="request",
    )
    broker.start()
    time.sleep(1)
    try:
        test_with_vidaa_lib()
    finally:
        broker.stop()
        time.sleep(0.5)
    print("Emulator stopped cleanly.")


if __name__ == "__main__":
    main()
