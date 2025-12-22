# Quick Reference: Developer Command Policy

## ⚠️ MANDATORY: Use Wrapper for All Commands

**Every command that produces output MUST use the wrapper.**

## Quick Usage

```powershell
# Standard pattern
powershell -NoProfile -NonInteractive -File tools/utils/run_logged.ps1 -Cmd "<YOUR_COMMAND>" -Head 30 -Tail 30

# Or use the convenience helper
powershell -NoProfile -NonInteractive -File tools/utils/run_safe.ps1 -Cmd "<YOUR_COMMAND>" -Head 30 -Tail 30
```

## Why?

Pipeline truncators (`| Select-Object -First N`) cause **cancellation**, which halts the execution. The wrapper ensures commands complete fully.

## Full Documentation

- **Policy**: `tools/docs/DEVELOPER_COMMAND_POLICY.md`
- **Details**: `plans/CANCELLATION_PREVENTION.md`
- **Validation**: Run `tools/utils/validate_command_safety.ps1` to check your code

## Examples

### Compile Pyrite
```powershell
powershell -NoProfile -NonInteractive -File tools/utils/run_logged.ps1 -Cmd "python -m src.compiler file.pyrite --emit-llvm" -Head 30 -Tail 30
```

### Run Tests
```powershell
powershell -NoProfile -NonInteractive -File tools/utils/run_logged.ps1 -Cmd "python tools/pytest.py" -Head 50 -Tail 50
```

### Debug Command
```powershell
powershell -NoProfile -NonInteractive -File tools/utils/run_logged.ps1 -Cmd "python script.py --debug" -Head 0 -Tail 0
# Then filter log file if needed (AFTER completion)
```
