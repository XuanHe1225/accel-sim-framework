#!/bin/bash
set -euo pipefail
tracer_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$tracer_root/install_nvbit.py" "$@"
