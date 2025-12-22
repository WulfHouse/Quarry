# Test Suite Timing Baseline

This document establishes the baseline timing for the Pyrite test suite.

## Measurement Method

Test timing is measured using pytest's `--durations` flag:
- `python tools/testing/pytest.py --timing` - Generates `test_timing.json`
- `python tools/testing/run_tests_batched.py` - Runs tests in batches

## Test Suite Structure

- **Total tests**: ~246 tests
- **Test batches**: 15 batches

## Baseline Measurements

### Full Test Suite

**Environment**: Windows 10, Python 3.14, pytest 9.0.2

**Test Execution**:
- Total batches: 15
- Batched execution time: ~varies (depends on system load)
- Individual test timing: Available via `--durations` flag

### Slowest Tests (Top 10)

To identify slowest tests, run:
```bash
python tools/testing/pytest.py forge/tests --timing --durations=10
```

This generates `test_timing.json` with test durations.

**Note**: Actual slowest tests will be measured when timing infrastructure is fully working.

## Test Categories

### Fast Tests (< 0.1s)
- Lexer tests
- Parser tests (simple cases)
- Type checker tests (simple cases)
- Codegen tests (simple cases)

### Medium Tests (0.1s - 1s)
- Integration tests
- Complex parser tests
- Complex type checker tests

### Slow Tests (> 1s)
- Full pipeline tests
- Large file compilation tests
- Integration tests with multiple modules

## Performance Notes

- Most tests are fast (< 0.1s)
- Batched execution helps with parallelization
- Test suite completes in reasonable time

## Optimization Opportunities

If test suite becomes slow:

1. **Parallel execution**: Already using pytest-xdist (24 workers)
2. **Test selection**: Use `-k` flag to run specific tests
3. **Fast suite**: Define fast gating suite (see M13-T03)
4. **Test optimization**: Optimize slow tests individually
5. **Incremental testing**: Only run tests for changed files

## Measurement Commands

```bash
# Full suite with timing
python tools/testing/pytest.py forge/tests --timing

# Batched execution
python tools/testing/run_tests_batched.py

# Fast suite (when defined)
python tools/testing/pytest_fast.py

# Specific test file
python tools/testing/pytest.py forge/tests/test_lexer.py --timing
```

## Timing JSON Format

When `--timing` flag is used, `test_timing.json` is generated with format:
```json
{
  "test_name::test_function": duration_in_seconds,
  ...
}
```

## Future Updates

This baseline should be updated when:
- Significant test changes are made
- New test categories are added
- Performance optimizations are implemented
- Test infrastructure changes
