#!/bin/bash

# Pyrite Git Hooks Installer
# Usage: ./scripts/run_gates.sh -- ./scripts/setup/install-hooks.sh

HOOKS_DIR=".git/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "Error: .git directory not found. Are you in the repo root?"
    exit 1
fi

echo "Installing Git hooks..."

# 1. pre-commit: runs ./scripts/check_no_powershell.sh
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook: Check for prohibited PowerShell/CMD artifacts
./scripts/run_gates.sh -- ./scripts/check_no_powershell.sh
EOF
chmod +x "$HOOKS_DIR/pre-commit"
echo "  - Installed pre-commit (running check_no_powershell.sh)"

# 2. pre-push: runs ./scripts/run_fast.sh
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook: Run FAST gate
./scripts/run_gates.sh -- ./scripts/run_fast.sh
EOF
chmod +x "$HOOKS_DIR/pre-push"
echo "  - Installed pre-push (running run_fast.sh)"

echo "Git hooks installed successfully."

