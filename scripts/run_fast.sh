#!/bin/bash

# FAST gate runner
# Usage: ./scripts/run_fast.sh

echo "Running PowerShell ban check..."
./scripts/run_gates.sh -- ./scripts/check_no_powershell.sh
if [ $? -ne 0 ]; then
    echo "PowerShell ban check failed!"
    exit 1
fi

./scripts/run_gates.sh -- python tools/testing/pytest.py forge/tests/middle/test_type_checker.py -v -m fast

