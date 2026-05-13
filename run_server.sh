#!/bin/bash
# Start the traceroute server with clear instructions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "Starting Traceroute Visualizer Server"
echo "============================================================"
echo ""
echo "Server will start at: http://localhost:5000"
echo ""
echo "IMPORTANT: After the server starts:"
echo "  1. Open your browser"
echo "  2. Go to: http://localhost:5000"
echo "  3. Enter a target (e.g., google.com)"
echo "  4. Click 'Run Traceroute'"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Check if dependencies are installed
if ! python3 -c "import flask" 2>/dev/null; then
    echo "ERROR: Flask is not installed!"
    echo "Install with: pip3 install flask flask-cors"
    exit 1
fi

if ! command -v traceroute &> /dev/null; then
    echo "WARNING: traceroute command not found!"
    echo "Install with: sudo apt-get install traceroute"
    echo ""
fi

# Start the server
python3 traceroute_server.py
