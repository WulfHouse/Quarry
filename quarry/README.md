# Quarry - Pyrite Build System

Quarry is Pyrite's official build system and package manager, inspired by Cargo (Rust) and providing a zero-configuration workflow. Quarry uses **Forge** (the Pyrite compiler) to build projects.

## Commands

### Project Management

```bash
# Create new project
python tools/runtime/quarry.py new myproject

# Build project
python tools/runtime/quarry.py build                # Debug build
python tools/runtime/quarry.py build --release      # Optimized build

# Build and run
python tools/runtime/quarry.py run

# Clean build artifacts
python tools/runtime/quarry.py clean
```

### Code Quality

```bash
# Format code
python tools/runtime/quarry.py fmt

# Run tests
python tools/runtime/quarry.py test

# Auto-fix common errors
python tools/runtime/quarry.py fix                  # Interactive mode
python tools/runtime/quarry.py fix --auto           # Automatic mode
```

### Performance Analysis

```bash
# Analyze performance costs
python tools/runtime/quarry.py cost                 # Human-readable
python tools/runtime/quarry.py cost --json          # Machine-readable

# Analyze binary size
python tools/runtime/quarry.py bloat

# Performance profiling
python tools/runtime/quarry.py perf --baseline      # Generate Perf.lock
python tools/runtime/quarry.py perf --check         # Check for regressions
```

## Features

### Incremental Compilation

Quarry automatically caches compiled modules and only recompiles what changed:

```bash
$ python tools/runtime/quarry.py build
   Compiling 50 modules in 10.0s

$ # Change one file
$ touch src/utils.pyrite

$ python tools/runtime/quarry.py build
   [Cached] 49 modules
   [Compiled] src/utils.pyrite
   Finished in 0.8s  # 12x faster!
```

**Benefits:**
- 10-15x faster rebuilds
- Automatic dependency tracking
- Smart cache invalidation
- Works transparently

### Auto-Fix System

Quarry can automatically fix common errors:

```bash
$ python tools/runtime/quarry.py fix

[Fix 1/3]
  Pass reference to 'data' instead of moving
  File: src/main.pyrite:15
  Change:
    - process(data)
    + process(&data)
  Explanation: This changes the function call to borrow 'data'...
  
  Apply fix? [y/n/s] y
  ✓ Fix applied

Applied 1 fix(es)
```

**Fixes:**
- Use-after-move errors
- Borrow conflicts
- Type mismatches
- Undefined variables

### Cost Analysis

Track allocations and performance costs:

```bash
$ python tools/runtime/quarry.py cost

Performance Analysis
==================================================

Allocations: 12 sites (47 KB estimated)
  • Line 234: List[int] (24 bytes)
  • Line 156: Map[String, Config] (1024 bytes)

Copies: 3 sites (12 KB)
  • Line 567: ImageBuffer (4096 bytes)

✓ Analysis complete
```

**Use cases:**
- Find allocation hot spots
- Identify unnecessary copies
- Optimize memory usage
- Track performance costs

### Binary Size Analysis

Understand what's consuming binary space:

```bash
$ python tools/runtime/quarry.py bloat

Binary Size Analysis
============================================================

Total size: 47.2 KB

Section breakdown:
  .text (code):       38.4 KB
  .rodata (data):      6.2 KB
  .data (init):        1.5 KB
  .bss (uninit):       1.0 KB

Largest symbols (top 10):
   1.   4.2 KB  std::fmt
   2.   3.5 KB  panic_handler
   3.   2.9 KB  main
   ...

Optimization suggestions:
  • Use minimal-fmt (saves 3.4 KB)
  • Use --panic=abort (saves 3.2 KB)
```

**Use cases:**
- Embedded systems (flash constraints)
- Optimization guidance
- Dependency size tracking
- Regression detection

### Performance Lockfile

Prevent performance regressions in CI:

```bash
# Generate baseline
$ python tools/runtime/quarry.py perf --baseline
✓ Performance baseline saved to Perf.lock
  Total time: 234.5ms

# Check for regressions (in CI)
$ python tools/runtime/quarry.py perf --check

Checking performance against baseline (threshold: 5%)
============================================================

✓ Performance stable (change: +1.2%)
```

**Benefits:**
- Catch regressions before merge
- Track performance over time
- Enforce performance contracts
- "Fast forever" guarantee

### Package Management

Quarry includes a built-in package manager for dependency resolution and publishing:

```bash
# Resolve dependencies and generate Quarry.lock
python tools/runtime/quarry.py resolve

# Install dependencies from Quarry.lock
python tools/runtime/quarry.py install

# Search for packages in the registry
python tools/runtime/quarry.py search <query>

# Show package information
python tools/runtime/quarry.py info <package>

# Update dependencies
python tools/runtime/quarry.py update
python tools/runtime/quarry.py update --package <name>

# Publish package to registry
python tools/runtime/quarry.py publish
```

---

## Configuration

### Quarry.toml

```toml
[package]
name = "myproject"
version = "0.1.0"
edition = "2025"

[dependencies]
# Dependencies will be added here

[build]
incremental = true          # Enable incremental compilation
max-binary-size = "64KB"    # Fail if exceeded (embedded)

[profile.release]
opt-level = 3
lto = "thin"
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Pyrite
        run: curl -sSf https://get.pyrite-lang.org | sh
      
      - name: Format check
        run: quarry fmt --check
      
      - name: Build
        run: quarry build
      
      - name: Run tests
        run: quarry test
      
      - name: Check performance
        run: quarry perf --check
      
      - name: Check binary size
        run: quarry bloat
```

---

## Troubleshooting

### Incremental build issues

```bash
# Clear cache and rebuild
python tools/runtime/quarry.py clean
python tools/runtime/quarry.py build
```

### LSP not working

```bash
# Check LSP server location
ls ~/.pyrite/forge/lsp/pyrite-lsp.py

# Test LSP manually
python ~/.pyrite/forge/lsp/pyrite-lsp.py
```

### Performance check failing

```bash
# Regenerate baseline
python tools/runtime/quarry.py perf --baseline

# Check with higher threshold
python tools/runtime/quarry.py perf --check --threshold=10
```

---

## Development

### Running Quarry from Source

```bash
cd forge
python quarry/main.py build
```

### Testing

```bash
pytest tests/test_incremental.py -v
pytest tests/test_quarry_tools.py -v
pytest tests/test_lsp.py -v
```

---

## Learn More

- [Pyrite Specification](../docs/SSOT.md)
- [Forge Compiler](../forge/src/README.md)
- [Standard Library](../pyrite/README.md)

---

**Quarry makes Pyrite development fast, safe, and enjoyable!**

