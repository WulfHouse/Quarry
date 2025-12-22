"""FFI Bridge for Pyrite dependency fingerprinting module

This module provides a Python interface to the Pyrite dep_fingerprint.pyrite module.
The Pyrite module calls C functions for the core logic, and this bridge loads
the shared library and provides Python wrappers.
"""

import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Dict

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
# Individual flag: PYRITE_USE_DEP_FINGERPRINT (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_DEP_FINGERPRINT_EXPLICIT = "PYRITE_USE_DEP_FINGERPRINT" in os.environ
USE_FFI = PYRITE_USE_DEP_FINGERPRINT_EXPLICIT and os.getenv("PYRITE_USE_DEP_FINGERPRINT", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_DEP_FINGERPRINT_EXPLICIT)

# Try to load shared library
_lib = None
if USE_FFI:
    try:
        # Find library path (will be built during compilation)
        compiler_dir = Path(__file__).parent.parent
        lib_name = "dep_fingerprint"
        if sys.platform == "win32":
            lib_path = compiler_dir / "target" / f"{lib_name}.dll"
        elif sys.platform == "darwin":
            lib_path = compiler_dir / "target" / f"lib{lib_name}.dylib"
        else:
            lib_path = compiler_dir / "target" / f"lib{lib_name}.so"
        
        if lib_path.exists():
            _lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            _lib.normalize_dependency_source.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.normalize_dependency_source.restype = ctypes.c_int32
            
            _lib.normalize_dependency_set.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.normalize_dependency_set.restype = ctypes.c_int32
            
            _lib.compute_resolution_fingerprint.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.compute_resolution_fingerprint.restype = ctypes.c_int32
        else:
            # Library not found, fall back to Python
            USE_FFI = False
    except Exception as e:
        # FFI failed, fall back to Python
        USE_FFI = False
        print(f"Warning: Failed to load dep_fingerprint FFI library: {e}", file=sys.stderr)


def normalize_dependency_source_ffi(source: DependencySource) -> DependencySource:
    """Normalize a single dependency source to canonical form using FFI
    
    Args:
        source: DependencySource to normalize
        
    Returns:
        Normalized DependencySource
    """
    if USE_FFI and _lib:
        try:
            # Convert to JSON
            source_dict = source.to_dict()
            source_json = json.dumps(source_dict)
            source_bytes = source_json.encode('utf-8')
            source_arr = (ctypes.c_uint8 * len(source_bytes)).from_buffer_copy(source_bytes)
            
            # Allocate result buffer
            result_cap = 65536
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            # Call FFI function
            ret = _lib.normalize_dependency_source(source_arr, len(source_bytes), result_buf, result_cap, ctypes.byref(result_len))
            
            if ret == 0:
                # Parse JSON result
                result_bytes = bytes(result_buf[:result_len.value])
                result_json = result_bytes.decode('utf-8')
                result_dict = json.loads(result_json)
                
                # Convert to DependencySource
                return DependencySource(**result_dict)
        except Exception as e:
            # FFI error, fall back to Python
            pass
    
    # Python fallback
    return normalize_dependency_source_python(source)


def normalize_dependency_source_python(source: DependencySource) -> DependencySource:
    """Python fallback implementation"""
    # Normalize type to lowercase
    normalized_type = source.type.lower() if source.type else source.type
    
    # Normalize checksum/hash format (ensure lowercase hex)
    normalized_checksum = source.checksum
    if normalized_checksum and normalized_checksum.startswith("sha256:"):
        normalized_checksum = "sha256:" + normalized_checksum[7:].lower()
    
    normalized_hash = source.hash
    if normalized_hash and normalized_hash.startswith("sha256:"):
        normalized_hash = "sha256:" + normalized_hash[7:].lower()
    
    return DependencySource(
        type=normalized_type,
        version=source.version,
        git_url=source.git_url,
        git_branch=source.git_branch,
        path=source.path,
        checksum=normalized_checksum,
        commit=source.commit,
        hash=normalized_hash
    )


