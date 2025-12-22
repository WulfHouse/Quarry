# TOML C Backend

C implementation of TOML parsing functions for Pyrite, called via FFI.

## Functions

- `parse_dependencies_simple_c()` - Parses `[dependencies]` section from TOML text
- `parse_workspace_simple_c()` - Parses `[workspace]` section from TOML text

## Build

The C library should be compiled to a shared library:

- **Windows:** `forge/target/toml.dll`
- **macOS:** `forge/target/libtoml.dylib`
- **Linux:** `forge/target/libtoml.so`

### Manual Compilation (For Testing)

**Windows (MSVC):**
```powershell
cl /LD toml.c /Fe:../target/toml.dll
```

**macOS/Linux (GCC/Clang):**
```bash
gcc -shared -fPIC toml.c -o ../target/libtoml.so
```

**Note:** Production build system should handle this automatically.

## Enable FFI

Set environment variable:
```powershell
$env:PYRITE_USE_TOML_FFI="true"
```

The Python bridge (`quarry/toml_bridge.py`) will automatically:
1. Check the feature flag
2. Look for the library at the expected path
3. Load via ctypes if found
4. Fall back to Python implementation if unavailable

## See Also

- `WAVE2_TARGET_B_DONE.md` - Complete documentation
- `quarry/toml_bridge.py` - Python FFI bridge
- `src-pyrite/toml.pyrite` - Pyrite FFI declarations
