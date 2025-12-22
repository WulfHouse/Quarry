# Compile Time Baseline

This document establishes the baseline compile times for the Pyrite compiler bootstrap process.

## Measurement Method

Timing is measured in the bootstrap scripts:
- `scripts/bootstrap/bootstrap_stage1.py` - Times each module compilation and total Stage1 build
- `scripts/bootstrap/bootstrap_stage2.py` - Times each module compilation and total Stage2 build

Timing includes:
- Individual module compilation time
- Total module compilation time
- Linking time
- Total build time

## Baseline Measurements

### Stage1 Build (Python Compiler → Pyrite Compiler)

**Environment**: Windows 10, Python 3.14, clang available

**Module Compilation Times** (measured):
- `main.pyrite`: 0.69s
- `diagnostics.pyrite`: 0.59s
- `ast.pyrite`: 0.53s
- `types.pyrite`: 0.48s
- `tokens.pyrite`: 0.39s
- `symbol_table.pyrite`: 0.01s (fails early due to type checking)

**Total Module Compilation**: 2.69s
**Linking Time**: 0.39s
**Total Stage1 Build**: 3.08s

### Stage2 Build (Stage1 Compiler → Pyrite Compiler)

**Environment**: Windows 10, Stage1 executable available

**Module Compilation Times** (measured):
- `diagnostics.pyrite`: 0.06s
- `ast.pyrite`: 0.06s
- `main.pyrite`: 0.06s
- `symbol_table.pyrite`: 0.06s (fails due to type checking)
- `tokens.pyrite`: 0.05s
- `types.pyrite`: 0.05s

**Total Module Compilation**: 0.34s
**Linking Time**: 0.50s
**Total Stage2 Build**: 0.84s

## Slowest Modules

Based on measurements:

**Stage1 (Python compiler)**:
1. **main.pyrite** - 0.69s (entry point, complex logic)
2. **diagnostics.pyrite** - 0.59s (diagnostic message handling)
3. **ast.pyrite** - 0.53s (complex AST node definitions)

**Stage2 (Stage1 compiler)**:
- All modules compile in ~0.05-0.06s (very fast)
- No significant bottlenecks identified

## Performance Notes

- **Stage1**: Module compilation takes 0.4-0.7s per module (Python compiler overhead)
- **Stage2**: Module compilation is very fast (< 0.1s per module)
- Linking takes ~0.4-0.5s (similar for both stages)
- Total bootstrap time: ~3s for Stage1, ~0.8s for Stage2
- Performance is acceptable for development workflow
- Stage2 is significantly faster than Stage1 (native compiler vs Python)

## Optimization Opportunities

If compile time becomes a concern:

1. **Parallel compilation**: Compile modules in parallel (currently sequential)
2. **Incremental compilation**: Only recompile changed modules
3. **Linker optimization**: Use faster linker or optimize linking process
4. **Codegen optimization**: Optimize LLVM IR generation if it becomes a bottleneck

## Measurement Command

To measure current baseline:

```bash
# Stage1 build with timing
python scripts/bootstrap/bootstrap_stage1.py

# Stage2 build with timing
python scripts/bootstrap/bootstrap_stage2.py
```

Timing summary is printed at the end of each build.

## Future Updates

This baseline should be updated when:
- Significant codegen changes are made
- New modules are added
- Performance optimizations are implemented
- Toolchain versions change
