#!/usr/bin/env python3
"""
Smart Fridge Demo Launcher

Launches both the smart fridge simulator and the main UI in convenient order.
"""

import sys
import time
import subprocess
import signal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def print_banner():
    """Print welcome banner."""
    print("=" * 70)
    print("  P3-Edge Smart Fridge Demo")
    print("=" * 70)
    print()


def check_database():
    """Check if database exists."""
    db_path = Path("data/p3edge.db")
    if not db_path.exists():
        print("⚠️  Database not found!")
        print()
        print("Would you like to:")
        print("  1. Initialize empty database")
        print("  2. Populate with 2 months of vegetarian data (recommended)")
        print("  3. Exit and run manually")
        print()
        choice = input("Enter choice (1-3): ").strip()

        if choice == "1":
            print("\nInitializing database...")
            subprocess.run([sys.executable, "scripts/init_db.py"])
            return True
        elif choice == "2":
            print("\nPopulating database with sample data...")
            print("This will take about 10-20 seconds...")
            result = subprocess.run([sys.executable, "scripts/populate_db_vegetarian.py"])
            return result.returncode == 0
        else:
            print("\nPlease run one of these commands manually:")
            print("  python scripts/init_db.py")
            print("  python scripts/populate_db_vegetarian.py")
            return False

    return True


def start_simulator():
    """Start the smart fridge simulator."""
    print("Starting Smart Fridge Simulator...")
    print("  URL: http://localhost:5001")
    print()

    # Start simulator in background
    simulator_process = subprocess.Popen(
        [sys.executable, "src/ingestion/samsung_fridge_simulator.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait a bit for it to start
    time.sleep(2)

    # Check if it's running
    if simulator_process.poll() is not None:
        print("❌ Failed to start simulator")
        stderr = simulator_process.stderr.read().decode()
        print(f"Error: {stderr}")
        return None

    print("✅ Simulator started (PID: {})".format(simulator_process.pid))
    print()
    return simulator_process


def start_ui():
    """Start the main UI."""
    print("Starting P3-Edge UI...")
    print()

    ui_process = subprocess.Popen(
        [sys.executable, "src/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return ui_process


def main():
    """Main launcher."""
    print_banner()

    # Check database
    if not check_database():
        return 1

    # Start simulator
    simulator = start_simulator()
    if not simulator:
        return 1

    # Start UI
    ui = start_ui()

    print("=" * 70)
    print("  Demo is running!")
    print("=" * 70)
    print()
    print("Instructions:")
    print("  1. The main UI should open automatically")
    print("  2. Click 'Smart Fridge' in the left navigation")
    print("  3. Click 'Connect' (URL should be pre-filled)")
    print("  4. Click 'Start Auto-Sync' to enable real-time updates")
    print()
    print("To simulate inventory changes:")
    print("  curl -X PUT http://localhost:5001/api/inventory/<item_id> \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"quantity\": 1.5}'")
    print()
    print("Press Ctrl+C to stop everything")
    print("=" * 70)
    print()

    # Register signal handler for clean shutdown
    def signal_handler(sig, frame):
        print("\n\nShutting down...")
        if simulator:
            print("  Stopping simulator...")
            simulator.terminate()
            simulator.wait(timeout=5)
        if ui:
            print("  Stopping UI...")
            ui.terminate()
            ui.wait(timeout=5)
        print("Done!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Wait for UI to exit
    try:
        ui.wait()
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up
        if simulator:
            simulator.terminate()
            simulator.wait(timeout=5)

    return 0


if __name__ == "__main__":
    sys.exit(main())
