#!/usr/bin/env python3
"""Python bridge: Hisense VIDAA TV <-> iRidi Server Tags.

Runs on the same machine as iRidi Server (Raspberry Pi / Mini PC / x86).
Connects to the TV via MQTT mTLS and exposes control via Server Tags.

Prerequisites:
    pip install vidaa-control

Server Tags used:
    Server.Tags.TV_Command      - write: "KEY_POWER", "KEY_VOLUME_UP", etc.
    Server.Tags.TV_Volume_Set   - write: "0..100"
    Server.Tags.TV_State        - read: JSON with current TV state
    Server.Tags.TV_Volume       - read: current volume (0-100)
    Server.Tags.TV_Source       - read: current source name

Usage:
    python vidaa_iridi_bridge.py --host <TV_IP> --mac <TV_MAC>
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

# Try to import vidaa-control
try:
    from vidaa import AsyncVidaaTV
    from vidaa.config import TokenStorage
except ImportError:
    print("ERROR: vidaa-control not installed. Run: pip install vidaa-control")
    sys.exit(1)

# Try to import iRidi API (optional - only needed if running on iRidi Server)
try:
    from iridi_server_api import IR  # iRidi Server scripting API
    HAS_IRIDI = True
except ImportError:
    HAS_IRIDI = False
    # Mock IR for testing outside iRidi Server
    class MockIR:
        _tags = {}
        def GetVariable(self, name):
            return self._tags.get(name, "")
        def Log(self, msg):
            print(f"[IR.Log] {msg}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("vidaa_bridge")

# Path for storing tokens
TOKEN_PATH = Path(__file__).parent / "vidaa_tokens.json"


class VidaaIRidiBridge:
    """Bridge between Hisense VIDAA TV and iRidi Server Tags."""

    def __init__(self, host: str, mac: str, port: int = 36669):
        self.host = host
        self.mac = mac
        self.port = port
        self.tv: AsyncVidaaTV = None
        self.running = False

    async def start(self):
        """Start the bridge: connect to TV and begin polling."""
        self.running = True

        storage = TokenStorage(str(TOKEN_PATH))
        self.tv = AsyncVidaaTV(
            host=self.host,
            port=self.port,
            mac_address=self.mac,
            use_dynamic_auth=True,
            enable_persistence=True,
            storage=storage,
        )

        # Connect to TV
        log.info("Connecting to TV at %s:%d...", self.host, self.port)
        if not await self.tv.async_connect(timeout=15.0):
            log.error("Cannot connect to TV. Is it on and on the same network?")
            return False

        log.info("Connected to TV!")

        # Check if we need to pair
        if not self.tv.is_authenticated():
            log.info("Starting pairing...")
            if not await self.tv.async_start_pairing():
                log.error("Cannot start pairing")
                return False
            log.info("Pairing initiated. Enter PIN shown on TV via Server.Tags.TV_PIN")

        return True

    async def stop(self):
        """Stop the bridge."""
        self.running = False
        if self.tv:
            await self.tv.async_disconnect()

    async def handle_pin(self, pin: str):
        """Handle PIN authentication."""
        if await self.tv.async_authenticate(pin, timeout=10.0):
            log.info("Authentication successful!")
            return True
        log.error("Authentication failed")
        return False

    async def process_command(self, command: str):
        """Process a command from Server Tags."""
        if not command:
            return

        cmd = command.strip()
        log.info("Command: %s", cmd)

        try:
            if cmd.startswith("KEY_"):
                await self.tv.async_send_key(cmd)
            elif cmd.startswith("VOLUME_SET:"):
                vol = int(cmd.split(":", 1)[1])
                await self.tv.async_set_volume(max(0, min(100, vol)))
            elif cmd == "VOLUME_UP":
                await self.tv.async_volume_up()
            elif cmd == "VOLUME_DOWN":
                await self.tv.async_volume_down()
            elif cmd == "MUTE":
                await self.tv.async_mute()
            elif cmd.startswith("SOURCE:"):
                source = cmd.split(":", 1)[1]
                await self.tv.async_set_source(source)
            elif cmd.startswith("LAUNCH:"):
                app = cmd.split(":", 1)[1]
                await self.tv.async_launch_app(app)
            elif cmd == "POWER_ON":
                await self.tv.async_power_on()
            elif cmd == "POWER_OFF":
                await self.tv.async_power_off()
            elif cmd.startswith("PIN:"):
                pin = cmd.split(":", 1)[1]
                await self.handle_pin(pin)
            elif cmd == "GET_STATE":
                state = await self.tv.async_get_state(timeout=5.0)
                log.info("State: %s", state)
            elif cmd == "GET_VOLUME":
                vol = await self.tv.async_get_volume(timeout=5.0)
                log.info("Volume: %s", vol)
            elif cmd == "RECONNECT":
                await self.tv.async_disconnect()
                await self.tv.async_connect(timeout=10.0)
            else:
                log.warning("Unknown command: %s", cmd)
        except Exception as e:
            log.error("Error processing command '%s': %s", cmd, e)

    async def poll_state(self, interval: int = 10):
        """Poll TV state periodically."""
        while self.running:
            try:
                if self.tv.is_connected():
                    # Get state
                    state = await self.tv.async_get_state(timeout=5.0)
                    if state:
                        if HAS_IRIDI:
                            IR.GetServer().Set("Server.Tags.TV_State", json.dumps(state))

                    # Get volume
                    volume = await self.tv.async_get_volume(timeout=5.0)
                    if volume is not None:
                        if HAS_IRIDI:
                            IR.GetServer().Set("Server.Tags.TV_Volume", str(volume))
            except Exception as e:
                log.error("Poll error: %s", e)

            await asyncio.sleep(interval)

    async def run(self, poll_interval: int = 10):
        """Main loop: poll commands from Server Tags and update state."""
        if not await self.start():
            return

        poll_task = asyncio.create_task(self.poll_state(poll_interval))

        while self.running:
            try:
                if HAS_IRIDI:
                    command = IR.GetVariable("Server.Tags.TV_Command")
                    if command:
                        await self.process_command(command)
                        IR.GetServer().Set("Server.Tags.TV_Command", "")
                else:
                    await asyncio.sleep(0.5)
            except Exception as e:
                log.error("Loop error: %s", e)
                await asyncio.sleep(5)

        poll_task.cancel()


async def main():
    parser = argparse.ArgumentParser(description="VIDAA TV <-> iRidi Bridge")
    parser.add_argument("--host", required=True, help="TV IP address")
    parser.add_argument("--mac", required=True, help="TV MAC address (e.g. AA:BB:CC:DD:EE:FF)")
    parser.add_argument("--port", type=int, default=36669)
    parser.add_argument("--poll", type=int, default=10, help="State polling interval (seconds)")
    args = parser.parse_args()

    bridge = VidaaIRidiBridge(host=args.host, mac=args.mac, port=args.port)
    await bridge.run(poll_interval=args.poll)


if __name__ == "__main__":
    asyncio.run(main())
