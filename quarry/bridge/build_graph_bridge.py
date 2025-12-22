"""FFI Bridge for Pyrite build_graph module

This module provides a Python interface to the Pyrite build_graph.pyrite module.
The Pyrite module calls C functions for the core logic, and this bridge loads
the shared library and provides Python wrappers.
"""

import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Dict, List

# Feature flags
# Master flag: PYRITE_ACCELERATE enables all Pyrite acceleration features
# Individual flag: PYRITE_USE_BUILD_GRAPH_FFI (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_BUILD_GRAPH_FFI_EXPLICIT = "PYRITE_USE_BUILD_GRAPH_FFI" in os.environ
USE_FFI = PYRITE_USE_BUILD_GRAPH_FFI_EXPLICIT and os.getenv("PYRITE_USE_BUILD_GRAPH_FFI", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_BUILD_GRAPH_FFI_EXPLICIT)

# Try to load shared library
_lib = None
if USE_FFI:
    try:
        # Find library path (will be built during compilation)
        compiler_dir = Path(__file__).parent.parent
        lib_name = "build_graph"
        if sys.platform == "win32":
            lib_path = compiler_dir / "target" / f"{lib_name}.dll"
        elif sys.platform == "darwin":
            lib_path = compiler_dir / "target" / f"lib{lib_name}.dylib"
        else:
            lib_path = compiler_dir / "target" / f"lib{lib_name}.so"
        
        if lib_path.exists():
            _lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            _lib.has_cycle.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int32)
            ]
            _lib.has_cycle.restype = ctypes.c_int32
            
            _lib.topological_sort.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.topological_sort.restype = ctypes.c_int32
        else:
            # Library not found, fall back to Python
            USE_FFI = False
    except Exception as e:
        # FFI failed, fall back to Python
        USE_FFI = False
        print(f"Warning: Failed to load build_graph FFI library: {e}", file=sys.stderr)


def _has_cycle_ffi(edges: Dict[str, List[str]]) -> bool:
    """Check if graph has cycles using FFI
    
    Args:
        edges: Dictionary mapping node names to lists of dependency names
              Example: {"A": ["B"], "B": ["A"]}
    
    Returns:
        True if cycle detected, False otherwise
    """
    if USE_FFI and _lib:
        # Convert edges dict to JSON
        edges_json = json.dumps(edges)
        edges_bytes = edges_json.encode('utf-8')
        edges_arr = (ctypes.c_uint8 * len(edges_bytes)).from_buffer_copy(edges_bytes)
        
        # Call FFI function
        result = ctypes.c_int32(0)
        ret = _lib.has_cycle(edges_arr, len(edges_bytes), ctypes.byref(result))
        
        if ret != 0:
            # FFI error, fall back to Python
            return _has_cycle_python(edges)
        
        return bool(result.value)
    else:
        return _has_cycle_python(edges)


def _has_cycle_python(edges: Dict[str, List[str]]) -> bool:
    """Python fallback implementation of cycle detection"""
    visited = set()
    rec_stack = set()
    
    def has_cycle_helper(node: str) -> bool:
        if node in rec_stack:
            return True
        if node in visited:
            return False
        
        visited.add(node)
        rec_stack.add(node)
        
        for dep in edges.get(node, []):
            if has_cycle_helper(dep):
                return True
        
        rec_stack.remove(node)
        return False
    
    for node in edges:
        if node not in visited:
            if has_cycle_helper(node):
                return True
    
    return False


def _topological_sort_ffi(edges: Dict[str, List[str]]) -> List[str]:
    """Topological sort using FFI
    
    Args:
        edges: Dictionary mapping node names to lists of dependency names
              Example: {"A": ["B"], "B": []}
    
    Returns:
        List of node names in topological order (dependencies first)
    
    Raises:
        ValueError: If graph contains cycles
    """
    if USE_FFI and _lib:
        # Convert edges dict to JSON
        edges_json = json.dumps(edges)
        edges_bytes = edges_json.encode('utf-8')
        edges_arr = (ctypes.c_uint8 * len(edges_bytes)).from_buffer_copy(edges_bytes)
        
        # Allocate result buffer (max 64KB should be enough)
        result_cap = 65536
        result_buf = (ctypes.c_uint8 * result_cap)()
        result_len = ctypes.c_int64(0)
        
        # Call FFI function
        ret = _lib.topological_sort(edges_arr, len(edges_bytes), result_buf, result_cap, ctypes.byref(result_len))
        
        if ret != 0:
            # FFI error (may be cycle), fall back to Python
            return _topological_sort_python(edges)
        
        # Parse JSON result
        result_bytes = bytes(result_buf[:result_len.value])
        result_json = result_bytes.decode('utf-8')
        result_list = json.loads(result_json)
        return result_list
    else:
        return _topological_sort_python(edges)


def _topological_sort_python(edges: Dict[str, List[str]]) -> List[str]:
    """Python fallback implementation of topological sort"""
    # Check for cycles first
    if _has_cycle_python(edges):
        raise ValueError("Build graph contains circular dependencies")
    
    # Build in-degree map
    in_degree = {}
    for name in edges:
        in_degree[name] = len(edges.get(name, []))
    
    # Start with nodes that have no dependencies (in-degree 0)
    queue = [name for name, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        current = queue.pop(0)
        result.append(current)
        
        # For packages that depend on current, reduce their in-degree
        for name, deps in edges.items():
            if current in deps:
                in_degree[name] -= 1
                if in_degree[name] == 0:
                    queue.append(name)
    
    # Check if all nodes were processed
    if len(result) != len(edges):
        raise ValueError("Topological sort failed: cycle detected")
    
    return result
