#!/bin/bash

# Wrapper script to run debug commands safely using run_gates.sh
# Usage: ./scripts/run_debug_wrapper.sh

export PYRITE_DEBUG_TYPE_RESOLUTION='1'

CMD="python -m src.compiler forge/src-pyrite/tokens.pyrite --emit-llvm"
LOG_FILE=".debug-tokens.log"

# Run command using run_gates.sh
./scripts/run_gates.sh -- $CMD

# Get the latest log file from stdout of run_gates.sh (or it writes to its own log)
# For this specific debug script, we also want to filter output.

# Find the most recent .out.log in the log directory
LOG_DIR="${LOCALAPPDATA}/pyrite/logs"
if [ -z "$LOCALAPPDATA" ]; then
    LOG_DIR="/c/Users/$(whoami)/AppData/Local/pyrite/logs"
fi

LATEST_LOG=$(ls -t "${LOG_DIR}"/dev-*.out.log | head -1)

if [ -f "$LATEST_LOG" ]; then
    echo ""
    echo "=== Filtered debug output (first 30 matches) ==="
    grep -E "Option|Some|check_field_access|TRACE|register_option" "$LATEST_LOG" | head -n 30
fi

