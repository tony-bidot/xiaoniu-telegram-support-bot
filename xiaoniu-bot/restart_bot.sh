#!/usr/bin/env bash
set -euo pipefail

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_DIR="$(cd "$BOT_DIR/.." && pwd)"

if [ -x "$BOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$BOT_DIR/.venv/bin/python"
elif [ -x "$WORKSPACE_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$WORKSPACE_DIR/.venv/bin/python"
else
  PYTHON_BIN="$(command -v python3 || true)"
fi

if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
  echo "No usable python interpreter found for bot restart" >&2
  exit 1
fi

cd "$BOT_DIR"

if pgrep -af "$BOT_DIR/bot.py|$PYTHON_BIN bot.py|python3 bot.py|python bot.py" >/dev/null 2>&1; then
  pkill -f "$BOT_DIR/bot.py|$PYTHON_BIN bot.py|python3 bot.py|python bot.py" || true
  sleep 1
fi

nohup "$PYTHON_BIN" bot.py > bot.log 2>&1 &
sleep 2

echo "bot restarted with $PYTHON_BIN"
pgrep -af "$BOT_DIR/bot.py|$PYTHON_BIN bot.py|python3 bot.py|python bot.py" || true
