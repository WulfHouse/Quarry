"""FFI Bridge for Pyrite lockfile module

This module provides a Python interface to the Pyrite lockfile.pyrite module.
The Pyrite module calls C functions for the core logic, and this bridge loads
the shared library and provides Python wrappers.
"""

import os
import sys
import json
import ctypes
from pathlib import Path
from typing import Dict, Optional

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
# Individual flag: PYRITE_USE_LOCKFILE_CORE (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_LOCKFILE_CORE_EXPLICIT = "PYRITE_USE_LOCKFILE_CORE" in os.environ
USE_FFI = PYRITE_USE_LOCKFILE_CORE_EXPLICIT and os.getenv("PYRITE_USE_LOCKFILE_CORE", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_LOCKFILE_CORE_EXPLICIT)

# Try to load shared library
_lib = None
if USE_FFI:
    try:
        # Find library path (will be built during compilation)
        compiler_dir = Path(__file__).parent.parent
        lib_name = "lockfile"
        if sys.platform == "win32":
            lib_path = compiler_dir / "target" / f"{lib_name}.dll"
        elif sys.platform == "darwin":
            lib_path = compiler_dir / "target" / f"lib{lib_name}.dylib"
        else:
            lib_path = compiler_dir / "target" / f"lib{lib_name}.so"
        
        if lib_path.exists():
            _lib = ctypes.CDLL(str(lib_path))
            
            # Define function signatures
            _lib.generate_lockfile.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.generate_lockfile.restype = ctypes.c_int32
            
            _lib.read_lockfile.argtypes = [
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_uint8), ctypes.c_int64,
                ctypes.POINTER(ctypes.c_int64)
            ]
            _lib.read_lockfile.restype = ctypes.c_int32
        else:
            # Library not found, fall back to Python
            USE_FFI = False
    except Exception as e:
        # FFI failed, fall back to Python
        USE_FFI = False
        print(f"Warning: Failed to load lockfile FFI library: {e}", file=sys.stderr)


def generate_lockfile_ffi(resolved_deps: Dict[str, DependencySource], lockfile_path: str, project_dir: Path = None) -> None:
    """Generate lockfile using FFI
    
    Args:
        resolved_deps: Dictionary mapping dependency name to resolved DependencySource
        lockfile_path: Path to lockfile file
        project_dir: Project directory (for computing checksums, not used in FFI)
    """
    # Try to normalize dependencies before processing
    try:
        from .dep_fingerprint_bridge import normalize_dependency_set_ffi
        normalized_deps = normalize_dependency_set_ffi(resolved_deps)
    except (NameError, ImportError):
        # Fallback: use as-is
        normalized_deps = resolved_deps
    
    if USE_FFI and _lib:
        try:
            # Convert dependencies to JSON
            deps_dict = {}
            for name, source in normalized_deps.items():
                deps_dict[name] = {
                    "type": source.type,
                    "version": source.version,
                    "git_url": source.git_url,
                    "git_branch": source.git_branch,
                    "commit": source.commit,
                    "path": source.path,
                    "checksum": source.checksum,
                    "hash": source.hash
                }
            
            deps_json = json.dumps(deps_dict)
            deps_bytes = deps_json.encode('utf-8')
            deps_arr = (ctypes.c_uint8 * len(deps_bytes)).from_buffer_copy(deps_bytes)
            
            # Allocate result buffer
            result_cap = 65536
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            # Call FFI function
            ret = _lib.generate_lockfile(deps_arr, len(deps_bytes), result_buf, result_cap, ctypes.byref(result_len))
            
            if ret == 0:
                # Write TOML to file
                result_bytes = bytes(result_buf[:result_len.value])
                toml_text = result_bytes.decode('utf-8')
                Path(lockfile_path).write_text(toml_text, encoding='utf-8')
                return
        except Exception as e:
            # FFI error, fall back to Python
            pass
    
    # Python fallback
    generate_lockfile_python(resolved_deps, lockfile_path, project_dir)


