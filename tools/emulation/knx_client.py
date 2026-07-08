"""Thin HTTP client for knx-e REST API."""

from __future__ import annotations

import time
from typing import Any

import httpx


class KnxClient:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=10)

    def status(self) -> dict[str, Any]:
        r = self._http.get(f"{self.base_url}/api/status")
        r.raise_for_status()
        return r.json()

    def wait_ready(self, timeout: float = 15) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                return self.status().get("running", False)
            except Exception:
                time.sleep(0.5)
        return False

    def import_sirpz(self, path: str, replace: bool = True) -> dict[str, Any]:
        with open(path, "rb") as f:
            r = self._http.post(
                f"{self.base_url}/api/project/import-sirpz",
                data={"replace": "1" if replace else "0"},
                files={"file": f},
            )
        r.raise_for_status()
        return r.json()

    def import_knxproj(self, path: str) -> dict[str, Any]:
        with open(path, "rb") as f:
            r = self._http.post(
                f"{self.base_url}/api/project/import-knxproj",
                files={"file": f},
            )
        r.raise_for_status()
        return r.json()

    def clear_project(self) -> dict[str, Any]:
        r = self._http.post(f"{self.base_url}/api/project/clear")
        r.raise_for_status()
        return r.json()

    def get_devices(self) -> list[dict[str, Any]]:
        r = self._http.get(f"{self.base_url}/api/devices")
        r.raise_for_status()
        return r.json()

    def close(self):
        self._http.close()
