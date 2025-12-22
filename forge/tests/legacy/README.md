# Legacy Tests

This directory is for tests that are marked for replacement or refactoring.

## Purpose

Legacy tests are tests that:
- Are flaky or non-deterministic
- Are too slow for their category
- Have unclear purpose or poor maintainability
- Need significant refactoring

## Process

1. **Identify legacy test**: Test fails frequently, is slow, or is hard to maintain
2. **Move to legacy/**: Move test file here
3. **Add `@pytest.mark.legacy`**: Mark test with legacy marker
4. **Document**: Add entry to this README explaining why it's legacy
5. **Plan replacement**: Create issue/plan for replacement test
6. **Run in Lane 3 only**: Legacy tests excluded from Lane 1/2

## Current Legacy Tests

*None yet - this directory is prepared for future use*

## Replacement Strategy

When replacing a legacy test:
1. Write new test with clear purpose
2. Ensure new test is fast and deterministic
3. Add appropriate marker (fast/integration/slow)
4. Verify new test passes
5. Remove legacy test
6. Update this README

## CI Integration

Legacy tests run only in Lane 3 (nightly full regression):
- Excluded from Lane 1 (fast PR gating)
- Excluded from Lane 2 (integration tests)
- Run in nightly job for visibility
