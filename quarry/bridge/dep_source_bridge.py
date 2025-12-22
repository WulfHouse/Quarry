"""FFI Bridge for Pyrite dep_source module

This module provides a Python interface to the Pyrite dep_source.pyrite module.
The Pyrite module calls C functions for the core logic, and this bridge loads
the shared library and provides Python wrappers.
"""

import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Optional, Dict, Any

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

# Feature flags
# Master flag: PYRITE_ACCELERATE enables all Pyrite acceleration features
# Individual flag: PYRITE_USE_DEP_SOURCE_FFI (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_DEP_SOURCE_FFI_EXPLICIT = "PYRITE_USE_DEP_SOURCE_FFI" in os.environ
USE_FFI = PYRITE_USE_DEP_SOURCE_FFI_EXPLICIT and os.getenv("PYRITE_USE_DEP_SOURCE_FFI", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_DEP_SOURCE_FFI_EXPLICIT)

# Try to load shared library
_lib = None
if USE_FFI:
    try:
        # Find library path (will be built during compilation)
        compiler_dir = Path(__file__).parent.parent
        lib_name = "dep_source"
        if sys.platform == "win32":
            lib_path = compiler_dir / "target" / f"{lib_name}.dll"
        elif sys.platform == "darwin":
            lib_path = compiler_dir / "target" / f"lib{lib_name}.dylib"
        else:
            lib_path = compiler_dir / "target" / f"lib{lib_name}.so"
        
        if lib_path.exists():
            _lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            _lib.parse_dependency_source.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.parse_dependency_source.restype = ctypes.c_int32
        else:
            # Library not found, fall back to Python
            USE_FFI = False
    except Exception as e:
        # FFI failed, fall back to Python
        USE_FFI = False
        print(f"Warning: Failed to load dep_source FFI library: {e}", file=sys.stderr)


def _parse_dependency_source_ffi(name: str, value) -> Optional[DependencySource]:
    """Parse dependency source using FFI
    
    Args:
        name: Dependency name
        value: TOML value (string or dict)
    
    Returns:
        DependencySource or None if invalid
    """
    if USE_FFI and _lib:
        try:
            # Convert value to JSON
            value_json = json.dumps(value)
            value_bytes = value_json.encode('utf-8')
            value_arr = (ctypes.c_uint8 * len(value_bytes)).from_buffer_copy(value_bytes)
            
            name_bytes = name.encode('utf-8')
            name_arr = (ctypes.c_uint8 * len(name_bytes)).from_buffer_copy(name_bytes)
            
            # Allocate result buffer (max 64KB should be enough)
            result_cap = 65536
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            # Call FFI function
            ret = _lib.parse_dependency_source(
                name_arr, len(name_bytes),
                value_arr, len(value_bytes),
                result_buf, result_cap,
                ctypes.byref(result_len)
            )
            
            if ret != 0:
                # FFI error, fall back to Python
                return _parse_dependency_source_python(name, value)
            
            # Parse JSON result
            result_bytes = bytes(result_buf[:result_len.value])
            result_json = result_bytes.decode('utf-8')
            
            if result_json == "null":
                return None
            
            result_dict = json.loads(result_json)
            
            # Convert to DependencySource
            return DependencySource(
                type=result_dict.get("type", ""),
                version=result_dict.get("version"),
                git_url=result_dict.get("git_url"),
                git_branch=result_dict.get("git_branch"),
                path=result_dict.get("path"),
                checksum=result_dict.get("checksum"),
                commit=result_dict.get("commit"),
                hash=result_dict.get("hash")
            )
        except Exception as e:
            # FFI error, fall back to Python
            return _parse_dependency_source_python(name, value)
    else:
        return _parse_dependency_source_python(name, value)


def _parse_dependency_source_python(name: str, value) -> Optional[DependencySource]:
    """Python fallback implementation of dependency source parsing"""
    if isinstance(value, str):
        # Registry dependency: "foo = "1.0.0""
        return DependencySource(type="registry", version=value)
    
    elif isinstance(value, dict):
        # Git or path dependency: "foo = { git = "...", branch = "main" }"
        if "git" in value:
            git_url = value.get("git")
            git_branch = value.get("branch") or value.get("tag") or value.get("rev")
            commit = value.get("commit")
            return DependencySource(type="git", git_url=git_url, git_branch=git_branch, commit=commit)
        
        elif "path" in value:
            path = value.get("path")
            path_hash = value.get("hash")
            return DependencySource(type="path", path=path, hash=path_hash)
        
        elif "version" in value:
            # Registry with explicit version: "foo = { version = "1.0.0", checksum = "sha256:..." }"
            version = value.get("version")
            checksum = value.get("checksum")
            return DependencySource(type="registry", version=version, checksum=checksum)
    
    return None
