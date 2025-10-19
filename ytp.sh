#!/bin/bash
# YTP - YouTube Parser launcher for Linux/Mac
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$DIR/ytp.py" "$@"
