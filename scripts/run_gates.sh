#!/bin/bash

# HARD LOCK: Verify we are running under Git Bash (MSYS/MINGW)
if [[ ! $(uname) =~ MINGW|MSYS ]]; then
    echo "ERROR: run_gates.sh must be executed from Git Bash (MSYS/MINGW)."
    exit 1
fi

# Goal: a minimal, crash-safe wrapper that:
# - runs a command (passed as argv, not a quoted string)
# - supports optional timeout
# - logs stdout/stderr to files under $LOCALAPPDATA/pyrite/logs
# - on timeout, kills the entire process tree via taskkill /T /F
# - prints a short summary (command, log paths, status)

TIMEOUT=""
if [[ "$1" == "--timeout" ]]; then
    TIMEOUT="$2"
    shift 2
fi

if [[ "$1" == "--" ]]; then
    shift
fi

if [[ -z "$1" ]]; then
    echo "Usage: ./scripts/run_gates.sh [--timeout N] -- command [args...]"
    exit 1
fi

# Ensure LOCALAPPDATA is set (Windows env var)
if [[ -z "$LOCALAPPDATA" ]]; then
    # Fallback for some bash environments
    LOCALAPPDATA="/c/Users/$(whoami)/AppData/Local"
fi

export PYRITE_WRAPPED=1

LOG_DIR="${LOCALAPPDATA}/pyrite/logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
PID=$$
LOG_BASE="${LOG_DIR}/dev-${TIMESTAMP}-${PID}"
OUT_LOG="${LOG_BASE}.out.log"
ERR_LOG="${LOG_BASE}.err.log"

# Run command
if [[ -n "$TIMEOUT" ]]; then
    # Run in background
    "$@" > "$OUT_LOG" 2> "$ERR_LOG" &
    CMD_PID=$!
    
    # Wait for completion or timeout
    ELAPSED=0
    while kill -0 $CMD_PID 2>/dev/null; do
        if [[ $ELAPSED -ge $TIMEOUT ]]; then
            # Timeout reached
            # kill child process tree via taskkill
            taskkill //T //F //PID $CMD_PID > /dev/null 2>&1
            echo "TIMEOUT"
            echo "Command: $@"
            echo "Stdout: $OUT_LOG"
            echo "Stderr: $ERR_LOG"
            exit 124
        fi
        sleep 1
        ((ELAPSED++))
    done
    wait $CMD_PID
    STATUS=$?
else
    "$@" > "$OUT_LOG" 2> "$ERR_LOG"
    STATUS=$?
fi

echo "Status: $STATUS"
echo "Command: $@"
echo "Stdout: $OUT_LOG"
echo "Stderr: $ERR_LOG"

exit $STATUS

