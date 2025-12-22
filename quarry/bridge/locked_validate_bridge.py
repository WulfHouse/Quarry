"""FFI Bridge for Pyrite locked validation module

This module provides a Python interface to the Pyrite locked_validate.pyrite module.
The Pyrite module calls C functions for structural validation, and this bridge
handles version constraint checking and provides Python wrappers.
"""

import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Import DependencySource
try:
    from ..dependency import DependencySource
except ImportError:
    # Fallback if relative import fails
    import importlib.util
    dependency_path = Path(__file__).parent.parent / "dependency.py"
    spec = importlib.util.spec_from_file_location("dependency", dependency_path)
    dependency_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dependency_module)
    DependencySource = dependency_module.DependencySource

# Import version bridge for constraint checking
try:
    from .version_bridge import _version_satisfies_constraint
except ImportError:
    # Fallback if version_bridge not available
    def _version_satisfies_constraint(version: str, constraint: str) -> bool:
        """Python fallback for version constraint checking"""
        if constraint == "*":
            return True
        if constraint.startswith(">="):
            min_version = constraint[2:].strip()
            # Simple comparison
            def version_tuple(v):
                parts = v.split('.')
                return tuple(int(p) for p in parts if p.isdigit())
            return version_tuple(version) >= version_tuple(min_version)
        # Exact match
        return version == constraint

# Feature flags
# Master flag: PYRITE_ACCELERATE enables all Pyrite acceleration features
# Individual flag: PYRITE_USE_LOCKED_VALIDATE (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_LOCKED_VALIDATE_EXPLICIT = "PYRITE_USE_LOCKED_VALIDATE" in os.environ
USE_FFI = PYRITE_USE_LOCKED_VALIDATE_EXPLICIT and os.getenv("PYRITE_USE_LOCKED_VALIDATE", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_LOCKED_VALIDATE_EXPLICIT)

# Try to load shared library
_lib = None
if USE_FFI:
    try:
        # Find library path (will be built during compilation)
        compiler_dir = Path(__file__).parent.parent
        lib_name = "locked_validate"
        if sys.platform == "win32":
            lib_path = compiler_dir / "target" / f"{lib_name}.dll"
        elif sys.platform == "darwin":
            lib_path = compiler_dir / "target" / f"lib{lib_name}.dylib"
        else:
            lib_path = compiler_dir / "target" / f"lib{lib_name}.so"
        
        if lib_path.exists():
            _lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            _lib.validate_locked_deps.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.validate_locked_deps.restype = ctypes.c_int32
        else:
            # Library not found, fall back to Python
            USE_FFI = False
    except Exception as e:
        # FFI failed, fall back to Python
        USE_FFI = False
        print(f"Warning: Failed to load locked_validate FFI library: {e}", file=sys.stderr)


def validate_locked_deps_ffi(toml_deps: Dict[str, DependencySource],
                              lockfile_deps: Dict[str, DependencySource]) -> Tuple[bool, List[str], List[str]]:
    """Validate lockfile matches TOML dependencies using FFI
    
    Args:
        toml_deps: Dictionary mapping dependency name to DependencySource from Quarry.toml
        lockfile_deps: Dictionary mapping dependency name to DependencySource from Quarry.lock
    
    Returns:
        (is_valid, errors, warnings)
    """
    if USE_FFI and _lib:
        try:
            # Convert dependencies to JSON
            toml_dict = {}
            for name, source in toml_deps.items():
                toml_dict[name] = {
                    "type": source.type,
                    "version": source.version,
                    "git_url": source.git_url,
                    "git_branch": source.git_branch,
                    "commit": source.commit,
                    "path": source.path,
                    "checksum": source.checksum,
                    "hash": source.hash
                }
            
            lockfile_dict = {}
            for name, source in lockfile_deps.items():
                lockfile_dict[name] = {
                    "type": source.type,
                    "version": source.version,
                    "git_url": source.git_url,
                    "git_branch": source.git_branch,
                    "commit": source.commit,
                    "path": source.path,
                    "checksum": source.checksum,
                    "hash": source.hash
                }
            
            toml_json = json.dumps(toml_dict)
            lockfile_json = json.dumps(lockfile_dict)
            toml_bytes = toml_json.encode('utf-8')
            lockfile_bytes = lockfile_json.encode('utf-8')
            toml_arr = (ctypes.c_uint8 * len(toml_bytes)).from_buffer_copy(toml_bytes)
            lockfile_arr = (ctypes.c_uint8 * len(lockfile_bytes)).from_buffer_copy(lockfile_bytes)
            
            # Allocate result buffer
            result_cap = 65536
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            # Call FFI function
            ret = _lib.validate_locked_deps(toml_arr, len(toml_bytes), lockfile_arr, len(lockfile_bytes),
                                             result_buf, result_cap, ctypes.byref(result_len))
            
            if ret == 0:
                # Parse JSON result
                result_bytes = bytes(result_buf[:result_len.value])
                result_json = result_bytes.decode('utf-8')
                result_dict = json.loads(result_json)
                
                is_valid = result_dict.get("valid", False)
                errors = result_dict.get("errors", [])
                warnings = result_dict.get("warnings", [])
                
                # Add version constraint checking for registry dependencies
                for name, toml_source in toml_deps.items():
                    if name in lockfile_deps:
                        locked_source = lockfile_deps[name]
                        # For registry dependencies, verify locked version satisfies constraint
                        if toml_source.type == "registry" and locked_source.type == "registry":
                            if toml_source.version and locked_source.version:
                                if not _version_satisfies_constraint(locked_source.version, toml_source.version):
                                    errors.append(f"Quarry.lock is outdated. Locked version '{locked_source.version}' for '{name}' does not satisfy constraint '{toml_source.version}'")
                                    is_valid = False
                
                return (is_valid, errors, warnings)
        except Exception as e:
            # FFI error, fall back to Python
            pass
    
    # Python fallback
    return validate_locked_deps_python(toml_deps, lockfile_deps)


def validate_locked_deps_python(toml_deps: Dict[str, DependencySource],
                                 lockfile_deps: Dict[str, DependencySource]) -> Tuple[bool, List[str], List[str]]:
    """Python fallback implementation"""
    errors = []
    warnings = []
    
    # Check each TOML dependency
    for name, toml_source in toml_deps.items():
        if name not in lockfile_deps:
            errors.append(f"Quarry.lock is outdated. Dependency '{name}' in Quarry.toml not found in lockfile.")
            continue
        
        locked_source = lockfile_deps[name]
        
        # For registry dependencies, verify locked version satisfies constraint
        if toml_source.type == "registry" and locked_source.type == "registry":
            if toml_source.version and locked_source.version:
                if not _version_satisfies_constraint(locked_source.version, toml_source.version):
                    errors.append(f"Quarry.lock is outdated. Locked version '{locked_source.version}' for '{name}' does not satisfy constraint '{toml_source.version}'")
        
        # For git/path dependencies, verify source type matches
        elif toml_source.type != locked_source.type:
            errors.append(f"Quarry.lock is outdated. Source type mismatch for '{name}'")
    
    # Check for extra dependencies in lockfile (warnings)
    for name in lockfile_deps:
        if name not in toml_deps:
            warnings.append(f"Quarry.lock contains '{name}' which is not in Quarry.toml")
    
    is_valid = len(errors) == 0
    return (is_valid, errors, warnings)
