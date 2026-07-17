# VIDAA Bridge — Native Go MQTT mTLS Driver for iRidi Server

## Architecture

```
┌──────────────┐     HTTP :8090     ┌──────────────┐     MQTT mTLS     ┌──────────┐
│ iRidi Server │ ◄──────────────► │  vidaa-bridge │ ◄──────────────► │ VIDAA TV │
│ (.sirpz)     │   GET /state     │  (Go binary)  │   port 36669    │          │
│              │   POST /command   │               │                 │          │
└──────────────┘                   └──────────────┘                 └──────────┘
```

The Go bridge runs alongside iRidi Server on the same device and:
1. Maintains a persistent MQTT 3.1.1 connection to the TV over TLS mTLS (port 36669)
2. Generates dynamic VIDAA credentials (MAC + timestamp based)
3. Exposes a simple HTTP API:
   - `GET /state` — returns TV state as JSON
   - `POST /command` — sends a remote key to the TV

iRidi Server communicates with the bridge via the built-in **AV&CS HTTP driver** — no Python, no external dependencies.

## Why a bridge?

**iRidi Server's built-in MQTT driver does NOT support client certificates (mTLS).** The SSL checkbox only enables one-way TLS (server certificate verification). Hisense VIDAA TVs require the client to present a certificate — without it, the TV responds "TLS certificate required / not authorized".

Neither the MQTT driver nor the AV&CS TCP driver have fields for client certificate configuration.

## Files

| File | Description |
|------|-------------|
| `tools/vidaa-bridge/vidaa_bridge.go` | Go source — cross-compiles to aarch64 |
| `tools/vidaa-bridge/vidaa-bridge` | Binary for Linux aarch64 (HS Server) |
| `tools/vidaa-bridge/vidaa-bridge.exe` | Binary for Windows (testing) |
| `tools/vidaa-bridge/vidaa_client.pem` | Client certificate (copy from vidaa-control) |
| `tools/vidaa-bridge/vidaa_client.key` | Client private key (copy from vidaa-control) |
| `tools/vidaa-bridge/start_vidaa_bridge.sh` | Startup script for HS Server |
| `tools/vidaa-bridge/VIDAA_Bridge.sirpz` | iRidi Server project |
| `tools/vidaa-emulator/` | TV emulator for testing |

## Deployment on HS Server

- `/iridiumserver/vidaa-bridge` — binary (5.9 MB, aarch64)
- `/iridiumserver/vidaa_client.pem` — client certificate
- `/iridiumserver/vidaa_client.key` — client private key
- `/iridiumserver/start_vidaa_bridge.sh` — startup script

### Usage

```bash
# Edit TV IP and MAC in start_vidaa_bridge.sh, then:
/iridiumserver/start_vidaa_bridge.sh

# Or run directly:
/iridiumserver/vidaa-bridge \
    --tv-ip 192.168.1.13 \
    --tv-mac AA:BB:CC:DD:EE:FF \
    --cert /iridiumserver/vidaa_client.pem \
    --key /iridiumserver/vidaa_client.key \
    --listen :8090
```

### iRidi Studio Project Setup

1. Import `VIDAA_Bridge.sirpz` into iRidi Studio
2. Deploy to iRidi Server
3. The server script polls `/state` every 2 seconds and updates Server Tags
4. To send a key: write to `Server.Tags.TV_Command` (e.g. "KEY_HOME")

### Server Tags

| Tag | Direction | Type | Description |
|-----|-----------|------|-------------|
| `Server.Tags.TV_Command` | Write | String | Send a key: "KEY_HOME", "KEY_VOLUME_UP", etc. |
| `Server.Tags.TV_Connected` | Read | "0"/"1" | TV connection status |
| `Server.Tags.TV_Power` | Read | String | "on" / "off" |
| `Server.Tags.TV_Volume` | Read | String | Volume 0-100 |
| `Server.Tags.TV_Muted` | Read | "0"/"1" | Mute status |
| `Server.Tags.TV_Source` | Read | String | Current input source |
| `Server.Tags.TV_State` | Read | JSON | Full TV state object |

### Build (from source)

```bash
# Linux aarch64 (HS Server)
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -ldflags="-s -w" -o vidaa-bridge vidaa_bridge.go

# Windows (testing)
go build -ldflags="-s -w" -o vidaa-bridge.exe vidaa_bridge.go
```

## Emulator

For testing without a real TV:

```bash
# Generate certs (once)
cd tools/vidaa-emulator
python generate_certs.py

# Start emulator
python vidaa_tv_emulator.py --no-tls   # plain TCP
python vidaa_tv_emulator.py --server-cert certs/server_cert.pem --server-key certs/server_key.pem  # with TLS

# Test with bridge
vidaa-bridge.exe --tv-ip 127.0.0.1 --tv-mac AA:BB:CC:DD:EE:FF --listen :8090 --no-tls
```

Integration tests: `python test_integration.py` (16/16), edge cases: `python test_edge_cases.py` (15/15)

## Testing Results

| Test | Result |
|------|--------|
| Go bridge + emulator (no TLS) | Connected, keys sent |
| Go bridge + emulator (TLS) | Connected, keys sent |
| Go bridge + emulator (mTLS, cert requested) | N/A — emulator uses self-signed CA, real TV uses RemoteCA |
| Go bridge on HS Server (aarch64) | Binary executes, help output correct |
| vidaa-control + emulator (TLS) | Full pairing + commands cycle |

## Supported Keys

`KEY_POWER`, `KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT`, `KEY_OK`, `KEY_BACK`, `KEY_MENU`, `KEY_HOME`, `KEY_EXIT`, `KEY_VOLUME_UP`, `KEY_VOLUME_DOWN`, `KEY_MUTE`, `KEY_CHANNEL_UP`, `KEY_CHANNEL_DOWN`, `KEY_0`-`KEY_9`, `KEY_RED`, `KEY_GREEN`, `KEY_YELLOW`, `KEY_BLUE`, `KEY_PLAY`, `KEY_PAUSE`, `KEY_STOP`, `KEY_REWIND`, `KEY_FAST_FORWARD`, `KEY_INFO`, `KEY_SUBTITLE`
