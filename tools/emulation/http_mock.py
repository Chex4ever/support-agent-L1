"""HTTP mock for multiroom amp (Russound / similar).

Responds to GET /httpapi.asp?command=multiroom:getSlaveList
with JSON matching what amp_core.js expects.

Usage:
    python -m tools.emulation.http_mock [--port 8002] [--host 0.0.0.0]
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger("http_mock")

app = FastAPI(title="Multiroom Amp Mock", version="1.0")

_slaves: list[dict[str, str]] = []
_request_log: list[dict[str, Any]] = []


class SlaveAdd(BaseModel):
    ip: str


@app.get("/httpapi.asp")
async def httpapi(command: str = Query(""), slave: str | None = None):
    if command == "multiroom:getSlaveList":
        entry = {
            "command": command,
            "slave_count": len(_slaves),
            "response": {"slaves": str(len(_slaves))},
        }
        resp: dict[str, str] = {"slaves": str(len(_slaves))}
        if _slaves:
            resp["slave_list"] = json.dumps(_slaves)
            entry["response"]["slave_list"] = resp["slave_list"]
        _request_log.append(entry)
        logger.info("GET /httpapi.asp command=%s slaves=%d", command, len(_slaves))
        return resp
    if command == "multiroom:setSlaveList":
        entry = {"command": command, "slave": slave}
        _request_log.append(entry)
        logger.info("GET /httpapi.asp command=%s slave=%s", command, slave)
        return {"status": "OK"}
    logger.warning("GET /httpapi.asp command=%s (unhandled)", command)
    return {"status": "unknown_command"}


@app.get("/api/slaves")
def list_slaves():
    return {"slaves": _slaves, "count": len(_slaves)}


@app.post("/api/slaves", status_code=201)
def add_slave(body: SlaveAdd):
    if not any(s["ip"] == body.ip for s in _slaves):
        _slaves.append({"ip": body.ip})
        logger.info("Slave added: %s (total %d)", body.ip, len(_slaves))
    return {"slaves": _slaves, "count": len(_slaves)}


@app.delete("/api/slaves")
def clear_slaves():
    _slaves.clear()
    logger.info("All slaves cleared")
    return {"ok": True}


@app.delete("/api/slaves/{ip:path}")
def remove_slave(ip: str):
    global _slaves
    _slaves = [s for s in _slaves if s["ip"] != ip]
    logger.info("Slave removed: %s (total %d)", ip, len(_slaves))
    return {"slaves": _slaves, "count": len(_slaves)}


@app.get("/api/log")
def request_log(limit: int = Query(100, ge=1, le=1000)):
    return _request_log[-limit:]


@app.delete("/api/log")
def clear_log():
    _request_log.clear()
    return {"ok": True}


@app.post("/api/reset")
def reset():
    _slaves.clear()
    _request_log.clear()
    return {"ok": True}


@app.get("/api/status")
def status():
    return {
        "slaves_count": len(_slaves),
        "requests_logged": len(_request_log),
    }


def main():
    parser = argparse.ArgumentParser(description="Multiroom amp HTTP mock")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
    logger.info("Starting HTTP mock on %s:%s", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
