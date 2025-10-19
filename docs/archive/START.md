# How to Start Servbot CLI

## Quick Start

Choose one of these methods:

### Method 1: Run from Package Directory (Easiest)

```bash
cd D:\servbot\servbot
python main.py
```

### Method 2: Run as Module (From Parent Directory)

```bash
cd D:\servbot
python -m servbot
```

### Method 3: Use Startup Script

```bash
cd D:\servbot\servbot
run.bat          # Windows
```

## Common Issue

**Error: "No module named servbot"**

This happens when you run `python -m servbot` from inside the `servbot` package directory.

**Solution:** Either:
1. Use `python main.py` instead (works from anywhere)
2. Or go up one directory: `cd ..` then `python -m servbot`

## Recommended

The **easiest way** is:

```bash
cd D:\servbot\servbot
python main.py
```

This always works regardless of your current directory!

