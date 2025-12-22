"""FFI Bridge for Pyrite version module

This module provides a Python interface to the Pyrite version.pyrite module.
The Pyrite module calls C functions for the core logic, and this bridge loads
the shared library and provides Python wrappers.
"""

import os
import sys
import ctypes
from pathlib import Path
from typing import Optional

# Feature flags
# Master flag: PYRITE_ACCELERATE enables all Pyrite acceleration features
# Individual flag: PYRITE_USE_VERSION_FFI (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_VERSION_FFI_EXPLICIT = "PYRITE_USE_VERSION_FFI" in os.environ
USE_FFI = PYRITE_USE_VERSION_FFI_EXPLICIT and os.getenv("PYRITE_USE_VERSION_FFI", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_VERSION_FFI_EXPLICIT)

# Try to load shared library
_lib = None
if USE_FFI:
    try:
        # Find library path (will be built during compilation)
        compiler_dir = Path(__file__).parent.parent
        lib_name = "version"
        if sys.platform == "win32":
            lib_path = compiler_dir / "target" / f"{lib_name}.dll"
        elif sys.platform == "darwin":
            lib_path = compiler_dir / "target" / f"lib{lib_name}.dylib"
        else:
            lib_path = compiler_dir / "target" / f"lib{lib_name}.so"
        
        if lib_path.exists():
            _lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            _lib.compare_versions.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                                               ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64]
            _lib.compare_versions.restype = ctypes.c_int32
            
            _lib.version_satisfies_constraint.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                                                          ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64]
            _lib.version_satisfies_constraint.restype = ctypes.c_int32
            
            _lib.select_version.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.select_version.restype = ctypes.c_int32
            
            _lib.is_semver.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int32)
            ]
            _lib.is_semver.restype = ctypes.c_int32
            
            _lib.is_valid_package_name.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int32)
            ]
            _lib.is_valid_package_name.restype = ctypes.c_int32
            
            _lib.normalize_string.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.normalize_string.restype = ctypes.c_int32
        else:
            # Library not found, fall back to Python
            USE_FFI = False
    except Exception as e:
        # FFI failed, fall back to Python
        USE_FFI = False
        print(f"Warning: Failed to load version FFI library: {e}", file=sys.stderr)


def _compare_versions(v1: str, v2: str) -> int:
    """Compare two version strings
    
    Returns:
        -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
    """
    if USE_FFI and _lib:
        # Call Pyrite/C implementation
        v1_bytes = v1.encode('utf-8')
        v2_bytes = v2.encode('utf-8')
        v1_arr = (ctypes.c_uint8 * len(v1_bytes)).from_buffer_copy(v1_bytes)
        v2_arr = (ctypes.c_uint8 * len(v2_bytes)).from_buffer_copy(v2_bytes)
        result = _lib.compare_versions(v1_arr, len(v1_bytes), v2_arr, len(v2_bytes))
        return int(result)
    else:
        # Python fallback (original implementation)
        def version_tuple(v):
            parts = v.split('.')
            return tuple(int(p) for p in parts if p.isdigit())
        
        t1 = version_tuple(v1)
        t2 = version_tuple(v2)
        
        # Compare element by element, treating missing parts as 0
        max_len = max(len(t1), len(t2))
        for i in range(max_len):
            part1 = t1[i] if i < len(t1) else 0
            part2 = t2[i] if i < len(t2) else 0
            if part1 < part2:
                return -1
            elif part1 > part2:
                return 1
        
        return 0


def _version_satisfies_constraint(version: str, constraint: str) -> bool:
    """Check if a version satisfies a constraint
    
    Args:
        version: Version string (e.g., "1.0.0")
        constraint: Constraint string (e.g., ">=1.0.0", "1.0.0", "*")
        
    Returns:
        True if version satisfies constraint
    """
    if USE_FFI and _lib:
        # Call Pyrite/C implementation
        version_bytes = version.encode('utf-8')
        constraint_bytes = constraint.encode('utf-8')
        version_arr = (ctypes.c_uint8 * len(version_bytes)).from_buffer_copy(version_bytes)
        constraint_arr = (ctypes.c_uint8 * len(constraint_bytes)).from_buffer_copy(constraint_bytes)
        result = _lib.version_satisfies_constraint(version_arr, len(version_bytes),
                                                    constraint_arr, len(constraint_bytes))
        return bool(result)
    else:
        # Python fallback (original implementation)
        if constraint == "*":
            return True
        
        if constraint.startswith(">="):
            min_version = constraint[2:].strip()
            return _compare_versions(version, min_version) >= 0
        
        if constraint.startswith("~>"):
            # Pessimistic constraint: ~>1.0 means >=1.0.0 and <2.0.0
            # This means: major must match, and version must be >= base_version and < (major+1).0.0
            base_version = constraint[2:].strip()
            parts = base_version.split('.')
            if len(parts) >= 2:
                major = int(parts[0])
                minor = parts[1]
                # Check if version's major matches and it's >= base_version and < (major+1).0.0
                version_parts = version.split('.')
                if len(version_parts) >= 1:
                    version_major = int(version_parts[0])
                    # Major must match
                    if version_major != major:
                        return False
                    # Version must be >= base_version
                    if _compare_versions(version, base_version) < 0:
                        return False
                    # Version must be < (major+1).0.0
                    next_major = f"{major + 1}.0.0"
                    if _compare_versions(version, next_major) >= 0:
                        return False
                    return True
                return False
            return version.startswith(base_version)
        
        # Exact match
        return version == constraint


