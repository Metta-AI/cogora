#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec uv run --directory "$SCRIPT_DIR" cogora-server
