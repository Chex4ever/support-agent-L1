#!/bin/sh
# VIDAA Bridge startup script for iRidi HS Server
# Place at: /iridiumserver/start_vidaa_bridge.sh
# Add to /iridiumserver/forebear.sh or run manually

BRIDGE_BIN="/iridiumserver/vidaa-bridge"
CERT_FILE="/iridiumserver/vidaa_client.pem"
KEY_FILE="/iridiumserver/vidaa_client.key"
TV_IP="192.168.1.13"
TV_MAC="AA:BB:CC:DD:EE:FF"
LISTEN_PORT="8090"
LOG_FILE="/iridiumserver/vidaa_bridge.log"

echo "Starting VIDAA Bridge..."
echo "  TV: $TV_IP:36669 (MAC: $TV_MAC)"
echo "  API: http://127.0.0.1:$LISTEN_PORT"
echo "  Log: $LOG_FILE"

$BRIDGE_BIN \
    --tv-ip "$TV_IP" \
    --tv-mac "$TV_MAC" \
    --tv-port 36669 \
    --listen ":$LISTEN_PORT" \
    --cert "$CERT_FILE" \
    --key "$KEY_FILE" \
    >> "$LOG_FILE" 2>&1 &

echo "VIDAA Bridge started (PID: $!)"
