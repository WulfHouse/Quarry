#!/bin/bash

# Soft check for direct command usage bypassing run_gates.sh
# Usage: ./scripts/run_gates.sh -- ./scripts/check_wrapper_usage.sh

if [[ -z "$PYRITE_WRAPPED" ]]; then
    echo "ERROR: check_wrapper_usage.sh must be executed via ./scripts/run_gates.sh"
    exit 1
fi

echo "Scanning for direct command usage bypassing the wrapper..."

# Prohibited direct patterns (heuristic)
# These are common command starts that should probably be wrapped.
# We look for them in READMEs, .md files, and .sh scripts.
PROHIBITED_DIRECT=("python scripts/pyrite" "python tools/runtime/pyrite" "python tools/runtime/quarry" "python forge/src/compiler.py" "python tools/testing/pytest.py")

WARNINGS_FOUND=0

for PATTERN in "${PROHIBITED_DIRECT[@]}"; do
    # Search for lines containing the pattern but NOT the wrapper prefix
    # Excluding .git, node_modules, etc.
    # We want to match lines like "python scripts/pyrite hello.pyrite"
    # but not "./scripts/run_gates.sh -- python scripts/pyrite hello.pyrite"
    
    # Using grep -v to exclude lines containing the wrapper
    # and grep -F for literal string matching
    MATCHES=$(grep -r "$PATTERN" . \
        --include="*.md" --include="*.sh" --include="*.txt" \
        --exclude-dir=.git \
        --exclude-dir=node_modules \
        --exclude-dir=.cursor \
        --exclude-dir=.quarry \
        --exclude-dir=.pyrite \
        --exclude=run_gates.sh \
        --exclude=check_wrapper_usage.sh | grep -v "./scripts/run_gates.sh --")
    
    if [ -n "$MATCHES" ]; then
        echo "WARNING: Found potential unwrapped command: '$PATTERN'"
        echo "$MATCHES"
        echo ""
        WARNINGS_FOUND=$((WARNINGS_FOUND + 1))
    fi
done

if [ $WARNINGS_FOUND -eq 0 ]; then
    echo "Success: No unwrapped command usage found (heuristics pass)."
    exit 0
else
    echo "Summary: Found $WARNINGS_FOUND unwrapped usage patterns."
    echo "Note: This is a soft check (warning only)."
    exit 0 # Non-failing for now
fi

