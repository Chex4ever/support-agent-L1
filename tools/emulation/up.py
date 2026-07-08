#!/usr/bin/env python3
"""CLI: start the emulation stack for a client project.

Usage:
    python -m tools.emulation.up --project <file.irpz> [--sirpz <file.sirpz>]
    python -m tools.emulation.up --knx-only
    python -m tools.emulation.up --mdb-only --config register-init.yaml
    python -m tools.emulation.up --status
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

from .orchestrator import EmulationStack, load_config


def main():
    parser = argparse.ArgumentParser(description="Start emulation stack")
    parser.add_argument("--project", help="Path to .irpz project file")
    parser.add_argument("--sirpz", help="Path to .sirpz file (if different from .irpz)")
    parser.add_argument("--knx-only", action="store_true", help="Start only knx-e")
    parser.add_argument("--mdb-only", action="store_true", help="Start only mdb-e")
    parser.add_argument("--http-only", action="store_true", help="Start only http-mock")
    parser.add_argument("--config", help="Path to emulation config YAML")
    parser.add_argument("--modbus-config",
                        help="Modbus register-init YAML (relative to mdb-e dir)")
    parser.add_argument("--status", action="store_true", help="Show status of running stack")
    parser.add_argument("--stop", action="store_true", help="Stop all emulators")
    parser.add_argument("--timeout", type=int, default=30, help="Wait timeout (seconds)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s %(message)s",
        stream=sys.stdout,
    )
    logger = logging.getLogger("emulation.up")

    cfg = load_config(args.config)
    if args.modbus_config:
        cfg["mdb"]["config"] = args.modbus_config

    skip_knx = args.mdb_only or args.http_only
    skip_mdb = args.knx_only or args.http_only
    skip_http = args.knx_only or args.mdb_only

    if args.knx_only:
        skip_mdb = True
        skip_http = True
    elif args.mdb_only:
        skip_knx = True
        skip_http = True
    elif args.http_only:
        skip_knx = True
        skip_mdb = True

    stack = EmulationStack(cfg)

    if args.stop:
        logger.info("Stopping all emulators...")
        stack.stop()
        return

    if args.status:
        summary = stack.get_summary()
        for name, info in summary.items():
            if "error" in info:
                logger.info("  %s: ERROR - %s", name, info["error"])
            elif "status" in info:
                logger.info("  %s: running, %d devices", name, info.get("devices", 0))
            else:
                logger.info("  %s: %s", name, info)
        return

    logger.info("Starting emulation stack...")
    result = stack.start(skip_knx=skip_knx, skip_mdb=skip_mdb, skip_http=skip_http)
    logger.info("Started: %s", ", ".join(result["started"]))

    logger.info("Waiting for emulators to be ready...")
    ready = stack.wait_ready(timeout=args.timeout)
    for name, ok in ready.items():
        logger.info("  %s: %s", name, "ready" if ok else "TIMEOUT")

    if args.project and stack.knx:
        logger.info("Deploying project %s...", args.project)
        deploy = stack.deploy_project(args.project, args.sirpz)
        if "error" in deploy:
            logger.error("Deploy error: %s", deploy["error"])
        else:
            for emulator, info in deploy["imported"].items():
                if "note" in info:
                    logger.info("  %s: %s", emulator, info["note"])
                else:
                    logger.info("  %s: %d devices", emulator, len(info.get("devices", [])))

    knx_port = cfg["knx"]["web_port"]
    knx_udp = cfg["knx"]["udp_port"]
    mdb_port = cfg["mdb"]["web_port"]
    mdb_modbus = cfg["mdb"]["modbus_port"]
    http_port = cfg["http_mock"]["port"]

    print()
    print("=== Emulation Stack ===")
    print(f"  KNX bus:        UDP {knx_udp} (routing/tunneling)")
    print(f"  KNX web UI:     http://localhost:{knx_port}")
    print(f"  Modbus TCP:     localhost:{mdb_modbus}")
    print(f"  Modbus web UI:  http://localhost:{mdb_port}")
    print(f"  HTTP mock:      http://localhost:{http_port}")
    print(f"  Amp mock:       http://localhost:{http_port}/httpapi.asp")
    print()
    print("Press Ctrl+C to stop all emulators.")
    print()

    def shutdown(signum, frame):
        logger.info("Shutting down...")
        stack.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
