#!/usr/bin/env python
"""
Demo script showing CLI commands programmatically.

This demonstrates how the CLI can be used both interactively
and programmatically for testing/automation.
"""

import sys
from pathlib import Path

# Add parent directory to path

from servbot.cli import ServbotCLI

def demo_commands():
    """Run a series of demo commands."""
    print("=" * 70)
    print("SERVBOT CLI DEMO")
    print("=" * 70)
    print("\nThis demo shows various CLI commands in action.")
    print("In normal use, you'd run: python -m servbot")
    print("\n" + "=" * 70)
    
    # Create CLI instance
    cli = ServbotCLI()
    cli.running = True  # Keep it running for demo
    
    # Demo commands
    commands = [
        ("help", "Show all available commands"),
        ("accounts", "List all email accounts"),
        ("database", "Show database contents"),
        ("inventory", "Check Flashmail inventory"),
    ]
    
    for cmd, description in commands:
        print(f"\n{'=' * 70}")
        print(f"COMMAND: {cmd}")
        print(f"PURPOSE: {description}")
        print("=" * 70)
        
        try:
            cli.handle_command(cmd)
        except Exception as e:
            print(f"Error executing command: {e}")
        
        input("\nPress Enter to continue to next command...")
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print("\nTo use the CLI interactively, run:")
    print("  python -m servbot")
    print("\nOr use the startup scripts:")
    print("  run.bat         (Windows)")
    print("  ./run.sh        (Linux/Mac)")
    print("=" * 70)


if __name__ == "__main__":
    demo_commands()

