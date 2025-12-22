# Developer Command Execution Policy

## Non-Negotiable Rule

**ALL developer commands MUST use the `run_logged.ps1` wrapper. Direct command execution with pipeline truncators is FORBIDDEN.**

## Why This Policy Exists

Pipeline truncators like `Select-Object -First N` cause early cancellation:
- They stop reading after N items
- This forces upstream commands to stop (broken pipe)
- Agent runners interpret this as **Cancelled** (not "failed")
- Cancellation halts the execution

## Required Pattern

### ✅ CORRECT: Use Wrapper

```powershell
powershell -NoProfile -NonInteractive -File tools/utils/run_logged.ps1 -Cmd "python script.py args" -Head 20 -Tail 20
```

### ❌ FORBIDDEN: Direct Execution with Truncators

```powershell
# NEVER DO THIS:
python script.py 2>&1 | Select-Object -First 10
python script.py | Select-Object -Last 20
python script.py | more
python script.py | head
python script.py | tail
```

## Wrapper Location

- **Primary**: `tools/utils/run_logged.ps1` (full-featured, auto-generates log paths)
- **Main**: `tools/utils/run_logged.ps1` (full-featured version with auto-logging)

## Wrapper Parameters

- `-Cmd` (required): Full command line to execute
- `-Log` (optional): Log file path (default: auto-generated in `.logs/`)
- `-Head` (optional, default: 80): Number of first lines to print
- `-Tail` (optional, default: 80): Number of last lines to print

## How It Works

1. **Runs command to completion** - No live output piping
2. **Captures ALL output** - Both stdout and stderr to log file
3. **Shows filtered output** - First N and last N lines AFTER completion
4. **Preserves exit code** - Returns original command's exit code

## Enforcement

- All agent-run commands MUST use the wrapper
- No exceptions for "quick tests" or "debugging"
- If a command needs filtering, filter the LOG FILE after completion, not the live output

## Examples

### Compiling Pyrite Source

```powershell
# ✅ CORRECT
powershell -NoProfile -NonInteractive -File tools/utils/run_logged.ps1 -Cmd "python -m src.compiler file.pyrite --emit-llvm" -Head 30 -Tail 30

# ❌ FORBIDDEN
python -m src.compiler file.pyrite --emit-llvm 2>&1 | Select-Object -First 30
```

### Running Tests

```powershell
# ✅ CORRECT
powershell -NoProfile -NonInteractive -File tools/utils/run_logged.ps1 -Cmd "python tools/pytest.py" -Head 50 -Tail 50

# ❌ FORBIDDEN
python tools/pytest.py 2>&1 | Select-Object -First 50
```

### Debug Commands

```powershell
# ✅ CORRECT
powershell -NoProfile -NonInteractive -File tools/utils/run_logged.ps1 -Cmd "python script.py --debug" -Head 0 -Tail 0
# Then filter the log file if needed (AFTER completion)

# ❌ FORBIDDEN
python script.py --debug 2>&1 | Select-String -Pattern "ERROR" | Select-Object -First 20
```

## Log Files

All command output is automatically logged to `.logs/` directory:
- Logs are preserved for debugging
- Full output available even if only head/tail is shown
- Log filenames include timestamp and command hash

## Questions?

If you need to see full output, check the log file path shown at the end of wrapper output.