def generate_lockfile_python(resolved_deps: Dict[str, DependencySource], lockfile_path: str, project_dir: Path = None) -> None:
    """Python fallback implementation"""
    from ..dependency import _compute_registry_checksum, _get_git_commit_hash, _compute_path_hash
    
    # Try to normalize dependencies before processing
    try:
        from .dep_fingerprint_bridge import normalize_dependency_set_ffi
        normalized_deps = normalize_dependency_set_ffi(resolved_deps)
    except (NameError, ImportError):
        # Fallback: use as-is
        normalized_deps = resolved_deps
    
    if project_dir is None:
        project_dir = Path.cwd()
    else:
        project_dir = Path(project_dir).resolve()
    
    lockfile = Path(lockfile_path)
    
    # Compute checksums/hashes for dependencies that don't have them
    deps_with_checksums = {}
    for name, source in normalized_deps.items():
        new_source = DependencySource(
            type=source.type,
            version=source.version,
            git_url=source.git_url,
            git_branch=source.git_branch,
            path=source.path,
            checksum=source.checksum,
            commit=source.commit,
            hash=source.hash
        )
        
        # Compute checksum/hash if not already set
        if source.type == "registry" and not source.checksum:
            checksum = _compute_registry_checksum(name, source.version, project_dir)
            if checksum:
                new_source.checksum = f"sha256:{checksum}"
        
        elif source.type == "git" and not source.commit:
            commit = _get_git_commit_hash(source.git_url, source.git_branch, project_dir)
            if commit:
                new_source.commit = commit
        
        elif source.type == "path" and not source.hash:
            path_hash = _compute_path_hash(source.path, project_dir)
            if path_hash:
                new_source.hash = f"sha256:{path_hash}"
        
        deps_with_checksums[name] = new_source
    
    # Try to use tomli_w for writing TOML
    try:
        import tomli_w
        lockfile_data = {"dependencies": {}}
        for name, source in sorted(deps_with_checksums.items()):
            if source.type == "registry":
                dep_entry = {"version": source.version}
                if source.checksum:
                    dep_entry["checksum"] = source.checksum
                lockfile_data["dependencies"][name] = dep_entry
            elif source.type == "git":
                dep_entry = {"git": source.git_url}
                if source.git_branch:
                    dep_entry["branch"] = source.git_branch
                if source.commit:
                    dep_entry["commit"] = source.commit
                lockfile_data["dependencies"][name] = dep_entry
            elif source.type == "path":
                dep_entry = {"path": source.path}
                if source.hash:
                    dep_entry["hash"] = source.hash
                lockfile_data["dependencies"][name] = dep_entry
        
        lockfile.write_text(tomli_w.dumps(lockfile_data), encoding='utf-8')
    except ImportError:
        # Fallback: write simple TOML format
        lines = ["[dependencies]"]
        for name, source in sorted(deps_with_checksums.items()):
            if source.type == "registry":
                if source.checksum:
                    lines.append(f'{name} = {{ version = "{source.version}", checksum = "{source.checksum}" }}')
                else:
                    lines.append(f'{name} = "{source.version}"')
            elif source.type == "git":
                parts = [f'git = "{source.git_url}"']
                if source.git_branch:
                    parts.append(f'branch = "{source.git_branch}"')
                if source.commit:
                    parts.append(f'commit = "{source.commit}"')
                lines.append(f'{name} = {{ {", ".join(parts)} }}')
            elif source.type == "path":
                parts = [f'path = "{source.path}"']
                if source.hash:
                    parts.append(f'hash = "{source.hash}"')
                lines.append(f'{name} = {{ {", ".join(parts)} }}')
        lockfile.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def read_lockfile_ffi(lockfile_path: str) -> Dict[str, DependencySource]:
    """Read lockfile using FFI
    
    Args:
        lockfile_path: Path to lockfile file
    
    Returns:
        Dictionary mapping dependency name to DependencySource
    """
    lockfile = Path(lockfile_path)
    
    if not lockfile.exists():
        return {}
    
    if USE_FFI and _lib:
        try:
            # Read lockfile text
            lockfile_text = lockfile.read_text(encoding='utf-8')
            lockfile_bytes = lockfile_text.encode('utf-8')
            lockfile_arr = (ctypes.c_uint8 * len(lockfile_bytes)).from_buffer_copy(lockfile_bytes)
            
            # Allocate result buffer
            result_cap = 65536
            result_buf = (ctypes.c_uint8 * result_cap)()
            result_len = ctypes.c_int64(0)
            
            # Call FFI function
            ret = _lib.read_lockfile(lockfile_arr, len(lockfile_bytes), result_buf, result_cap, ctypes.byref(result_len))
            
            if ret == 0:
                # Parse JSON result
                result_bytes = bytes(result_buf[:result_len.value])
                result_json = result_bytes.decode('utf-8')
                result_dict = json.loads(result_json)
                
                # Convert to DependencySource objects
                deps = {}
                for name, dep_data in result_dict.items():
                    deps[name] = DependencySource(
                        type=dep_data.get("type", ""),
                        version=dep_data.get("version"),
                        git_url=dep_data.get("git_url"),
                        git_branch=dep_data.get("git_branch"),
                        path=dep_data.get("path"),
                        checksum=dep_data.get("checksum"),
                        commit=dep_data.get("commit"),
                        hash=dep_data.get("hash")
                    )
                return deps
        except Exception as e:
            # FFI error, fall back to Python
            pass
    
    # Python fallback
    return read_lockfile_python(lockfile_path)


def read_lockfile_python(lockfile_path: str) -> Dict[str, DependencySource]:
    """Python fallback implementation"""
    from ..dependency import TOML_LOAD, _parse_dependency_source, _parse_dependencies_simple_with_sources
    
    lockfile = Path(lockfile_path)
    
    if not lockfile.exists():
        return {}
    
    try:
        lockfile_text = lockfile.read_text(encoding='utf-8')
        
        # Parse using available TOML library
        if TOML_LOAD:
            data = TOML_LOAD(lockfile_text)
            dependencies = data.get("dependencies", {})
            result = {}
            for name, value in dependencies.items():
                source = _parse_dependency_source(name, value)
                if source:
                    result[name] = source
            return result
        else:
            # Fallback: use simple parser
            return _parse_dependencies_simple_with_sources(lockfile_text)
    
    except Exception as e:
        print(f"Warning: Failed to parse {lockfile_path}: {e}", file=sys.stderr)
        return {}
