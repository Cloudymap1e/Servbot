#!/usr/bin/env python
"""
Main entry point for Servbot interactive CLI.

Run this file to start the interactive command-line interface:
    python -m servbot.main
    
Or directly:
    python main.py
"""

import sys
from pathlib import Path

# Ensure the parent directory is in the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from servbot.cli import main

if __name__ == "__main__":
    main()

