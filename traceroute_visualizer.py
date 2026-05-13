#!/usr/bin/env python3
"""
Traceroute Visualizer
Generates and visualizes network traceroute data with multiple output formats.
"""

import subprocess
import re
import json
import sys
from datetime import datetime
from pathlib import Path

# Try to import visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def run_traceroute(target, max_hops=30):
    """
    Run traceroute command and parse the output.
    
    Args:
        target: Target hostname or IP
        max_hops: Maximum number of hops to trace
    
    Returns:
        List of hop dictionaries with timing and host information
    """
    hops = []
    
    try:
        # Try Linux traceroute first
        cmd = ['traceroute', '-m', str(max_hops), '-n', target]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        output = result.stdout
        
        if not output:
            # Try Windows tracert if Linux traceroute fails
            cmd = ['tracert', '-d', '-h', str(max_hops), target]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            output = result.stdout
        
        # Parse the output
        lines = output.strip().split('\n')
        
        for line in lines:
            # Skip header lines
            if line.startswith('traceroute') or line.startswith('Tracing route') or not line.strip():
                continue
            
            # Match hop lines - improved pattern for different traceroute formats
            match = re.match(r'\s*(\d+)\s+(.+)', line)
            if match:
                hop_num = int(match.group(1))
                rest = match.group(2)
                
                # Extract IP and timing
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
                        if not re.match(r'^\d+\.?\d*$', part):  # Not a number
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
        print(f"Error: Traceroute to {target} timed out")
    except FileNotFoundError:
        print("Error: traceroute/tracert command not found")
        print("Please install traceroute or use the demo data mode")
        sys.exit(1)
    except Exception as e:
        print(f"Error running traceroute: {e}")
    
    return hops


def generate_demo_data():
    """Generate realistic demo traceroute data for demonstration."""
    demo_hops = [
        {'hop': 1, 'ip': '192.168.1.1', 'times': [1.2, 1.1, 1.3], 'avg_time': 1.2},
        {'hop': 2, 'ip': '10.0.0.1', 'times': [5.4, 5.2, 5.6], 'avg_time': 5.4},
        {'hop': 3, 'ip': '172.16.0.1', 'times': [12.3, 11.9, 12.5], 'avg_time': 12.2},
        {'hop': 4, 'ip': '203.0.113.1', 'times': [25.7, 26.1, 25.4], 'avg_time': 25.7},
        {'hop': 5, 'ip': '198.51.100.1', 'times': [45.2, 44.8, 45.6], 'avg_time': 45.2},
        {'hop': 6, 'ip': '93.184.216.34', 'times': [52.3, 51.9, 52.7], 'avg_time': 52.3},
    ]
    return demo_hops


def print_text_table(hops, target):
    """Print traceroute data as a formatted text table."""
    if HAS_RICH:
        console = Console()
        
        table = Table(title=f"Traceroute to {target}", box=box.ROUNDED)
        table.add_column("Hop", style="cyan", justify="right")
        table.add_column("IP Address", style="green")
        table.add_column("Avg (ms)", style="yellow", justify="right")
        table.add_column("Min (ms)", style="blue", justify="right")
        table.add_column("Max (ms)", style="red", justify="right")
        table.add_column("Visual", style="magenta")
        
        max_time = max([h['avg_time'] or 0 for h in hops]) or 1
        
        for hop in hops:
            times = hop['times']
            bar_len = int((hop['avg_time'] / max_time) * 20) if hop['avg_time'] else 0
            bar = '█' * bar_len + '░' * (20 - bar_len)
            
            table.add_row(
                str(hop['hop']),
                hop['ip'] or '*',
                f"{hop['avg_time']:.1f}" if hop['avg_time'] else 'N/A',
                f"{min(times):.1f}" if times else 'N/A',
                f"{max(times):.1f}" if times else 'N/A',
                bar
            )
        
        console.print(table)
    else:
        # Simple text output if rich is not available
        print(f"\n{'='*80}")
        print(f"Traceroute to {target}")
        print(f"{'='*80}")
        print(f"{'Hop':<5} {'IP Address':<20} {'Avg(ms)':<10} {'Min(ms)':<10} {'Max(ms)':<10}")
        print(f"{'-'*80}")
        
        for hop in hops:
            times = hop['times']
            print(f"{hop['hop']:<5} {(hop['ip'] or '*'):<20} "
                  f"{str(hop['avg_time'] or 'N/A'):<10} "
                  f"{str(min(times) if times else 'N/A'):<10} "
                  f"{str(max(times) if times else 'N/A'):<10}")


