#!/usr/bin/env python3
"""
Simple Flask server for traceroute visualizer.
Provides API endpoint for running traceroute from the browser.
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import subprocess
import re
import sys
from pathlib import Path

app = Flask(__name__, static_folder=str(Path(__file__).parent))
CORS(app, resources={r"/*": {"origins": "*"}})

# Store the HTML file path
HTML_FILE = Path(__file__).parent / 'traceroute_visualizer.html'


def run_traceroute(target, max_hops=30):
    """Run traceroute and parse results."""
    hops = []
    
    try:
        # Try Linux traceroute
        cmd = ['traceroute', '-m', str(max_hops), '-n', target]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout
        
        if not output:
            # Try Windows tracert
            cmd = ['tracert', '-d', '-h', str(max_hops), target]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = result.stdout
        
        lines = output.strip().split('\n')
        
        for line in lines:
            if line.startswith('traceroute') or line.startswith('Tracing route') or not line.strip():
                continue
            
            match = re.match(r'\s*(\d+)\s+(.+)', line)
            if match:
                hop_num = int(match.group(1))
                rest = match.group(2)
                parts = rest.split()
                ip = None
                times = []
                
                for part in parts:
                    # Check for IP pattern FIRST before numeric patterns
                    if re.match(r'\d+\.\d+\.\d+\.\d+', part):
                        ip = part
                    elif re.match(r'\d+\.?\d*', part) and ('ms' in rest or part.replace('.','',1).isdigit()):
                        # Extract timing values (with or without 'ms' suffix)
                        try:
                            time_val = float(part.replace('ms', ''))
                            times.append(time_val)
                        except ValueError:
                            pass
                    elif part != '*' and ip is None and not part.endswith('ms'):
                        # Non-IP, non-timing value (could be hostname)
                        if not re.match(r'^\d+\.?\d*$', part): # Not a number
                            ip = part
                
                if ip == '*':
                    ip = None
                
                # Only add hop if we have valid data
                if times or ip:
                    hops.append({
                        'hop': hop_num,
                        'ip': ip,
                        'times': times,
                        'avg_time': sum(times) / len(times) if times else None
                    })
                
    except subprocess.TimeoutExpired:
        return [], "Traceroute timed out"
    except FileNotFoundError:
        return [], "traceroute command not found"
    except Exception as e:
        return [], str(e)
    
    return hops, None


@app.route('/')
def index():
    """Serve the HTML visualizer."""
    if HTML_FILE.exists():
        return send_from_directory(HTML_FILE.parent, HTML_FILE.name)
    return jsonify({'error': 'HTML file not found'}), 404


@app.route('/api/traceroute')
def api_traceroute():
    """API endpoint for running traceroute."""
    target = request.args.get('target', '')
    max_hops = request.args.get('max_hops', 30, type=int)
    
    if not target:
        return jsonify({'error': 'No target specified'}), 400
    
    # Basic validation - allow DNS names and IPs
    if not re.match(r'^[a-zA-Z0-9.\-_]+$', target):
        return jsonify({'error': 'Invalid target format'}), 400
    
    hops, error = run_traceroute(target, max_hops)
    
    if error:
        return jsonify({'error': error}), 500
    
    return jsonify({
        'target': target,
        'hops': hops
    })


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'message': 'Traceroute server is running'})


if __name__ == '__main__':
    print("=" * 60)
    print("Traceroute Visualizer Server")
    print("=" * 60)
    print(f"HTML File: {HTML_FILE}")
    print(f"HTML Exists: {HTML_FILE.exists()}")
    print("=" * 60)
    print("Server starting...")
    print("Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        # Use threaded=True for better concurrency
        app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)
