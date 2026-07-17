"""HTTP client for BACnet-E REST API."""

from __future__ import annotations
import json
import urllib.request
import urllib.error
from typing import Any, Optional


class BacnetClient:
    """Client for BACnet-E emulator REST API."""

    def __init__(self, base_url: str = "http://localhost:8003"):
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, data: Any = None) -> Any:
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": str(e), "status": e.code}
        except Exception as e:
            return {"error": str(e)}

    def status(self) -> dict[str, Any]:
        return self._request("GET", "/api/status")

    def get_objects(self, type_filter: Optional[int] = None) -> list[dict]:
        path = "/api/objects"
        if type_filter is not None:
            path += f"?type_filter={type_filter}"
        data = self._request("GET", path)
        return data.get("objects", [])

    def get_object(self, otype: int, instance: int) -> dict:
        return self._request("GET", f"/api/objects/{otype}/{instance}")

    def set_value(self, otype: int, instance: int, value: float) -> dict:
        return self._request("POST", f"/api/objects/{otype}/{instance}/value",
                             {"value": value})

    def create_object(self, otype: int, instance: int, name: str = "",
                      value: float = 0.0) -> dict:
        return self._request("POST", "/api/objects",
                             {"type": otype, "instance": instance,
                              "name": name, "value": value})

    def delete_object(self, otype: int, instance: int) -> dict:
        return self._request("DELETE", f"/api/objects/{otype}/{instance}")

    def get_log(self, limit: int = 100) -> list[dict]:
        data = self._request("GET", f"/api/log?limit={limit}")
        return data.get("items", [])

    def clear_log(self) -> dict:
        return self._request("DELETE", "/api/log")

    def close(self):
        pass
