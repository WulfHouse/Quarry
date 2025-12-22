"""FFI Bridge for Pyrite path_utils module

This module provides a Python interface to the Pyrite path_utils.pyrite module.
The Pyrite module calls C functions for the core logic, and this bridge loads
the shared library and provides Python wrappers.
"""

import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Optional

# Feature flags
# Master flag: PYRITE_ACCELERATE enables all Pyrite acceleration features
# Individual flag: PYRITE_USE_PATH_UTILS_FFI (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_PATH_UTILS_FFI_EXPLICIT = "PYRITE_USE_PATH_UTILS_FFI" in os.environ
USE_FFI = PYRITE_USE_PATH_UTILS_FFI_EXPLICIT and os.getenv("PYRITE_USE_PATH_UTILS_FFI", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_PATH_UTILS_FFI_EXPLICIT)

# Try to load shared library
_lib = None
if USE_FFI:
    try:
        # Find library path (will be built during compilation)
        compiler_dir = Path(__file__).parent.parent
        lib_name = "path_utils"
        if sys.platform == "win32":
            lib_path = compiler_dir / "target" / f"{lib_name}.dll"
        elif sys.platform == "darwin":
            lib_path = compiler_dir / "target" / f"lib{lib_name}.dylib"
        else:
            lib_path = compiler_dir / "target" / f"lib{lib_name}.so"
        
        if lib_path.exists():
            _lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            _lib.is_absolute.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int32)
            ]
            _lib.is_absolute.restype = ctypes.c_int32
            
            _lib.resolve_path.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.resolve_path.restype = ctypes.c_int32
            
            _lib.join_paths.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.join_paths.restype = ctypes.c_int32
            
            _lib.relative_path.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.relative_path.restype = ctypes.c_int32
        else:
            # Library not found, fall back to Python
            USE_FFI = False
    except Exception as e:
        # FFI failed, fall back to Python
        USE_FFI = False
        print(f"Warning: Failed to load path_utils FFI library: {e}", file=sys.stderr)


def is_absolute_ffi(path: str) -> bool:
    """Check if path is absolute using FFI"""
    if USE_FFI and _lib:
        try:
            path_bytes = path.encode('utf-8')
            path_arr = (ctypes.c_uint8 * len(path_bytes)).from_buffer_copy(path_bytes)
            result = ctypes.c_int32(0)
            ret = _lib.is_absolute(path_arr, len(path_bytes), ctypes.byref(result))
            if ret == 0:
                return bool(result.value)
        except Exception:
            pass
    return is_absolute_python(path)


def is_absolute_python(path: str) -> bool:
    """Python fallback implementation"""
    return Path(path).is_absolute()


def resolve_path_ffi(path: str, base: Optional[str] = None) -> str:
    """Resolve path to absolute using FFI"""
    if USE_FFI and _lib:
        try:
            path_bytes = path.encode('utf-8')
            path_arr = (ctypes.c_uint8 * len(path_bytes)).from_buffer_copy(path_bytes)
            
            base_bytes = base.encode('utf-8') if base else b""
            base_arr = (ctypes.c_uint8 * len(base_bytes)).from_buffer_copy(base_bytes) if base else None
            
            result_cap = 4096
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            ret = _lib.resolve_path(
                path_arr, len(path_bytes),
                base_arr if base else None, len(base_bytes) if base else 0,
                result_buf, result_cap,
                ctypes.byref(result_len)
            )
            
            if ret == 0:
                result_bytes = bytes(result_buf[:result_len.value])
                return result_bytes.decode('utf-8')
        except Exception:
            pass
    return resolve_path_python(path, base)


def resolve_path_python(path: str, base: Optional[str] = None) -> str:
    """Python fallback implementation"""
    if base:
        return str((Path(base) / path).resolve())
    else:
        return str(Path(path).resolve())


def join_paths_ffi(*parts: str) -> str:
    """Join path components using FFI"""
    if USE_FFI and _lib and len(parts) > 0:
        try:
            parts_json = json.dumps(parts)
            parts_bytes = parts_json.encode('utf-8')
            parts_arr = (ctypes.c_uint8 * len(parts_bytes)).from_buffer_copy(parts_bytes)
            
            result_cap = 4096
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            ret = _lib.join_paths(parts_arr, len(parts_bytes), result_buf, result_cap, ctypes.byref(result_len))
            
            if ret == 0:
                result_bytes = bytes(result_buf[:result_len.value])
                return result_bytes.decode('utf-8')
        except Exception:
            pass
    return join_paths_python(*parts)


def join_paths_python(*parts: str) -> str:
    """Python fallback implementation"""
    if not parts:
        return ""
    result = Path(parts[0])
    for part in parts[1:]:
        result = result / part
    return str(result)


def relative_path_ffi(path: str, base: str) -> Optional[str]:
    """Get relative path from base to path using FFI"""
    if USE_FFI and _lib:
        try:
            path_bytes = path.encode('utf-8')
            path_arr = (ctypes.c_uint8 * len(path_bytes)).from_buffer_copy(path_bytes)
            
            base_bytes = base.encode('utf-8')
            base_arr = (ctypes.c_uint8 * len(base_bytes)).from_buffer_copy(base_bytes)
            
            result_cap = 4096
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            ret = _lib.relative_path(
                path_arr, len(path_bytes),
                base_arr, len(base_bytes),
                result_buf, result_cap,
                ctypes.byref(result_len)
            )
            
            if ret == 0:
                result_bytes = bytes(result_buf[:result_len.value])
                result_str = result_bytes.decode('utf-8')
                if result_str == "null":
                    return None
                return result_str
        except Exception:
            pass
    return relative_path_python(path, base)


def relative_path_python(path: str, base: str) -> Optional[str]:
    """Python fallback implementation"""
    try:
        rel = Path(path).resolve().relative_to(Path(base).resolve())
        return str(rel)
    except ValueError:
        # No relative path exists
        return None
