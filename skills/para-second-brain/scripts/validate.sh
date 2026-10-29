#!/usr/bin/env bash
# Read-only launcher. All paths are resolved relative to this installed skill.
set -euo pipefail
SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/validate.py" "$@"
