# Forge Bootstrap Guide

> **⚠️ ALPHA v1.1 STATUS**
> 
> This project is currently in **Alpha v1.1**. All repository content, including code, documentation, APIs, and specifications, is subject to change and may contain inconsistencies as development progresses toward Beta v1.0.

This guide explains how to bootstrap **Forge** (the Pyrite compiler) from a clean checkout.

## Prerequisites

Before bootstrapping, ensure you have:

1. **Python 3.8+** - Required for running Forge Stage0 (Python implementation)
   - Check version: `python --version`
   - Install from [python.org](https://www.python.org/downloads/)

2. **llvmlite** - Python bindings for LLVM
   - Install: `pip install llvmlite`
   - Verify: `python -c "import llvmlite; print(llvmlite.__version__)"`

3. **clang or gcc** - Required for linking object files into executables
   - Check clang: `clang --version`
   - Check gcc: `gcc --version`
   - At least one must be available in PATH

4. **LLVM toolchain** - Required for object file generation
   - Usually included with llvmlite installation
   - Verify: `python -c "from llvmlite import binding; print(binding.llvm_version)"`

## Quick Start (One Command)

The simplest way to bootstrap:

```bash
python scripts/bootstrap.py
```

This will:
1. Build Stage1 (Forge compiled by Python/Stage0)
2. Build Stage2 (Forge compiled by Stage1)
3. Run determinism check (verify Stage1 and Stage2 produce equivalent output)

## Manual Bootstrap Steps

If you need more control, you can run each step manually:

### Step 1: Build Stage1

```bash
python scripts/bootstrap/bootstrap_stage1.py
```

This compiles Forge source code using the Python implementation (Stage0), producing the Stage1 executable.

**Output**: `build/bootstrap/stage1/forge` (or `forge.exe` on Windows)

### Step 2: Build Stage2

```bash
python scripts/bootstrap/bootstrap_stage2.py
```

This compiles Forge source code using Stage1, producing the Stage2 executable.

**Output**: `build/bootstrap/stage2/forge` (or `forge.exe` on Windows)

### Step 3: Validate Self-Hosting

```bash
python scripts/bootstrap/validate_self_hosting.py
```

This verifies that Stage2 can:
- Compile all Forge modules
- Compile test programs

**Expected output**: `[OK] Self-hosting validation passed`

## Clean Checkout Verification

To verify self-hosting works from a completely clean checkout:

```bash
# Full verification (cleans and rebuilds everything)
python scripts/bootstrap/verify_clean_checkout.py --clean

# Skip Stage1 if it already exists
python scripts/bootstrap/verify_clean_checkout.py --skip-stage1

# Skip Stage2 if it already exists
python scripts/bootstrap/verify_clean_checkout.py --skip-stage2
```

This script:
1. Verifies prerequisites
2. Optionally cleans `build/bootstrap/` directory
3. Builds Stage1 (unless skipped)
4. Builds Stage2 (unless skipped)
5. Validates self-hosting
6. Verifies all artifacts exist

## Artifact Locations

After successful bootstrap, you'll find:

- **Stage1 executable**: `build/bootstrap/stage1/forge` (or `.exe` on Windows)
- **Stage2 executable**: `build/bootstrap/stage2/forge` (or `.exe` on Windows)
- **Stage1 object files**: `build/bootstrap/stage1/*.o`
- **Stage2 object files**: `build/bootstrap/stage2/*.o`
- **Runtime library**: `forge/runtime/libpyrite.a` (if built)

## Using Stage1 and Stage2

Once built, you can use the bootstrapped Forge compilers:

```bash
# Use Stage1 to compile Pyrite code
./build/bootstrap/stage1/forge hello.pyrite -o hello

# Use Stage2 to compile Pyrite code
./build/bootstrap/stage2/forge hello.pyrite -o hello
```

## Troubleshooting

### "llvmlite not found"

**Error**: `ModuleNotFoundError: No module named 'llvmlite'`

**Solution**: Install llvmlite:
```bash
pip install llvmlite
```

### "clang/gcc not found"

**Warning**: `[WARN] clang/gcc not found in PATH`

**Impact**: Compilation will work, but linking may fail. Install clang or gcc:
- **Windows**: Install via Visual Studio Build Tools or LLVM
- **macOS**: `xcode-select --install`
- **Linux**: `sudo apt-get install clang` or `sudo apt-get install gcc`

### "Stage1 build failed"

**Possible causes**:
- Missing Python dependencies
- Syntax errors in Pyrite compiler source
- LLVM/llvmlite version mismatch

**Solution**: Check error output, verify prerequisites, ensure Python compiler works.

### "Stage2 build failed"

**Possible causes**:
- Stage1 executable not found or broken
- Codegen features missing (enum constructors, Map, Option)
- Type checking errors in Pyrite modules

**Solution**: Rebuild Stage1, check that all codegen features are implemented.

### "Self-hosting validation failed"

**Possible causes**:
- Stage2 executable broken
- Missing codegen features
- Runtime library linking issues

**Solution**: Check validation output, verify Stage2 can compile simple programs.

## Determinism Check

After building Stage1 and Stage2, verify they produce equivalent output:

```bash
python scripts/bootstrap/check_bootstrap_determinism.py
```

This compares the LLVM IR generated by Stage1 and Stage2 for the same source code.

## Next Steps

After successful bootstrap:

1. **Run tests**: `python tools/testing/run_tests_batched.py`
2. **Develop**: Make changes to Pyrite compiler source
3. **Rebuild**: Run `python scripts/bootstrap/bootstrap_stage2.py` to rebuild Stage2
4. **Validate**: Run `python scripts/bootstrap/validate_self_hosting.py` to verify

## Additional Resources

- **Compiler source**: `forge/src-pyrite/`
- **Bootstrap scripts**: `scripts/bootstrap/`
- **Test suite**: `forge/tests/`
- **Runtime library**: `forge/runtime/`
