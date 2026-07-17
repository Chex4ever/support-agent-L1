"""Orchestrator — manage knx-e + mdb-e + http-mock as a unified emulation stack."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from .knx_client import KnxClient
from .mdb_client import MdbClient
from .bacnet_client import BacnetClient
from .http_mock import app as http_mock_app

logger = logging.getLogger("emulation.orchestrator")

DEFAULT_CONFIG = {
    "knx": {
        "dir": os.environ.get("KNX_E_DIR", r"C:\iridi\knx-e"),
        "web_port": 8001,
        "udp_port": 3671,
    },
    "mdb": {
        "dir": os.environ.get("MDB_E_DIR", r"C:\iridi\mdb-e"),
        "web_port": 7999,
        "modbus_port": 502,
        "config": "register-init.yaml",
    },
    "http_mock": {
        "port": 8002,
    },
    "bacnet": {
        "dir": os.environ.get("BACNET_E_DIR", r"C:\iridi\bacnet-e"),
        "web_port": 8003,
        "udp_port": 47808,
    },
}


def load_config(path: str | None = None) -> dict[str, Any]:
    if path and Path(path).exists():
        with open(path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        for section in ("knx", "mdb", "http_mock", "bacnet"):
            if section not in cfg:
                cfg[section] = DEFAULT_CONFIG[section]
            else:
                merged = dict(DEFAULT_CONFIG[section])
                merged.update(cfg[section])
                cfg[section] = merged
        return cfg
    return dict(DEFAULT_CONFIG)


class EmulationStack:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._processes: list[subprocess.Popen] = []
        self.knx: KnxClient | None = None
        self.mdb: MdbClient | None = None
        self.bacnet: BacnetClient | None = None

    def _start_subprocess(self, cwd: str, *args: str) -> subprocess.Popen:
        logger.info("Starting: %s in %s", " ".join(args), cwd)
        proc = subprocess.Popen(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        self._processes.append(proc)
        return proc

    def start(self, skip_knx: bool = False, skip_mdb: bool = False,
              skip_http: bool = False, skip_bacnet: bool = False) -> dict[str, Any]:
        started: list[str] = []

        if not skip_knx:
            knx_cfg = self.config["knx"]
            self._start_subprocess(
                knx_cfg["dir"],
                sys.executable, "knx-e.py",
                "--web", "--emulator",
                "--port", str(knx_cfg["web_port"]),
                "--udp-port", str(knx_cfg["udp_port"]),
            )
            self.knx = KnxClient(f"http://localhost:{knx_cfg['web_port']}")
            started.append("knx-e")

        if not skip_mdb:
            mdb_cfg = self.config["mdb"]
            args = [sys.executable, "main.py"]
            config_path = Path(mdb_cfg["dir"]) / mdb_cfg["config"]
            if config_path.exists():
                args.extend(["--config", str(config_path)])
            if mdb_cfg["modbus_port"] != 502:
                args.extend(["--modbus-port", str(mdb_cfg["modbus_port"])])
            self._start_subprocess(mdb_cfg["dir"], *args)
            self.mdb = MdbClient(f"http://localhost:{mdb_cfg['web_port']}")
            started.append("mdb-e")

        if not skip_http:
            import uvicorn
            http_port = self.config["http_mock"]["port"]
            logger.info("Starting http-mock on port %s", http_port)
            cfg = uvicorn.Config(http_mock_app, host="0.0.0.0", port=http_port,
                                 log_level="info")
            server = uvicorn.Server(cfg)
            import threading
            t = threading.Thread(target=server.run, daemon=True)
            t.start()
            started.append("http-mock")

        if not skip_bacnet:
            bacnet_cfg = self.config["bacnet"]
            self._start_subprocess(
                bacnet_cfg["dir"],
                sys.executable, "bacnet-e.py",
                "--web-port", str(bacnet_cfg["web_port"]),
                "--port", str(bacnet_cfg["udp_port"]),
            )
            self.bacnet = BacnetClient(f"http://localhost:{bacnet_cfg['web_port']}")
            started.append("bacnet-e")

        return {"started": started}

    def wait_ready(self, timeout: float = 30) -> dict[str, bool]:
        result: dict[str, bool] = {}
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            statuses = {}
            if self.knx:
                try:
                    s = self.knx.status()
                    statuses["knx-e"] = s.get("running", False)
                except Exception:
                    statuses["knx-e"] = False
            if self.mdb:
                try:
                    self.mdb.status()
                    statuses["mdb-e"] = True
                except Exception:
                    statuses["mdb-e"] = False
            if self.bacnet:
                try:
                    s = self.bacnet.status()
                    statuses["bacnet-e"] = s.get("running", False)
                except Exception:
                    statuses["bacnet-e"] = False
            result.update(statuses)
            if all(result.values()):
                return result
            time.sleep(0.5)
        return result

    def deploy_project(self, irpz_path: str, sirpz_path: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {"imported": {}}
        path = Path(irpz_path)
        if not path.exists():
            return {"error": f"File not found: {irpz_path}"}

        if self.knx:
            sirpz = sirpz_path or str(path)
            if path.suffix.lower() in (".knxproj",):
                r = self.knx.import_knxproj(str(path))
            else:
                r = self.knx.import_sirpz(sirpz)
            result["imported"]["knx-e"] = {
                "ok": True,
                "response": r,
                "devices": self.knx.get_devices(),
            }

        if self.mdb:
            from tools.project.analyze_irpz import analyze
            mdb_config = self._build_mdb_config(irpz_path)
            if mdb_config["devices"]:
                r = self.mdb.import_config(mdb_config)
                self.mdb.clear_project()
                r = self.mdb.import_config(mdb_config)
                result["imported"]["mdb-e"] = {
                    "ok": True,
                    "response": r,
                    "devices": self.mdb.get_devices(),
                }
            else:
                result["imported"]["mdb-e"] = {"ok": True, "note": "no Modbus devices found"}

        return result

    def _build_mdb_config(self, irpz_path: str) -> dict[str, Any]:
        try:
            from ..project.analyze_irpz import analyze
        except ImportError:
            return {"devices": []}
        return {"devices": []}

    def get_summary(self) -> dict[str, Any]:
        summary: dict[str, Any] = {}
        if self.knx:
            try:
                s = self.knx.status()
                devs = self.knx.get_devices()
                summary["knx-e"] = {"status": s, "devices": len(devs)}
            except Exception as e:
                summary["knx-e"] = {"error": str(e)}
        if self.mdb:
            try:
                s = self.mdb.status()
                devs = self.mdb.get_devices()
                summary["mdb-e"] = {"status": s, "devices": len(devs)}
            except Exception as e:
                summary["mdb-e"] = {"error": str(e)}
        if self.bacnet:
            try:
                s = self.bacnet.status()
                objs = self.bacnet.get_objects()
                summary["bacnet-e"] = {"status": s, "objects": len(objs)}
            except Exception as e:
                summary["bacnet-e"] = {"error": str(e)}
        summary["http_mock"] = {"port": self.config["http_mock"]["port"]}
        return summary

    def stop(self):
        for p in self._processes:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
        self._processes.clear()
        if self.knx:
            self.knx.close()
        if self.mdb:
            self.mdb.close()
        if self.bacnet:
            self.bacnet.close()
