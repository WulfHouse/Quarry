#!/bin/bash

# FAST gate runner
# Usage: ./scripts/run_gates.sh -- ./scripts/run_fast.sh

if [[ -z "$PYRITE_WRAPPED" ]]; then
    echo "ERROR: run_fast.sh must be executed via ./scripts/run_gates.sh"
    exit 1
fi

echo "Running PowerShell ban check..."
./scripts/run_gates.sh -- ./scripts/check_no_powershell.sh
if [ $? -ne 0 ]; then
    echo "PowerShell ban check failed!"
    exit 1
fi

echo "Running Wrapper Usage check (soft)..."
./scripts/run_gates.sh -- ./scripts/check_wrapper_usage.sh
# Non-failing for now, so no exit on error

./scripts/run_gates.sh -- python tools/testing/pytest.py forge/tests/middle/test_type_checker.py -v -m fast

