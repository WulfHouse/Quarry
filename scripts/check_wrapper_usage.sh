#!/bin/bash

# Soft check for direct command usage bypassing run_gates.sh
# Usage: ./scripts/run_gates.sh -- ./scripts/check_wrapper_usage.sh

if [[ -z "$PYRITE_WRAPPED" ]]; then
    echo "ERROR: check_wrapper_usage.sh must be executed via ./scripts/run_gates.sh"
    exit 1
fi

echo "Scanning for direct command usage bypassing the wrapper..."

# Prohibited direct patterns (heuristic)
PROHIBITED_DIRECT=("python scripts/pyrite" "python tools/runtime/pyrite" "python tools/runtime/quarry" "python forge/src/compiler.py" "python tools/testing/pytest.py")

WARNING_COUNT=0

for PATTERN in "${PROHIBITED_DIRECT[@]}"; do
    # Search for lines containing the pattern but NOT the wrapper prefix
    # Use -n for line numbers
    MATCHES=$(grep -rn "$PATTERN" . \
        --include="*.md" --include="*.sh" --include="*.txt" \
        --exclude-dir=.git \
        --exclude-dir=node_modules \
        --exclude-dir=.cursor \
        --exclude-dir=.quarry \
        --exclude-dir=.pyrite \
        --exclude=run_gates.sh \
        --exclude=check_wrapper_usage.sh | grep -v "./scripts/run_gates.sh --")
    
    if [ -n "$MATCHES" ]; then
        # Process each match to format as WARN <n>: <path>:<line>: <snippet>
        while IFS= read -r line; do
            WARNING_COUNT=$((WARNING_COUNT + 1))
            echo "WARN $WARNING_COUNT: $line"
        done <<< "$MATCHES"
    fi
done

if [ $WARNING_COUNT -eq 0 ]; then
    echo "Success: No unwrapped command usage found (heuristics pass)."
    exit 0
else
    echo ""
    echo "Summary: Found $WARNING_COUNT unwrapped usage instances."
    echo "Note: This is a soft check (warning only)."
    exit 0 # Non-failing for now
fi
