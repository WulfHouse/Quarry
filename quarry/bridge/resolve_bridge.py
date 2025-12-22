"""FFI Bridge for Pyrite resolve module

This module provides a Python interface to orchestrate Pyrite-owned resolve workflow.
It composes existing Pyrite bridges (toml, dep_source, version, lockfile, fingerprint)
into a cohesive resolve vertical.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Optional

# Import DependencySource
try:
    from ..dependency import DependencySource
except ImportError:
    import importlib.util
    dependency_path = Path(__file__).parent.parent / "dependency.py"
    spec = importlib.util.spec_from_file_location("dependency", dependency_path)
    dependency_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dependency_module)
    DependencySource = dependency_module.DependencySource

# Feature flags
# Master flag: PYRITE_ACCELERATE enables all Pyrite acceleration features
# Individual flag: PYRITE_USE_RESOLVE_CORE (can override master flag if explicitly set)
PYRITE_ACCELERATE = os.getenv("PYRITE_ACCELERATE", "").lower() in ("1", "true", "yes", "on")
PYRITE_USE_RESOLVE_CORE_EXPLICIT = "PYRITE_USE_RESOLVE_CORE" in os.environ
USE_FFI = PYRITE_USE_RESOLVE_CORE_EXPLICIT and os.getenv("PYRITE_USE_RESOLVE_CORE", "false").lower() == "true"
USE_FFI = USE_FFI or (PYRITE_ACCELERATE and not PYRITE_USE_RESOLVE_CORE_EXPLICIT)

# Import existing Pyrite bridges
try:
    from .toml_bridge import _parse_dependencies_simple
    TOML_BRIDGE_AVAILABLE = True
except ImportError:
    TOML_BRIDGE_AVAILABLE = False

try:
    from .dep_source_bridge import _parse_dependency_source_ffi
    DEP_SOURCE_BRIDGE_AVAILABLE = True
except ImportError:
    DEP_SOURCE_BRIDGE_AVAILABLE = False

try:
    from .version_bridge import _select_version, _latest_version, _compare_versions
    VERSION_BRIDGE_AVAILABLE = True
except ImportError:
    VERSION_BRIDGE_AVAILABLE = False

try:
    from .lockfile_bridge import generate_lockfile_ffi, generate_lockfile_python
    LOCKFILE_BRIDGE_AVAILABLE = True
except ImportError:
    LOCKFILE_BRIDGE_AVAILABLE = False

try:
    from .dep_fingerprint_bridge import (
        normalize_dependency_set_ffi,
        compute_resolution_fingerprint_ffi
    )
    FINGERPRINT_BRIDGE_AVAILABLE = True
except ImportError:
    FINGERPRINT_BRIDGE_AVAILABLE = False


def resolve_dependencies_ffi(toml_content: str, project_dir: Path = None) -> Dict:
    """Resolve dependencies using Pyrite bridges
    
    Args:
        toml_content: TOML file content (string)
        project_dir: Project directory (optional, for relative paths)
        
    Returns:
        Dictionary with:
        - "resolved": Dict[str, DependencySource] - Resolved dependencies
        - "lockfile_content": str - Generated lockfile TOML content
        - "formatted_output": str - Console output text
        - "fingerprint": str - Resolution fingerprint
    """
    if not USE_FFI:
        return resolve_dependencies_python(toml_content, project_dir)
    
    try:
        # Step 1: Parse TOML and extract dependencies
        deps = _parse_quarry_toml_ffi(toml_content)
        
        # Step 2: Handle empty dependencies
        if not deps:
            # Generate empty lockfile
            lockfile_content = _generate_empty_lockfile()
            formatted_output = "Resolving dependencies...\nNo dependencies found in Quarry.toml\nGenerated Quarry.lock (empty)\n"
            fingerprint = compute_resolution_fingerprint_ffi({}) if FINGERPRINT_BRIDGE_AVAILABLE else ""
            
            return {
                "resolved": {},
                "lockfile_content": lockfile_content,
                "formatted_output": formatted_output,
                "fingerprint": fingerprint
            }
        
        # Step 3: Resolve versions
        resolved = _resolve_dependencies_ffi(deps)
        
        # Step 4: Normalize dependencies
        if FINGERPRINT_BRIDGE_AVAILABLE:
            normalized = normalize_dependency_set_ffi(resolved)
        else:
            normalized = resolved
        
        # Step 5: Generate lockfile content
        lockfile_content = _generate_lockfile_content_ffi(normalized, project_dir)
        
        # Step 6: Format output
        formatted_output = _format_resolved_output(normalized)
        
        # Step 7: Compute fingerprint
        if FINGERPRINT_BRIDGE_AVAILABLE:
            fingerprint = compute_resolution_fingerprint_ffi(normalized)
        else:
            fingerprint = ""
        
        return {
            "resolved": normalized,
            "lockfile_content": lockfile_content,
            "formatted_output": formatted_output,
            "fingerprint": fingerprint
        }
    
    except Exception as e:
        # FFI error, fall back to Python
        return resolve_dependencies_python(toml_content, project_dir)


def _parse_quarry_toml_ffi(toml_content: str) -> Dict[str, DependencySource]:
    """Parse Quarry.toml content using Pyrite bridges"""
    # Try to use full TOML parser first (preferred)
    try:
        import tomllib
        TOML_LOAD = tomllib.loads
    except ImportError:
        try:
            import tomli
            TOML_LOAD = tomli.loads
        except ImportError:
            TOML_LOAD = None
    
    if TOML_LOAD:
        try:
            data = TOML_LOAD(toml_content)
            dependencies = data.get("dependencies", {})
            result = {}
            for name, value in dependencies.items():
                # Try to parse as dependency source using Pyrite bridge
                if DEP_SOURCE_BRIDGE_AVAILABLE:
                    try:
                        source = _parse_dependency_source_ffi(name, value)
                        if source:
                            result[name] = source
                        continue
                    except:
                        pass
                
                # Fallback to Python parsing
                source = _parse_dependency_source_python(name, value)
                if source:
                    result[name] = source
            return result
        except:
            pass
    
    # Fallback to simple parser or Python
    if TOML_BRIDGE_AVAILABLE:
        try:
            # Parse dependencies section using simple parser
            deps_dict = _parse_dependencies_simple(toml_content)
            result = {}
            for name, value in deps_dict.items():
                # Try to parse as dependency source
                if DEP_SOURCE_BRIDGE_AVAILABLE:
                    try:
                        source = _parse_dependency_source_ffi(name, value)
                        if source:
                            result[name] = source
                        continue
                    except:
                        pass
                
                # Fallback to Python parsing
                source = _parse_dependency_source_python(name, value)
                if source:
                    result[name] = source
            return result
        except:
            pass
    
    # Final fallback to Python parsing
    return _parse_quarry_toml_python(toml_content)


def _parse_quarry_toml_python(toml_content: str) -> Dict[str, DependencySource]:
    """Python fallback for parsing TOML"""
    try:
        import tomllib
        TOML_LOAD = tomllib.loads
    except ImportError:
        try:
            import tomli
            TOML_LOAD = tomli.loads
        except ImportError:
            TOML_LOAD = None
    
    if TOML_LOAD:
        data = TOML_LOAD(toml_content)
        dependencies = data.get("dependencies", {})
        result = {}
        for name, value in dependencies.items():
            source = _parse_dependency_source_python(name, value)
            if source:
                result[name] = source
        return result
    else:
        return {}


def _parse_dependency_source_python(name: str, value) -> Optional[DependencySource]:
    """Python fallback for parsing dependency source"""
    if isinstance(value, str):
        return DependencySource(type="registry", version=value)
    elif isinstance(value, dict):
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
            version = value.get("version")
            checksum = value.get("checksum")
            return DependencySource(type="registry", version=version, checksum=checksum)
    return None


def _resolve_dependencies_ffi(dependencies: Dict[str, DependencySource]) -> Dict[str, DependencySource]:
    """Resolve version constraints using Pyrite bridges"""
    resolved = {}
    
    # Mock registry (MVP - will be replaced with real registry later)
    MOCK_REGISTRY = {
        "foo": ["1.0.0", "1.1.0", "2.0.0"],
        "bar": ["1.0.0", "2.0.0", "2.1.0", "3.0.0"],
        "baz": ["0.1.0", "1.0.0"],
        "qux": ["1.0.0"],
    }
    
    for name, source in dependencies.items():
        if source.type == "registry":
            # Resolve version constraint
            constraint = source.version
            if not constraint:
                raise ValueError(f"Dependency '{name}' has no version constraint")
            
            # Get available versions from mock registry
            available_versions = MOCK_REGISTRY.get(name, ["1.0.0"])
            
            # Use Pyrite version bridge if available
            if VERSION_BRIDGE_AVAILABLE:
                selected_version = _select_version(constraint, available_versions)
            else:
                # Python fallback
                selected_version = _select_version_python(constraint, available_versions)
            
            if selected_version is None:
                raise ValueError(f"Cannot resolve dependency '{name}' with constraint '{constraint}'. Available versions: {available_versions}")
            
            # Create resolved source with exact version
            resolved[name] = DependencySource(type="registry", version=selected_version)
        
        elif source.type == "git":
            # Git dependencies don't need version resolution
            resolved[name] = source
        
        elif source.type == "path":
            # Path dependencies don't need version resolution
            resolved[name] = source
    
    return resolved


def _select_version_python(constraint: str, available_versions: list) -> Optional[str]:
    """Python fallback for version selection"""
    if constraint == "*":
        if available_versions:
            return max(available_versions, key=lambda v: tuple(int(p) for p in v.split('.') if p.isdigit()))
        return None
    
    if constraint.startswith(">="):
        min_version = constraint[2:].strip()
        matching = [v for v in available_versions if _compare_versions_python(v, min_version) >= 0]
        if matching:
            return max(matching, key=lambda v: tuple(int(p) for p in v.split('.') if p.isdigit()))
        return None
    
    if constraint.startswith("~>"):
        base_version = constraint[2:].strip()
        parts = base_version.split('.')
        if len(parts) >= 2:
            major = parts[0]
            minor = parts[1]
            matching = [v for v in available_versions if v.startswith(f"{major}.{minor}")]
            if matching:
                return max(matching, key=lambda v: tuple(int(p) for p in v.split('.') if p.isdigit()))
        return None
    
    if constraint in available_versions:
        return constraint
    
    return None


def _compare_versions_python(v1: str, v2: str) -> int:
    """Python fallback for version comparison"""
    def version_tuple(v):
        parts = v.split('.')
        return tuple(int(p) for p in parts if p.isdigit())
    
    t1 = version_tuple(v1)
    t2 = version_tuple(v2)
    
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    else:
        return 0


def _generate_lockfile_content_ffi(resolved_deps: Dict[str, DependencySource], project_dir: Path = None) -> str:
    """Generate lockfile TOML content using Pyrite bridges"""
    if LOCKFILE_BRIDGE_AVAILABLE:
        try:
            # Use lockfile bridge to generate content
            # We need to write to a temp file and read it back, or modify bridge to return content
            # For now, use Python implementation
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lock', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                generate_lockfile_ffi(resolved_deps, tmp_path, project_dir)
                content = Path(tmp_path).read_text(encoding='utf-8')
                return content
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except:
            pass
    
    # Fallback to Python
    return _generate_lockfile_content_python(resolved_deps, project_dir)


def _generate_lockfile_content_python(resolved_deps: Dict[str, DependencySource], project_dir: Path = None) -> str:
    """Python fallback for generating lockfile content"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lock', delete=False) as tmp:
        tmp_path = tmp.name
    
    try:
        from ..dependency import generate_lockfile
        generate_lockfile(resolved_deps, tmp_path, project_dir)
        content = Path(tmp_path).read_text(encoding='utf-8')
        return content
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _generate_empty_lockfile() -> str:
    """Generate empty lockfile content"""
    return "[dependencies]\n"