def plot_latency_graph(hops, target, save_path=None):
    """Create a matplotlib visualization of latency across hops."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available. Install with: pip install matplotlib")
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    fig.suptitle(f'Traceroute Visualization: {target}\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                 fontsize=14, fontweight='bold')
    
    # Extract data
    hop_numbers = [h['hop'] for h in hops]
    avg_times = [h['avg_time'] or 0 for h in hops]
    
    # Plot 1: Latency over hops
    colors = plt.cm.viridis([t / max(avg_times) if max(avg_times) > 0 else 0.5 for t in avg_times])
    ax1.scatter(hop_numbers, avg_times, c=colors, s=100, edgecolors='black', linewidth=1.5, alpha=0.8)
    ax1.plot(hop_numbers, avg_times, 'b--', alpha=0.5, linewidth=2)
    ax1.fill_between(hop_numbers, avg_times, alpha=0.3)
    
    ax1.set_xlabel('Hop Number', fontsize=12)
    ax1.set_ylabel('Latency (ms)', fontsize=12)
    ax1.set_title('Network Latency by Hop', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(hop_numbers)
    
    # Add value labels
    for i, (hop, time) in enumerate(zip(hop_numbers, avg_times)):
        if time > 0:
            ax1.annotate(f'{time:.1f}ms', (hop, time), textcoords="offset points", 
                        xytext=(0, 10), ha='center', fontsize=9)
    
    # Plot 2: Response time distribution
    all_times = []
    for hop in hops:
        all_times.extend(hop['times'])
    
    if all_times:
        ax2.hist(all_times, bins=20, color='skyblue', edgecolor='black', alpha=0.7)
        ax2.set_xlabel('Response Time (ms)', fontsize=12)
        ax2.set_ylabel('Frequency', fontsize=12)
        ax2.set_title('Distribution of All Response Times', fontsize=14)
        ax2.grid(True, alpha=0.3)
        ax2.axvline(sum(all_times)/len(all_times), color='red', linestyle='--', 
                   label=f'Mean: {sum(all_times)/len(all_times):.1f}ms')
        ax2.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Graph saved to: {save_path}")
    else:
        plt.show()
    
    plt.close()


def create_network_map(hops, target, save_path=None):
    """Create a network path visualization."""
    if not HAS_MATPLOTLIB:
        print("Matplotlib not available. Install with: pip install matplotlib")
        return
    
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    fig.suptitle(f'Network Path: {target}\n{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 
                 fontsize=14, fontweight='bold')
    
    # Create nodes
    num_hops = len(hops)
    x_positions = list(range(num_hops))
    y_positions = [0] * num_hops
    
    # Node sizes based on latency
    max_time = max([h['avg_time'] or 0 for h in hops]) or 1
    sizes = [(h['avg_time'] or 0) / max_time * 500 + 100 for h in hops]
    
    # Draw connections
    for i in range(num_hops - 1):
        ax.plot([x_positions[i], x_positions[i+1]], [0, 0], 
               'b-', linewidth=2, alpha=0.5, zorder=1)
    
    # Draw nodes - use color list directly without cmap
    color_list = [plt.cm.RdYlGn_r(h['avg_time'] / max_time if h['avg_time'] else 0.5) for h in hops]
    scatter = ax.scatter(x_positions, y_positions, s=sizes, c=color_list,
                        alpha=0.8, edgecolors='black',
                        linewidth=2, zorder=2)
    
    # Add labels
    for i, hop in enumerate(hops):
        label = f"H{hop['hop']}\n{hop['ip'] or '*'}"
        if hop['avg_time']:
            label += f"\n{hop['avg_time']:.1f}ms"
        ax.annotate(label, (x_positions[i], y_positions[i]), 
                   xytext=(0, -40), textcoords='offset points',
                   ha='center', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', 
                            alpha=0.7, edgecolor='gray'))
    
    ax.set_xlim(-1, num_hops)
    ax.set_ylim(-100, 100)
    ax.set_xlabel('Hop Number', fontsize=12)
    ax.set_yticks([])
    ax.set_title('Network Path Visualization', fontsize=14)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add colorbar
    cbar = plt.colorbar(scatter)
    cbar.set_label('Latency (normalized)', fontsize=10)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Network map saved to: {save_path}")
    else:
        plt.show()
    
    plt.close()


def export_json(hops, target, save_path):
    """Export traceroute data to JSON."""
    data = {
        'target': target,
        'timestamp': datetime.now().isoformat(),
        'total_hops': len(hops),
        'hops': hops
    }
    
    with open(save_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Data exported to: {save_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Visualize network traceroute data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s google.com                    # Run traceroute and show text table
  %(prog)s google.com --graph            # Show latency graph
  %(prog)s google.com --map              # Show network map
  %(prog)s google.com --all              # Show all visualizations
  %(prog)s google.com --output out.png   # Save graph to file
  %(prog)s --demo --graph                # Use demo data
  %(prog)s --demo --export data.json     # Export demo data to JSON
        """
    )
    
    parser.add_argument('target', nargs='?', help='Target hostname or IP address')
    parser.add_argument('--demo', action='store_true', help='Use demo data instead of real traceroute')
    parser.add_argument('--graph', action='store_true', help='Show latency graph')
    parser.add_argument('--map', action='store_true', help='Show network map')
    parser.add_argument('--all', action='store_true', help='Show all visualizations')
    parser.add_argument('--output', '-o', help='Save visualization to file')
    parser.add_argument('--export', help='Export data to JSON file')
    parser.add_argument('--max-hops', type=int, default=30, help='Maximum number of hops (default: 30)')
    
    args = parser.parse_args()
    
    # Get traceroute data
    if args.demo or not args.target:
        print("Using demo data...")
        hops = generate_demo_data()
        target = args.target or "demo.example.com"
    else:
        print(f"Running traceroute to {args.target}...")
        hops = run_traceroute(args.target, args.max_hops)
        target = args.target
    
    if not hops:
        print("No traceroute data collected. Exiting.")
        sys.exit(1)
    
    # Print text table
    print_text_table(hops, target)
    
    # Show visualizations
    if args.graph or args.all:
        print("\nGenerating latency graph...")
        graph_output = args.output if args.output else None
        # If both graph and map, and single output specified, create separate files
        if args.all and args.output:
            base = args.output.replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
            graph_output = f"{base}_graph.png"
        plot_latency_graph(hops, target, graph_output)
    
    if args.map or args.all:
        print("\nGenerating network map...")
        map_output = args.output if args.output and not (args.graph or args.all) else None
        if args.all and args.output:
            base = args.output.replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
            map_output = f"{base}_map.png"
        elif args.map and args.output:
            map_output = args.output
        create_network_map(hops, target, map_output)
    
    # Export if requested
    if args.export:
        export_json(hops, target, args.export)
    
    print("\nDone!")


if __name__ == '__main__':
    main()
