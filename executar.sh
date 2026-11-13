#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$SCRIPT_DIR/instalar.py" --se-necessario
exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/executar.py" "$@"
