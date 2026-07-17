"""Start emulator with TLS and keep it running."""
import sys, os, time, logging

sys.path.insert(0, os.path.abspath(r"tools/vidaa-emulator"))
from vidaa_tv_emulator import VIDAAEmulatorBroker

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
abs_cert = os.path.join(SCRIPT_DIR, "certs", "server_cert.pem")
abs_key = os.path.join(SCRIPT_DIR, "certs", "server_key.pem")

# Configure root logger to file
log_file = os.path.join(SCRIPT_DIR, "emu.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log_file, mode="w"), logging.StreamHandler(sys.stdout)]
)

print(f"Cert: {abs_cert} exists={os.path.exists(abs_cert)}")
print(f"Key:  {abs_key} exists={os.path.exists(abs_key)}", flush=True)

broker = VIDAAEmulatorBroker(
    host="0.0.0.0", port=36669,
    server_cert=abs_cert, server_key=abs_key,
)
broker.start()
print("EMULATOR READY: 0.0.0.0:36669 TLS", flush=True)

while True:
    time.sleep(60)
