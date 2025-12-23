#!/bin/bash

# Fail-fast guard against reintroducing PowerShell or non-sh wrappers
# Usage: ./scripts/run_gates.sh -- ./scripts/check_no_powershell.sh

echo "Checking for prohibited PowerShell/CMD artifacts..."

PROHIBITED_EXTENSIONS=("*.ps1" "*.bat" "*.cmd")
# We allow .cmd only if they are the official entry points for Windows users (not for development automation)
# But per instructions "Remove PowerShell from Repo", we should be strict.
# Wait, the instructions say "No .ps1 wrappers or command entrypoints remain".
# It doesn't explicitly mention .cmd, but "Git Bash ONLY (hard lock)".

# 1. Check for .ps1 files
PS1_FILES=$(find . -name "*.ps1" -not -path "*/.git/*" -not -path "*/node_modules/*")
if [ -n "$PS1_FILES" ]; then
    echo "ERROR: Prohibited .ps1 files found:"
    echo "$PS1_FILES"
    exit 1
fi

# 2. Check for prohibited references in scripts and docs
# Exclude the check script itself and historical notes if any
PROHIBITED_PATTERNS=("powershell" "pwsh" "Select-Object" "Start-Process" "run_safe.ps1" "run_logged.ps1")

for PATTERN in "${PROHIBITED_PATTERNS[@]}"; do
    # Search in text files, excluding .git, node_modules, and this script
    MATCHES=$(grep -rEi "$PATTERN" . \
        --exclude-dir=.git \
        --exclude-dir=node_modules \
        --exclude-dir=.cursor \
        --exclude-dir=.quarry \
        --exclude-dir=.pyrite \
        --exclude=check_no_powershell.sh \
        --exclude=run_fast.sh \
        --exclude=README_COMMAND_POLICY.md \
        --exclude=*.log \
        --exclude=*.o \
        --exclude=*.exe \
        --exclude=*.pyc)
    
    if [ -n "$MATCHES" ]; then
        echo "ERROR: Prohibited pattern '$PATTERN' found in the following files:"
        echo "$MATCHES"
        exit 1
    fi
done

echo "Success: No PowerShell/CMD artifacts found."
exit 0

