#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if pgrep -af ".venv/bin/python bot.py|python3 bot.py|python bot.py" >/dev/null 2>&1; then
  pkill -f ".venv/bin/python bot.py|python3 bot.py|python bot.py" || true
  sleep 1
fi

nohup .venv/bin/python bot.py > bot.log 2>&1 &

echo "bot restarted"
pgrep -af ".venv/bin/python bot.py|python3 bot.py|python bot.py" || true