def _format_resolved_output(resolved: Dict[str, DependencySource]) -> str:
    """Format resolved dependencies for console output"""
    lines = ["Resolving dependencies..."]
    
    if not resolved:
        lines.append("No dependencies found in Quarry.toml")
        lines.append("Generated Quarry.lock (empty)")
        return "\n".join(lines) + "\n"
    
    lines.append(f"Resolved {len(resolved)} dependencies")
    
    # Sort by name for deterministic output
    for name, source in sorted(resolved.items()):
        if source.type == "registry":
            lines.append(f"  {name} = {source.version}")
        elif source.type == "git":
            branch = source.git_branch or "main"
            lines.append(f"  {name} = {{ git = \"{source.git_url}\", branch = \"{branch}\" }}")
        elif source.type == "path":
            lines.append(f"  {name} = {{ path = \"{source.path}\" }}")
    
    lines.append("\nGenerated Quarry.lock")
    
    return "\n".join(lines) + "\n"


def resolve_dependencies_python(toml_content: str, project_dir: Path = None) -> Dict:
    """Python fallback implementation"""
    from ..dependency import parse_quarry_toml, resolve_dependencies, generate_lockfile
    
    # Parse TOML
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as tmp:
        tmp.write(toml_content)
        tmp_path = tmp.name
    
    try:
        # Parse dependencies
        deps = parse_quarry_toml(tmp_path)
        
        # Handle empty dependencies
        if not deps:
            lockfile_content = _generate_empty_lockfile()
            formatted_output = "Resolving dependencies...\nNo dependencies found in Quarry.toml\nGenerated Quarry.lock (empty)\n"
            return {
                "resolved": {},
                "lockfile_content": lockfile_content,
                "formatted_output": formatted_output,
                "fingerprint": ""
            }
        
        # Resolve dependencies
        resolved = resolve_dependencies(deps)
        
        # Generate lockfile content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lock', delete=False) as tmp_lock:
            tmp_lock_path = tmp_lock.name
        
        try:
            generate_lockfile(resolved, tmp_lock_path, project_dir)
            lockfile_content = Path(tmp_lock_path).read_text(encoding='utf-8')
        finally:
            Path(tmp_lock_path).unlink(missing_ok=True)
        
        # Format output
        formatted_output = _format_resolved_output(resolved)
        
        # Compute fingerprint
        try:
            from .dep_fingerprint_bridge import compute_resolution_fingerprint_ffi
            fingerprint = compute_resolution_fingerprint_ffi(resolved)
        except:
            fingerprint = ""
        
        return {
            "resolved": resolved,
            "lockfile_content": lockfile_content,
            "formatted_output": formatted_output,
            "fingerprint": fingerprint
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)
