"""FFI Bridge for Pyrite TOML module

This module provides a Python interface to the Pyrite toml.pyrite module.
The Pyrite module calls C functions for the core logic, and this bridge loads
the shared library and provides Python wrappers.
"""

import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Dict, List, Optional

# Feature flags
# Master flag: PYRITE_ACCELERATE enables all Pyrite acceleration features
# Individual flag: PYRITE_USE_TOML_FFI (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_TOML_FFI_EXPLICIT = "PYRITE_USE_TOML_FFI" in os.environ
USE_FFI = PYRITE_USE_TOML_FFI_EXPLICIT and os.getenv("PYRITE_USE_TOML_FFI", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_TOML_FFI_EXPLICIT)

# Try to load shared library
_lib = None
if USE_FFI:
    try:
        # Find library path (will be built during compilation)
        compiler_dir = Path(__file__).parent.parent
        lib_name = "toml"
        if sys.platform == "win32":
            lib_path = compiler_dir / "target" / f"{lib_name}.dll"
        elif sys.platform == "darwin":
            lib_path = compiler_dir / "target" / f"lib{lib_name}.dylib"
        else:
            lib_path = compiler_dir / "target" / f"lib{lib_name}.so"
        
        if lib_path.exists():
            _lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            _lib.parse_dependencies_simple.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.parse_dependencies_simple.restype = ctypes.c_int32
            
            _lib.parse_workspace_simple.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.parse_workspace_simple.restype = ctypes.c_int32
        else:
            # Library not found, fall back to Python
            USE_FFI = False
    except Exception as e:
        # FFI failed, fall back to Python
        USE_FFI = False
        print(f"Warning: Failed to load TOML FFI library: {e}", file=sys.stderr)


def _parse_dependencies_simple(toml_text: str) -> Dict[str, str]:
    """Parse dependencies section from TOML text
    
    Args:
        toml_text: TOML file content as string
        
    Returns:
        Dictionary mapping dependency names to version strings
    """
    if USE_FFI and _lib:
        # Call Pyrite/C implementation
        toml_bytes = toml_text.encode('utf-8')
        toml_arr = (ctypes.c_uint8 * len(toml_bytes)).from_buffer_copy(toml_bytes)
        
        # Allocate result buffer (2KB should be enough)
        result_cap = 2048
        result_buf = (ctypes.c_uint8 * result_cap)()
        result_len = ctypes.c_int64(0)
        
        ret = _lib.parse_dependencies_simple(
            toml_arr, len(toml_bytes),
            result_buf, result_cap,
            ctypes.byref(result_len)
        )
        
        if ret == 0 and result_len.value > 0:
            # Parse JSON result
            json_str = bytes(result_buf[:result_len.value]).decode('utf-8')
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Fallback to Python if JSON parse fails
                pass
    
    # Python fallback (original implementation)
    dependencies = {}
    in_dependencies = False
    
    for line in toml_text.split('\n'):
        line = line.strip()
        
        # Check for [dependencies] section
        if line == "[dependencies]":
            in_dependencies = True
            continue
        
        # Check for next section (stops dependencies parsing)
        if line.startswith('[') and line.endswith(']'):
            if in_dependencies:
                break
            continue
        
        # Parse dependency line: name = "version"
        if in_dependencies and '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                name = parts[0].strip()
                value = parts[1].strip()
                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                dependencies[name] = value
    
    return dependencies


def _parse_workspace_simple(workspace_text: str) -> List[str]:
    """Parse workspace members from TOML text
    
    Args:
        workspace_text: TOML file content as string
        
    Returns:
        List of workspace member package names
    """
    if USE_FFI and _lib:
        # Call Pyrite/C implementation
        text_bytes = workspace_text.encode('utf-8')
        text_arr = (ctypes.c_uint8 * len(text_bytes)).from_buffer_copy(text_bytes)
        
        # Allocate result buffer (2KB should be enough)
        result_cap = 2048
        result_buf = (ctypes.c_uint8 * result_cap)()
        result_len = ctypes.c_int64(0)
        
        ret = _lib.parse_workspace_simple(
            text_arr, len(text_bytes),
            result_buf, result_cap,
            ctypes.byref(result_len)
        )
        
        if ret == 0 and result_len.value > 0:
            # Parse JSON result
            json_str = bytes(result_buf[:result_len.value]).decode('utf-8')
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Fallback to Python if JSON parse fails
                pass
    
    # Python fallback (original implementation)
    members = []
    in_workspace = False
    in_members = False
    
    for line in workspace_text.split('\n'):
        line = line.strip()
        
        if line == "[workspace]":
            in_workspace = True
            continue
        
        if in_workspace and line.startswith("members"):
            in_members = True
            # Parse members = ["pkg1", "pkg2"]
            if '=' in line:
                value_part = line.split('=', 1)[1].strip()
                # Simple parsing for array
                if '[' in value_part and ']' in value_part:
                    # Extract quoted strings
                    import re
                    matches = re.findall(r'"([^"]+)"', value_part)
                    members.extend(matches)
            continue
        
        if line.startswith('['):
            break
    
    return members
