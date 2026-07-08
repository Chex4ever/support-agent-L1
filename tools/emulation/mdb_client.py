"""Thin HTTP client for mdb-e (Modbus emulator) REST API."""

from __future__ import annotations

import time
from typing import Any

import httpx


class MdbClient:
    def __init__(self, base_url: str = "http://localhost:7999"):
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
                self.status()
                return True
            except Exception:
                time.sleep(0.5)
        return False

    def import_config(self, config: dict[str, Any]) -> dict[str, Any]:
        r = self._http.post(f"{self.base_url}/api/project/import", json=config)
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

    def add_device(self, slave_id: int, name: str, template: str = "blank",
                   holding: dict[int, Any] | None = None) -> dict[str, Any]:
        body = {"slave_id": slave_id, "name": name, "template": template}
        if holding:
            body["holding"] = {str(k): v for k, v in holding.items()}
        r = self._http.post(f"{self.base_url}/api/devices", json=body)
        r.raise_for_status()
        return r.json()

    def set_register(self, slave_id: int, address: int, value: int) -> dict[str, Any]:
        r = self._http.patch(
            f"{self.base_url}/api/devices/{slave_id}/registers/{address}",
            json={"value": value},
        )
        r.raise_for_status()
        return r.json()

    def close(self):
        self._http.close()
