#!/usr/bin/env python3
"""
Utility script to decrypt and view encrypted P3-Edge log files.

Usage:
    python scripts/view_logs.py                    # View main log file
    python scripts/view_logs.py --tail 50          # View last 50 lines
    python scripts/view_logs.py --grep "ERROR"     # Filter for errors
    python scripts/view_logs.py --file logs/p3edge.log.enc.1  # View rotated log
"""

import argparse
import base64
import sys
from pathlib import Path

from cryptography.fernet import Fernet


def load_encryption_key(key_path: str = "config/.key") -> bytes:
    """
    Load encryption key from file.

    Args:
        key_path: Path to encryption key file

    Returns:
        Encryption key bytes

    Raises:
        FileNotFoundError: If key file doesn't exist
    """
    key_file = Path(key_path)
    if not key_file.exists():
        raise FileNotFoundError(
            f"Encryption key not found at {key_path}. "
            "Please ensure the application has been initialized."
        )

    with open(key_file, 'rb') as f:
        return f.read()


def decrypt_log_file(log_path: str, encryption_key: bytes) -> list:
    """
    Decrypt an encrypted log file.

    Args:
        log_path: Path to encrypted log file
        encryption_key: Encryption key

    Returns:
        List of decrypted log lines

    Raises:
        FileNotFoundError: If log file doesn't exist
    """
    log_file = Path(log_path)
    if not log_file.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    cipher = Fernet(encryption_key)
    decrypted_lines = []

    with open(log_file, 'rb') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                # Decode from base64
                encrypted_data = base64.b64decode(line)

                # Decrypt
                decrypted_msg = cipher.decrypt(encrypted_data)

                # Decode to string
                decrypted_line = decrypted_msg.decode('utf-8')
                decrypted_lines.append(decrypted_line)

            except Exception as e:
                print(f"Warning: Failed to decrypt line {line_num}: {e}", file=sys.stderr)
                decrypted_lines.append(f"[DECRYPTION ERROR at line {line_num}]")

    return decrypted_lines


def view_logs(
    log_path: str,
    key_path: str = "config/.key",
    tail: int = None,
    grep: str = None,
    follow: bool = False
):
    """
    View and optionally filter encrypted logs.

    Args:
        log_path: Path to encrypted log file
        key_path: Path to encryption key
        tail: Show only last N lines
        grep: Filter lines containing this string
        follow: Continuously monitor log file (like tail -f)
    """
    try:
        # Load encryption key
        encryption_key = load_encryption_key(key_path)

        if follow:
            print("Follow mode not yet implemented for encrypted logs.", file=sys.stderr)
            print("Use --tail or --grep instead.", file=sys.stderr)
            sys.exit(1)

        # Decrypt log file
        lines = decrypt_log_file(log_path, encryption_key)

        # Apply filters
        if grep:
            lines = [line for line in lines if grep in line]

        if tail:
            lines = lines[-tail:]

        # Print results
        for line in lines:
            print(line)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error viewing logs: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Decrypt and view P3-Edge encrypted log files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # View all logs
  %(prog)s --tail 50                    # View last 50 lines
  %(prog)s --grep "ERROR"               # Show only error lines
  %(prog)s --grep "autonomous_agent"    # Filter by component
  %(prog)s --file logs/p3edge.log.enc.1 # View rotated log
  %(prog)s --tail 100 --grep "ERROR"    # Combine filters
        """
    )

    parser.add_argument(
        '--file',
        default='logs/p3edge.log.enc',
        help='Path to encrypted log file (default: logs/p3edge.log.enc)'
    )

    parser.add_argument(
        '--key',
        default='config/.key',
        help='Path to encryption key file (default: config/.key)'
    )

    parser.add_argument(
        '--tail',
        type=int,
        metavar='N',
        help='Show only last N lines'
    )

    parser.add_argument(
        '--grep',
        metavar='PATTERN',
        help='Filter lines containing PATTERN'
    )

    parser.add_argument(
        '--follow', '-f',
        action='store_true',
        help='Follow log file in real-time (not yet implemented)'
    )

    args = parser.parse_args()

    view_logs(
        log_path=args.file,
        key_path=args.key,
        tail=args.tail,
        grep=args.grep,
        follow=args.follow
    )


if __name__ == '__main__':
    main()
