#!/bin/bash

# FULL gate runner
# Usage: ./scripts/run_full.sh

echo "Running FULL gate..."

echo "Step 1/2: Type checker tests..."
./scripts/run_gates.sh -- python tools/testing/pytest.py forge/tests/middle/test_type_checker.py -v
if [ $? -ne 0 ]; then
    echo "FULL gate Step 1 failed!"
    exit 1
fi

echo "Step 2/2: Dogfood build..."
./scripts/run_gates.sh -- python quarry/main.py build --dogfood
if [ $? -ne 0 ]; then
    echo "FULL gate Step 2 failed!"
    exit 1
fi

echo "FULL gate passed!"

