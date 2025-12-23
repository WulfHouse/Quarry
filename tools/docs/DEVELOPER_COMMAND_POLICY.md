# Developer Command Execution Policy

## Non-Negotiable Rule

**ALL developer commands MUST use the `./scripts/run_gates.sh` wrapper. Direct command execution with pipeline truncators is FORBIDDEN.**

## Why This Policy Exists

Pipeline truncators like `head` or `tail` can cause early cancellation in some environments:
- They may stop reading before the command finishes.
- This can force upstream commands to stop (broken pipe).
- Agent runners may interpret this as **Cancelled** (not "failed").
- Cancellation halts the execution.

## Required Pattern

### ✅ CORRECT: Use Wrapper

```bash
./scripts/run_gates.sh -- python script.py args
```

### ❌ FORBIDDEN: Direct Execution with Truncators

```bash
# NEVER DO THIS:
python script.py 2>&1 | head -n 10
python script.py | tail -n 20
```

## Wrapper Location

- **Primary**: `./scripts/run_gates.sh` (argv-based, logging, timeout support)

## Wrapper Usage

```bash
./scripts/run_gates.sh [--timeout N] -- command [args...]
```

- `--timeout N` (optional): Kill command if it takes longer than N seconds.
- `--` (required): Separator between wrapper flags and the command.
- `command [args...]`: The full command to execute.

## How It Works

1. **Runs command to completion** - No live output piping for head/tail.
2. **Captures ALL output** - Both stdout and stderr to log files in `AppData/Local/pyrite/logs`.
3. **Preserves exit code** - Returns original command's exit code.
4. **Shell Enforcement** - Only runs in Git Bash (MSYS/MINGW).

## Enforcement

- All agent-run commands MUST use the wrapper.
- No exceptions for "quick tests" or "debugging".
- If a command needs filtering, filter the log file AFTER completion.

## Examples

### Compiling Pyrite Source

```bash
# ✅ CORRECT
./scripts/run_gates.sh -- python -m src.compiler file.pyrite --emit-llvm
```

### Running Tests

```bash
# ✅ CORRECT
./scripts/run_gates.sh -- python tools/testing/pytest.py
```

## Log Files

All command output is logged to the `AppData/Local/pyrite/logs` directory.
- Logs are preserved for debugging.
- Full output available in the `.out.log` and `.err.log` files.
