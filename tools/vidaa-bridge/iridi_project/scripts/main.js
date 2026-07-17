/// VIDAA Bridge — iRidi Server Script (v2)
///
/// Polls the Go bridge HTTP API for TV state and writes to Server Tags.
/// Reads commands from Server Tags and forwards to the bridge.
///
/// Server Tags:
///   Server.Tags.TV_Command   — write: "KEY_HOME", "VOL_50", "SRC_hdmi1", "APP_youtube", "MUTE"
///   Server.Tags.TV_State     — read: JSON with full TV state
///   Server.Tags.TV_Connected — read: "1" / "0"
///   Server.Tags.TV_Power     — read: "on" / "off"
///   Server.Tags.TV_Volume    — read: "0" to "100"
///   Server.Tags.TV_Muted     — read: "0" / "1"
///   Server.Tags.TV_Source    — read: source name

var BRIDGE_HOST = "127.0.0.1";
var BRIDGE_PORT = 8090;
var lastCommand = "";

// ── Send command to TV via bridge ───────────────────────────────────────

function sendToTV(command) {
    try {
        var device = IR.GetDevice("VIDAA Command (HTTP)");
        if (device) {
            device.Send([command]);
            IR.Log("[VIDAA] CMD: " + command);
        } else {
            IR.Log("[VIDAA] ERROR: Device not found");
        }
    } catch (e) {
        IR.Log("[VIDAA] Send error: " + e);
    }
}

// ── Poll state from bridge ──────────────────────────────────────────────

function pollState() {
    try {
        var device = IR.GetDevice("VIDAA State (HTTP)");
        if (device) {
            device.Send(["GET /state"]);
        }
    } catch (e) {
        IR.Log("[VIDAA] Poll error: " + e);
    }
}

// ── Process state response ──────────────────────────────────────────────

function processState(data) {
    try {
        var state = JSON.Parse(data);
        if (state) {
            var server = IR.GetServer();
            server.Set("Server.Tags.TV_Connected", state.connected ? "1" : "0");
            server.Set("Server.Tags.TV_Power", state.power);
            server.Set("Server.Tags.TV_Volume", String(state.volume));
            server.Set("Server.Tags.TV_Muted", state.muted ? "1" : "0");
            server.Set("Server.Tags.TV_Source", state.source);
            server.Set("Server.Tags.TV_State", JSON.Stringify(state));
        }
    } catch (e) {
        IR.Log("[VIDAA] Parse error: " + e);
    }
}

// ── Check for commands in Server Tags ───────────────────────────────────

function checkCommands() {
    var cmd = IR.GetVariable("Server.Tags.TV_Command");
    if (cmd && cmd !== lastCommand) {
        lastCommand = cmd;
        sendToTV(cmd);
        IR.GetServer().Set("Server.Tags.TV_Command", "");
    }
}

// ── Event loop ──────────────────────────────────────────────────────────

IR.AddListener(IR.EVENT_ON_TICK, function() {
    checkCommands();
    pollState();
});

// ── HTTP response handler ───────────────────────────────────────────────

IR.AddListener(IR.EVENT_DEVICE_DATA, function(deviceName, data) {
    if (deviceName === "VIDAA State (HTTP)") {
        processState(data);
    }
});

IR.Log("[VIDAA] Bridge script v2 loaded. Polling every 2s.");