def normalize_dependency_set_ffi(dependencies: Dict[str, DependencySource]) -> Dict[str, DependencySource]:
    """Normalize dependency set (sort and canonicalize) using FFI
    
    Args:
        dependencies: Dictionary mapping dependency name to DependencySource
        
    Returns:
        Normalized dictionary (sorted by name, canonicalized)
    """
    if USE_FFI and _lib:
        try:
            # Convert to JSON
            deps_dict = {}
            for name, source in dependencies.items():
                deps_dict[name] = source.to_dict()
            
            deps_json = json.dumps(deps_dict)
            deps_bytes = deps_json.encode('utf-8')
            deps_arr = (ctypes.c_uint8 * len(deps_bytes)).from_buffer_copy(deps_bytes)
            
            # Allocate result buffer
            result_cap = 65536
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            # Call FFI function
            ret = _lib.normalize_dependency_set(deps_arr, len(deps_bytes), result_buf, result_cap, ctypes.byref(result_len))
            
            if ret == 0:
                # Parse JSON result
                result_bytes = bytes(result_buf[:result_len.value])
                result_json = result_bytes.decode('utf-8')
                result_dict = json.loads(result_json)
                
                # Convert to DependencySource objects
                normalized = {}
                for name, dep_data in result_dict.items():
                    normalized[name] = DependencySource(**dep_data)
                return normalized
        except Exception as e:
            # FFI error, fall back to Python
            pass
    
    # Python fallback
    return normalize_dependency_set_python(dependencies)


def normalize_dependency_set_python(dependencies: Dict[str, DependencySource]) -> Dict[str, DependencySource]:
    """Python fallback implementation"""
    # Normalize each dependency
    normalized = {}
    for name, source in dependencies.items():
        normalized[name] = normalize_dependency_source_python(source)
    
    # Sort by name (deterministic ordering)
    sorted_items = sorted(normalized.items())
    
    return dict(sorted_items)


def compute_resolution_fingerprint_ffi(dependencies: Dict[str, DependencySource]) -> str:
    """Compute resolution fingerprint for dependency set using FFI
    
    Args:
        dependencies: Dictionary mapping dependency name to DependencySource
        
    Returns:
        Hex fingerprint string (SHA-256, 64 characters)
    """
    if USE_FFI and _lib:
        try:
            # Convert to JSON
            deps_dict = {}
            for name, source in dependencies.items():
                deps_dict[name] = source.to_dict()
            
            deps_json = json.dumps(deps_dict)
            deps_bytes = deps_json.encode('utf-8')
            deps_arr = (ctypes.c_uint8 * len(deps_bytes)).from_buffer_copy(deps_bytes)
            
            # Allocate result buffer
            result_cap = 128
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            # Call FFI function
            ret = _lib.compute_resolution_fingerprint(deps_arr, len(deps_bytes), result_buf, result_cap, ctypes.byref(result_len))
            
            if ret == 0:
                # Parse hex string
                result_bytes = bytes(result_buf[:result_len.value])
                fingerprint = result_bytes.decode('utf-8')
                return fingerprint
        except Exception as e:
            # FFI error, fall back to Python
            pass
    
    # Python fallback
    return compute_resolution_fingerprint_python(dependencies)


def compute_resolution_fingerprint_python(dependencies: Dict[str, DependencySource]) -> str:
    """Python fallback implementation"""
    import hashlib
    
    # Normalize dependency set
    normalized = normalize_dependency_set_python(dependencies)
    
    # Build canonical JSON (deterministic)
    canonical_dict = {}
    for name, source in normalized.items():
        # Build canonical dict for this dependency (sorted fields)
        dep_dict = {"type": source.type}
        
        if source.type == "registry":
            if source.version:
                dep_dict["version"] = source.version
            if source.checksum:
                dep_dict["checksum"] = source.checksum
        elif source.type == "git":
            if source.git_url:
                dep_dict["git_url"] = source.git_url
            if source.git_branch:
                dep_dict["git_branch"] = source.git_branch
            if source.commit:
                dep_dict["commit"] = source.commit
        elif source.type == "path":
            if source.path:
                dep_dict["path"] = source.path
            if source.hash:
                dep_dict["hash"] = source.hash
        
        canonical_dict[name] = dep_dict
    
    # Serialize to deterministic JSON (no whitespace, sorted keys)
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':')).encode('utf-8')
    
    # Compute SHA-256 hash
    hasher = hashlib.sha256()
    hasher.update(canonical_json)
    return hasher.hexdigest()
