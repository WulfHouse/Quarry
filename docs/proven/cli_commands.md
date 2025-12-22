# Proven CLI Commands

This document lists only CLI commands and flags that are **proven** to exist and work in the current repository, based on code evidence.

## Evidence Methodology

Each command listed here is backed by:
- Command handler function in `forge/quarry/main.py` or `forge/src/compiler.py`
- Command registration in the `main()` function
- Working examples or tests that use the command

## Forge Compiler Commands

**Entry Point**: `python -m src.compiler` (from forge directory) or `python tools/runtime/pyrite.py`

### Basic Compilation

```bash
cd forge && python -m src.compiler <input.pyrite>
python tools/runtime/pyrite.py <input.pyrite>
```

**Evidence:**
- Entry point: `forge/src/compiler.py:main()`
- Wrapper: `tools/runtime/pyrite.py:main()`
- Example usage in README.md

### Compiler Flags

#### Output File

```bash
cd forge && python -m src.compiler <input.pyrite> -o <output>
python tools/runtime/pyrite.py <input.pyrite> -o <output>
```

**Evidence:**
- Code: `forge/src/compiler.py:392-394` (parses `-o` flag)
- Code: `tools/runtime/pyrite.py:45` (compiler mode detection)

#### Emit LLVM IR

```bash
cd forge && python -m src.compiler <input.pyrite> --emit-llvm
```

**Evidence:**
- Code: `forge/src/compiler.py:395-397` (parses `--emit-llvm` flag)
- Function: `compile_file()` accepts `emit_llvm` parameter

#### Deterministic Builds

```bash
cd forge && python -m src.compiler <input.pyrite> --deterministic
```

**Evidence:**
- Code: `forge/src/compiler.py:398-400` (parses `--deterministic` flag)
- Function: `compile_file()` accepts `deterministic` parameter

#### Ownership Visualizations

```bash
cd forge && python -m src.compiler <input.pyrite> --visual
```

**Evidence:**
- Code: `forge/src/compiler.py:401-403` (parses `--visual` flag)
- Function: `compile_file()` accepts `visual` parameter

#### Cost Transparency Warnings

```bash
cd forge && python -m src.compiler <input.pyrite> --warn-cost
```

**Evidence:**
- Code: `forge/src/compiler.py:404-406` (parses `--warn-cost` flag)
- Function: `compile_file()` accepts `warn_cost` parameter

#### Incremental Compilation

```bash
cd forge && python -m src.compiler <input.pyrite> --incremental
cd forge && python -m src.compiler <input.pyrite> --no-incremental
```

**Evidence:**
- Code: `forge/src/compiler.py:407-412` (parses `--incremental` and `--no-incremental` flags)
- Function: `compile_file()` accepts `incremental` parameter (default: True)

#### Error Explanations

```bash
cd forge && python -m src.compiler --explain <CODE>
```

**Evidence:**
- Code: `forge/src/compiler.py:413-421` (parses `--explain` flag)
- Imports: `error_explanations.get_explanation()` and `error_explanations.list_error_codes()`

#### Help

```bash
cd forge && python -m src.compiler --help
python tools/runtime/pyrite.py --help
```

**Evidence:**
- Code: `forge/src/compiler.py:357-368` (usage message)
- Code: `tools/runtime/pyrite.py:135-154` (help output)

## Quarry Build System Commands

**Entry Point**: `python tools/runtime/quarry.py` or `python -m quarry.main`

### Project Management

#### Create New Project

```bash
python tools/runtime/quarry.py new <project_name>
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_new()`
- Registration: `forge/quarry/main.py:1244-1249`

### Building

#### Build Project

```bash
python tools/runtime/quarry.py build
python tools/runtime/quarry.py build --release
python tools/runtime/quarry.py build --deterministic
python tools/runtime/quarry.py build --no-incremental
python tools/runtime/quarry.py build --locked
python tools/runtime/quarry.py build --dogfood
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_build()`
- Registration: `forge/quarry/main.py:1251-1257`
- Flags parsed: `--release`, `--deterministic`, `--no-incremental`, `--locked`, `--dogfood`

