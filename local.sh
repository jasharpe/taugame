#!/bin/bash
# Runs the game straight from the working tree: no container, no colima, no
# build. Code changes need only a restart, or a browser reload for anything
# under static/ and templates/.
#
#   ./local.sh              run on the default ports
#   ./local.sh --hints      any extra arguments are passed through to tau.py
#
# To test the packaged container instead, use ./release.sh --serve.
set -euo pipefail

cd "$(dirname "$0")"

PORT=8000
SSL_PORT=8001
VENV=.venv

if [ ! -x "$VENV/bin/python" ]; then
  echo "==> Creating $VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r requirements.txt
fi

missing=""
[ -f secrets.py ] || missing="$missing secrets.py"
[ -f localhost.crt ] || missing="$missing localhost.crt"
[ -f localhost.key ] || missing="$missing localhost.key"
if [ -n "$missing" ]; then
  echo "Missing:$missing" >&2
  echo "Run: $VENV/bin/python setup.py" >&2
  exit 1
fi

# Checking first gives a clear message instead of a traceback from bind().
for port in "$PORT" "$SSL_PORT"; do
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Stop whatever is on it, or edit the" >&2
    echo "PORT/SSL_PORT settings at the top of this script." >&2
    exit 1
  fi
done

"$VENV/bin/python" tau.py --debug --port="$PORT" --ssl_port="$SSL_PORT" \
    --certfile=localhost.crt --keyfile=localhost.key "$@" &
server=$!
trap 'kill $server 2>/dev/null || true' EXIT INT TERM

# Wait until it is actually listening, so the address below is only printed
# once it is true. Checking the listener rather than making a request keeps the
# server log clean.
for _ in $(seq 1 100); do
  if lsof -nP -iTCP:"$SSL_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$server" 2>/dev/null; then
    echo "Server exited during startup." >&2
    wait "$server"
    exit 1
  fi
  sleep 0.1
done

echo ""
echo "  Tau is running at  https://localhost:$SSL_PORT/"
echo ""
echo "  The certificate is self-signed, so accept the browser warning once."
echo "  Press Ctrl-C to stop."
echo ""
echo "  https://localhost:$SSL_PORT/"

wait "$server"