def _latest_version(versions: list) -> Optional[str]:
    """Get latest version from list"""
    if not versions:
        return None
    
    # Sort versions (simple: assume semantic versioning)
    sorted_versions = sorted(versions, key=lambda v: tuple(int(p) for p in v.split('.') if p.isdigit()), reverse=True)
    return sorted_versions[0]


def _select_version(constraint: str, available_versions: list) -> Optional[str]:
    """Select a version from available versions based on constraint
    
    Args:
        constraint: Version constraint (e.g., "1.0.0", ">=1.0.0", "~>1.0", "*")
        available_versions: List of available version strings
        
    Returns:
        Selected version string or None if no match
    """
    if USE_FFI and _lib:
        # Call Pyrite/C implementation
        import json
        
        constraint_bytes = constraint.encode('utf-8')
        constraint_arr = (ctypes.c_uint8 * len(constraint_bytes)).from_buffer_copy(constraint_bytes)
        
        # Convert available_versions to JSON array
        versions_json = json.dumps(available_versions)
        versions_bytes = versions_json.encode('utf-8')
        versions_arr = (ctypes.c_uint8 * len(versions_bytes)).from_buffer_copy(versions_bytes)
        
        # Allocate result buffer (2KB should be enough)
        result_cap = 2048
        result_buf = (ctypes.c_uint8 * result_cap)()
        result_len = ctypes.c_int64(0)
        
        ret = _lib.select_version(
            constraint_arr, len(constraint_bytes),
            versions_arr, len(versions_bytes),
            result_buf, result_cap,
            ctypes.byref(result_len)
        )
        
        if ret == 0 and result_len.value > 0:
            # Parse JSON result
            json_str = bytes(result_buf[:result_len.value]).decode('utf-8')
            try:
                result = json.loads(json_str)
                # Result is either a string (version) or null
                return result if isinstance(result, str) else None
            except json.JSONDecodeError:
                # Fallback to Python if JSON parse fails
                pass
    
    # Python fallback (original implementation)
    if constraint == "*":
        # Select latest version
        return _latest_version(available_versions)
    
    if constraint.startswith(">="):
        # >= constraint: select latest version >= specified
        min_version = constraint[2:].strip()
        matching = [v for v in available_versions if _compare_versions(v, min_version) >= 0]
        if matching:
            return _latest_version(matching)
        return None
    
    if constraint.startswith("~>"):
        # ~> constraint (pessimistic): select latest compatible version
        # ~>1.0 means >=1.0.0 and <2.0.0
        base_version = constraint[2:].strip()
        parts = base_version.split('.')
        if len(parts) >= 2:
            major = parts[0]
            minor = parts[1]
            # Match versions with same major.minor
            matching = [v for v in available_versions if v.startswith(f"{major}.{minor}")]
            if matching:
                return _latest_version(matching)
        return None
    
    # Exact version match
    if constraint in available_versions:
        return constraint
    
    # Try to find exact match
    return constraint if constraint in available_versions else None


def _is_semver(version: str) -> bool:
    """Check if version string is valid semantic version format
    
    Args:
        version: Version string to validate
        
    Returns:
        True if valid semver format, False otherwise
    """
    if USE_FFI and _lib:
        # Call Pyrite/C implementation
        version_bytes = version.encode('utf-8')
        version_arr = (ctypes.c_uint8 * len(version_bytes)).from_buffer_copy(version_bytes)
        result = ctypes.c_int32(0)
        
        ret = _lib.is_semver(version_arr, len(version_bytes), ctypes.byref(result))
        if ret == 0:
            return bool(result.value)
        # Fall through to Python if FFI call failed
    
    # Python fallback (original implementation)
    import re
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$'
    return bool(re.match(pattern, version))


def _is_valid_package_name(name: str) -> bool:
    """Check if package name is valid
    
    Args:
        name: Package name string to validate
        
    Returns:
        True if valid package name format, False otherwise
    """
    if USE_FFI and _lib:
        # Call Pyrite/C implementation
        name_bytes = name.encode('utf-8')
        name_arr = (ctypes.c_uint8 * len(name_bytes)).from_buffer_copy(name_bytes)
        result = ctypes.c_int32(0)
        
        ret = _lib.is_valid_package_name(name_arr, len(name_bytes), ctypes.byref(result))
        if ret == 0:
            return bool(result.value)
        # Fall through to Python if FFI call failed
    
    # Python fallback (original implementation)
    if not name or len(name) == 0:
        return False
    
    # Cannot start or end with hyphen or underscore
    if name[0] == '-' or name[0] == '_' or name[-1] == '-' or name[-1] == '_':
        return False
    
    # All characters must be alphanumeric, hyphen, or underscore
    import re
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, name))


def _normalize_string(s: str) -> str:
    """Normalize string (trim whitespace and convert to lowercase)
    
    Args:
        s: String to normalize
        
    Returns:
        Normalized string (trimmed and lowercased)
    """
    if USE_FFI and _lib:
        # Call Pyrite/C implementation
        s_bytes = s.encode('utf-8')
        s_arr = (ctypes.c_uint8 * len(s_bytes)).from_buffer_copy(s_bytes)
        
        # Allocate result buffer (same size as input should be enough)
        result_cap = len(s_bytes) + 1
        result_buf = (ctypes.c_uint8 * result_cap)()
        result_len = ctypes.c_int64(0)
        
        ret = _lib.normalize_string(s_arr, len(s_bytes), result_buf, result_cap, ctypes.byref(result_len))
        if ret == 0 and result_len.value > 0:
            return bytes(result_buf[:result_len.value]).decode('utf-8')
        elif ret == 0:
            return ""  # Empty result
        # Fall through to Python if FFI call failed
    
    # Python fallback (original implementation)
    if not s:
        return ""
    return s.strip().lower()