#### Run Project

```bash
python tools/runtime/quarry.py run
python tools/runtime/quarry.py run --release
python tools/runtime/quarry.py run --args <arg1> <arg2> ...
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_run()`
- Registration: `forge/quarry/main.py:1259-1266`
- Flags parsed: `--release`, `--args`

#### Clean Build Artifacts

```bash
python tools/runtime/quarry.py clean
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_clean()`
- Registration: `forge/quarry/main.py:493`

### Testing

#### Run Tests

```bash
python tools/runtime/quarry.py test
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_test()`
- Registration: `forge/quarry/main.py:506`

### Code Quality

#### Format Code

```bash
python tools/runtime/quarry.py fmt
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_fmt()`
- Registration: `forge/quarry/main.py:513`

#### Auto-Fix Errors

```bash
python tools/runtime/quarry.py fix
python tools/runtime/quarry.py fix --interactive
python tools/runtime/quarry.py fix --auto
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_fix()`
- Registration: `forge/quarry/main.py:533-549`
- Flags parsed: `--interactive`, `--auto`

### Performance Analysis

#### Cost Analysis

```bash
python tools/runtime/quarry.py cost
python tools/runtime/quarry.py cost --json
python tools/runtime/quarry.py cost --level <level>
python tools/runtime/quarry.py cost --baseline <baseline>
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_cost()`
- Registration: `forge/quarry/main.py:550-562`
- Flags parsed: `--json`, `--level`, `--baseline`

#### Binary Size Analysis

```bash
python tools/runtime/quarry.py bloat
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_bloat()`
- Registration: `forge/quarry/main.py:563-602`

#### Performance Profiling

```bash
python tools/runtime/quarry.py perf
python tools/runtime/quarry.py perf --baseline
python tools/runtime/quarry.py perf --check
python tools/runtime/quarry.py perf --explain
python tools/runtime/quarry.py perf --threshold <threshold>
python tools/runtime/quarry.py perf --diff-asm <file>
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_perf()`
- Registration: `forge/quarry/main.py:603-609`
- Flags parsed: `--baseline`, `--check`, `--explain`, `--threshold`, `--diff-asm`

### Dependency Management

#### Resolve Dependencies

```bash
python tools/runtime/quarry.py resolve
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_resolve()`
- Registration: `forge/quarry/main.py:610-727`

#### Update Dependencies

```bash
python tools/runtime/quarry.py update
python tools/runtime/quarry.py update <package_name>
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_update()`
- Registration: `forge/quarry/main.py:728-834`

#### Install Dependencies

```bash
python tools/runtime/quarry.py install
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_install()`
- Registration: `forge/quarry/main.py:835-944`

#### Search Packages

```bash
python tools/runtime/quarry.py search
python tools/runtime/quarry.py search <query>
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_search()`
- Registration: `forge/quarry/main.py:945-991`

#### Package Information

```bash
python tools/runtime/quarry.py info
python tools/runtime/quarry.py info <package_name>
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_info()`
- Registration: `forge/quarry/main.py:992-1061`

#### Publish Package

```bash
python tools/runtime/quarry.py publish
python tools/runtime/quarry.py publish --dry-run
python tools/runtime/quarry.py publish --no-test
```

**Evidence:**
- Command handler: `forge/quarry/main.py:cmd_publish()`
- Registration: `forge/quarry/main.py:1062-1235`
- Flags parsed: `--dry-run`, `--no-test`

## Validation

To validate command claims:

1. Check command handler exists: `grep "def cmd_<command>" forge/quarry/main.py`
2. Check command registration: `grep "command == \"<command>\"" forge/quarry/main.py`
3. Try help output: `python tools/runtime/quarry.py --help` (if implemented)
4. Try the command: `python tools/runtime/quarry.py <command> --help` (if implemented)

## Notes

- Some commands may have incomplete implementations (see `LIMITATIONS.md`)
- Command-line help may not be fully implemented for all commands
- Flags may have different default values than documented in code comments
