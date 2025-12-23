# Quick Reference: Developer Command Policy

## ⚠️ MANDATORY: Use Wrapper for All Commands

**Every command that produces output MUST use the wrapper.**

## Quick Usage

```bash
# Standard pattern
./scripts/run_gates.sh -- <YOUR_COMMAND>
```

## Why?

Pipeline truncators (`| head -n 30`) can cause **cancellation**, which halts the execution. The wrapper ensures commands complete fully and logs output safely.

## Full Documentation

- **Policy**: `tools/docs/DEVELOPER_COMMAND_POLICY.md`
- **Validation**: Run `./scripts/check_no_powershell.sh` to ensure no prohibited shell artifacts.

## Examples

### Compile Pyrite
```bash
./scripts/run_gates.sh -- python -m src.compiler file.pyrite --emit-llvm
```

### Run Tests
```bash
./scripts/run_gates.sh -- python tools/testing/pytest.py
```

### Debug Command
```bash
./scripts/run_gates.sh -- python script.py --debug
# Then filter log file if needed (AFTER completion)
```
