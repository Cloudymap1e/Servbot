#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a fresh Linux host and run live tests.
# Optional env:
#   REPO_URL   - Git URL (default: current repo remote if present)
#   BRANCH     - Git branch (default: main)
#   WORKDIR    - Directory to checkout (default: ~/servbot)
#   PROXIES_FILE - Path to a text file with proxies to import (optional)
#   PROVIDER     - Provider label for imported proxies (default: ai-imported)
#   PYTHON_BIN   - Python binary (default: python3)

export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y || true
sudo apt-get install -y --no-install-recommends \
  ca-certificates curl wget git python3 python3-venv python3-pip \
  xvfb libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 \
  libasound2 libxkbcommon0 libgtk-3-0 libx11-xcb1 >/dev/null 2>&1 || true

REPO_URL=${REPO_URL:-}
BRANCH=${BRANCH:-main}
WORKDIR=${WORKDIR:-$HOME/servbot}
PY=${PYTHON_BIN:-python3}

mkdir -p "$WORKDIR"
cd "$WORKDIR"

if [ ! -d .git ]; then
  if [ -z "$REPO_URL" ]; then
    echo "REPO_URL not provided; attempting to infer from local environment is not supported here."
    echo "Please export REPO_URL or git clone manually before running this script."
    exit 2
  fi
  git clone -b "$BRANCH" "$REPO_URL" .
else
  git fetch --all --tags || true
  git checkout "$BRANCH" || true
  git pull --rebase || true
fi

# Python env
if [ ! -d .venv ]; then
  $PY -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip >/dev/null 2>&1 || true
pip install -r requirements.txt pytest >/dev/null 2>&1

# Playwright install
$PY -m playwright install chromium --with-deps || true

# Enable live tests
touch RUN_LIVE RUN_REDDIT

# Optional: import proxies
if [ -n "${PROXIES_FILE:-}" ] && [ -f "$PROXIES_FILE" ]; then
  $PY -m scripts.maintenance.import_proxies_ai --file "$PROXIES_FILE" --provider "${PROVIDER:-ai-imported}" || true
fi

# Run connectivity test (non-fatal)
echo "Running proxy connectivity smoke test..."
xvfb-run -a bash -lc "pytest -q tests/test_proxy_connectivity_live.py -s" || true

# Run Reddit registration test (headful via Xvfb)
echo "Running Reddit registration live test..."
SERVBOT_MAX_PROXY_ATTEMPTS=${SERVBOT_MAX_PROXY_ATTEMPTS:-6} \
xvfb-run -a bash -lc "pytest -q tests/test_reddit_registration_live.py -s"


