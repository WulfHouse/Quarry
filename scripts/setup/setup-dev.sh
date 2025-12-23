#!/bin/bash

# Pyrite Development Setup Script for Bash
# Adds convenient aliases for running Pyrite tools from anywhere in the repo
#
# Usage: source ./scripts/setup/setup-dev.sh

# Find the Pyrite repo root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

if [ ! -f "$REPO_ROOT/scripts/quarry" ]; then
    echo "Warning: Pyrite repository not found. Skipping alias setup."
    return
fi

# Create aliases
alias quarry="$REPO_ROOT/scripts/quarry"
alias pyrite="$REPO_ROOT/scripts/pyrite"
alias rebuild="$REPO_ROOT/scripts/rebuild"
alias pyrite_lsp="$REPO_ROOT/scripts/pyrite_lsp"
alias pyrite_test="$REPO_ROOT/scripts/pyrite_test"
alias run_gates="$REPO_ROOT/scripts/run_gates.sh"
alias run_fast="$REPO_ROOT/scripts/run_fast.sh"
alias run_full="$REPO_ROOT/scripts/run_full.sh"

echo "Pyrite development aliases loaded!"
echo ""
echo "Available commands:"
echo "  quarry <command>      # Build system (build, test, fmt, etc.)"
echo "  pyrite <file>         # Compiler (compile and run)"
echo "  rebuild               # Rebuild runtime library"
echo "  pyrite_lsp            # LSP server (for IDE integration)"
echo "  pyrite_test [args]    # Run tests"
echo "  run_gates [args]      # Gate runner"
echo "  run_fast              # Run FAST gate"
echo "  run_full              # Run FULL gate"
echo ""
echo "All commands work from anywhere in your shell!"

