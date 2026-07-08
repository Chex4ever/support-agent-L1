# Tools

Reusable utilities for support ticket work.

## Structure

```
tools/
  omnidesk/         # Omnidesk API tools (Python)
  project/          # .irpz/.sirpz project analysis tools (Python)
  image/            # Image processing tools (Python)
  script-patterns/  # iRidi Script solution patterns (.js)
```

## Omnidesk

| Tool | Description | Usage |
|------|-------------|-------|
| `fetch_messages.py` | Fetch all messages from an Omnidesk ticket by internal case ID | `python tools/omnidesk/fetch_messages.py <case_id> [--save out.json]` |
| `download_attachments.py` | Download all attachments + inline images from a ticket. Optionally run OCR on images. | `python tools/omnidesk/download_attachments.py <case_id> [--outdir DIR] [--ocr]` |

## Project Analysis

| Tool | Description | Usage |
|------|-------------|-------|
| `analyze_irpz.py` | Parse .irpz file: pages, popups, items, tokens, scripts, devices | `python tools/project/analyze_irpz.py <path/to/project.irpz>` |

## Image Processing

| Tool | Description | Usage |
|------|-------------|-------|
| `ocr.py` | OCR text extraction from images. Supports Tesseract + EasyOCR. 4 preprocessing pipelines: `monitor` (photos of screens), `screenshot`, `document`, `auto`. Includes screen detection + perspective correction for monitor photos. | `python tools/image/ocr.py <image> -p monitor -l rus+eng [--debug]` |

## PDF Processing

| Tool | Description | Usage |
|------|-------------|-------|
| `extract.py` | Extract text from PDF files using PyMuPDF (fitz). Falls back to OCR via `tools/image/ocr.py` when no text layer is found. | `python tools/pdf/extract.py <file.pdf> [-o out.txt] [--debug]` |

## BookStack KB Sync

| Tool | Description | Usage |
|------|-------------|-------|
| `bookstack/sync.py` | Two-way sync: download all BookStack content to local `.md` files, push changes back | `python -m tools.bookstack.sync pull` / `push` / `status` |
| `bookstack/migrate_kb.py` | Migrate old TicketDB KB entries into BookStack as a new book | `python -m tools.bookstack.migrate_kb --apply` |

## Emulation (client environment)

| Tool | Description | Usage |
|------|-------------|-------|
| `emulation/up.py` | Start full emulation stack: knx-e + mdb-e + http-mock | `python -m tools.emulation.up --project <file.irpz>` |
| `emulation/http_mock.py` | Standalone HTTP mock for multiroom amp `/httpapi.asp` | `python -m tools.emulation.http_mock --port 8002` |
| `emulation/knx_client.py` | HTTP client for knx-e REST API (port 8001) | import from Python |
| `emulation/mdb_client.py` | HTTP client for mdb-e REST API (port 7999) | import from Python |

### Requirements

- **knx-e** at `C:\iridi\knx-e` — KNX bus emulator (KNXnet/IP, FastAPI, port 8001)
- **mdb-e** at `C:\iridi\mdb-e` — Modbus TCP emulator (pymodbus, FastAPI, port 7999)

### Quick start with a client project

```powershell
python -m tools.emulation.up --project tickets/736-506651/files/project/project.irpz
```

This starts all 3 emulators, imports the KNX project into knx-e, and prints connection details.

### Subcommands

```powershell
python -m tools.emulation.up --knx-only                    # start only KNX
python -m tools.emulation.up --mdb-only --modbus-config my_config.yaml
python -m tools.emulation.up --http-only
python -m tools.emulation.up --status                       # check running status
python -m tools.emulation.up --stop                         # stop all
```

### Modbus config

By default mdb-e uses `register-init.yaml`. Pass a different config:

```powershell
python -m tools.emulation.up --mdb-only --modbus-config register-init-k40a-alice.yaml
```

### Network ports

| Service | Port | Protocol |
|---------|------|----------|
| KNX bus | 3671 | UDP |
| KNX web | 8001 | HTTP |
| Modbus | 502 | TCP |
| Modbus web | 7999 | HTTP |
| HTTP mock | 8002 | HTTP |

## iRidi Script Patterns

| Pattern | File | When to use |
|---------|------|-------------|
| **List Polling** | `list_polling.js` | Regular List items lose token bindings after `.Clone()`. Buttons use GUI actions that bypass scripts. |
| **Advanced List Polling** | `advlist_polling.js` | Same problem for Advanced List (Adapter pattern). |
| **Token Bus** | `token_bus.js` | You control all token writes via script (no GUI `number_to_tag`). Pub/sub for token changes. |
| **Sine Generator** | `sine_generator.js` | Generate test sine waves for Linear Trend debugging. Server project (init.js). |

## Usage with Agents

When an agent needs one of these tools, copy the file into the working context or reference it by path.
