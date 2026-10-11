#!/usr/bin/env bash
# Runs the chat server and the website together on your computer (macOS / Linux).
#   ./start.sh        then open the address it prints (usually http://localhost:5173)
# Press Ctrl+C to stop both.
set -e
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "Python 3 is missing: install it from https://www.python.org"; exit 1; }
command -v npm >/dev/null || { echo "Node.js is missing: install it from https://nodejs.org"; exit 1; }

# 1. Chat server settings
if [ ! -f server/.env ]; then
  cp server/.env.example server/.env
fi
if grep -q "^ANTHROPIC_API_KEY=sk-ant-\.\.\.$" server/.env || ! grep -q "^ANTHROPIC_API_KEY=." server/.env; then
  echo
  echo ">> Paste your Claude API key (starts with sk-ant-) into server/.env, line ANTHROPIC_API_KEY=, then run ./start.sh again."
  echo "   Get a key at https://console.anthropic.com"
  exit 1
fi

# 2. Chat server (Python, in its own virtual environment)
if [ ! -x server/.venv/bin/python ]; then
  echo ">> Installing the chat server (first time only)..."
  python3 -m venv server/.venv
fi
server/.venv/bin/python -m pip install -q --disable-pip-version-check -r server/requirements.txt

echo ">> Starting the chat server on http://localhost:8000 ..."
(cd server && exec .venv/bin/python -m uvicorn app:app --env-file .env --port 8000) &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT INT TERM

for _ in $(seq 1 30); do
  if curl -fs http://localhost:8000/api/health >/dev/null 2>&1; then break; fi
  if ! kill -0 $SERVER_PID 2>/dev/null; then echo "The chat server stopped: see the error above."; exit 1; fi
  sleep 1
done
curl -fs http://localhost:8000/api/health >/dev/null || { echo "The chat server did not start: see the error above."; exit 1; }
echo ">> Chat server is running."

# 3. Website
cd website
if [ ! -d node_modules ]; then
  echo ">> Installing the website (first time only)..."
  npm install --no-audit --no-fund
fi
echo ">> Open the Local address printed below (usually http://localhost:5173). The chat button is in the bottom-right corner."
npm run dev
