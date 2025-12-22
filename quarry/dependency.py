"""Dependency resolution and lockfile management for Quarry"""

import sys
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

# Try to import TOML parser (prefer tomllib for Python 3.11+, fallback to tomli)
try:
    import tomllib  # Python 3.11+
    TOML_LOAD = tomllib.loads
except ImportError:
    try:
        import tomli
        TOML_LOAD = tomli.loads
    except ImportError:
        # Fallback: basic TOML parsing for dependencies section only
        TOML_LOAD = None

# Import TOML bridge (FFI to Pyrite implementation)
try:
    from .bridge.toml_bridge import _parse_dependencies_simple
except ImportError:
    # Fallback to local implementation if bridge not available
    pass

# Import version bridge (FFI to Pyrite implementation)
try:
    from .bridge.version_bridge import _compare_versions, _latest_version, _select_version
except ImportError:
    # Fallback to local implementation if bridge not available
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two version strings
        
        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
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


# Import dep_source bridge (FFI to Pyrite implementation)
try:
    from .bridge.dep_source_bridge import _parse_dependency_source_ffi
except ImportError:
    # Fallback to local implementation if bridge not available
    pass

# Import path_utils bridge (FFI to Pyrite implementation)
try:
    from .bridge.path_utils_bridge import is_absolute_ffi, resolve_path_ffi
except ImportError:
    # Fallback to local implementation if bridge not available
    pass

# Import lockfile bridge (FFI to Pyrite implementation)
try:
    from .bridge.lockfile_bridge import generate_lockfile_ffi, read_lockfile_ffi
except ImportError:
    # Fallback to local implementation if bridge not available
    pass


def _parse_dependency_source(name: str, value) -> Optional[DependencySource]:
    """Parse a single dependency value into DependencySource
    
    Args:
        name: Dependency name
        value: TOML value (string or dict)
        
    Returns:
        DependencySource or None if invalid
    """
    # Try to use FFI bridge if available
    try:
        _parse_dependency_source_ffi  # Check if imported
        return _parse_dependency_source_ffi(name, value)
    except NameError:
        # Python fallback (original implementation)
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


@dataclass
class DependencySource:
    """Represents a dependency source (registry, git, or path)"""
    type: str  # "registry", "git", "path"
    version: Optional[str] = None  # For registry: version constraint
    git_url: Optional[str] = None  # For git: repository URL
    git_branch: Optional[str] = None  # For git: branch/tag/commit
    path: Optional[str] = None  # For path: relative or absolute path
    checksum: Optional[str] = None  # For registry: SHA-256 checksum (format: "sha256:...")
    commit: Optional[str] = None  # For git: commit hash
    hash: Optional[str] = None  # For path: directory hash (format: "sha256:...")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        result = {"type": self.type}
        if self.version:
            result["version"] = self.version
        if self.git_url:
            result["git_url"] = self.git_url
        if self.git_branch:
            result["git_branch"] = self.git_branch
        if self.path:
            result["path"] = self.path
        if self.checksum:
            result["checksum"] = self.checksum
        if self.commit:
            result["commit"] = self.commit
        if self.hash:
            result["hash"] = self.hash
        return result


def parse_quarry_toml(toml_path: str = "Quarry.toml") -> Dict[str, DependencySource]:
    """Parse Quarry.toml and extract dependencies with sources
    
    Args:
        toml_path: Path to Quarry.toml file (default: "Quarry.toml")
        
    Returns:
        Dictionary mapping dependency name to DependencySource
        Example:
        - {"foo": DependencySource(type="registry", version="1.0.0")}
        - {"bar": DependencySource(type="git", git_url="...", git_branch="main")}
        - {"baz": DependencySource(type="path", path="../baz")}
    """
    toml_file = Path(toml_path)
    
    if not toml_file.exists():
        return {}
    
    try:
        # Read TOML file
        toml_text = toml_file.read_text(encoding='utf-8')
        
        # Parse using available TOML library
        if TOML_LOAD:
            data = TOML_LOAD(toml_text)
            dependencies = data.get("dependencies", {})
            result = {}
            for name, value in dependencies.items():
                source = _parse_dependency_source(name, value)
                if source:
                    result[name] = source
            return result
        else:
            # Fallback: basic parsing for [dependencies] section
            return _parse_dependencies_simple_with_sources(toml_text)
    
    except Exception as e:
        # Return empty dict on parse error (caller can handle)
        print(f"Warning: Failed to parse {toml_path}: {e}", file=sys.stderr)
        return {}


def _parse_dependency_source(name: str, value) -> Optional[DependencySource]:
    """Parse a single dependency value into DependencySource
    
    Args:
        name: Dependency name
        value: TOML value (string or dict)
        
    Returns:
        DependencySource or None if invalid
    """
    # Try to use FFI bridge if available
    try:
        _parse_dependency_source_ffi  # Check if imported
        return _parse_dependency_source_ffi(name, value)
    except NameError:
        # Python fallback (original implementation)
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


# _parse_dependencies_simple is imported from toml_bridge above
# If import fails, define fallback implementation here
try:
    _parse_dependencies_simple  # Check if imported
except NameError:
    def _parse_dependencies_simple(toml_text: str) -> Dict[str, str]:
        """Simple TOML parser for [dependencies] section only (fallback)"""
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


def _parse_dependencies_simple_with_sources(toml_text: str) -> Dict[str, DependencySource]:
    """Simple TOML parser for [dependencies] section with sources (fallback)"""
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
        
        # Parse dependency line: name = "version" or name = { ... }
        if in_dependencies and '=' in line:
            parts = line.split('=', 1)
            if len(parts) == 2:
                name = parts[0].strip()
                value = parts[1].strip()
                
                # Try to parse as simple string version
                if value.startswith('"') and value.endswith('"'):
                    version = value[1:-1]
                    dependencies[name] = DependencySource(type="registry", version=version)
                elif value.startswith("'") and value.endswith("'"):
                    version = value[1:-1]
                    dependencies[name] = DependencySource(type="registry", version=version)
                # For dict syntax, we'd need more complex parsing - skip for MVP fallback
    
    return dependencies


# Mock registry for MVP (will be replaced with real registry later)
MOCK_REGISTRY = {
    "foo": ["1.0.0", "1.1.0", "2.0.0"],
    "bar": ["1.0.0", "2.0.0", "2.1.0", "3.0.0"],
    "baz": ["0.1.0", "1.0.0"],
    "qux": ["1.0.0"],
}


def resolve_dependencies(dependencies: Dict[str, DependencySource]) -> Dict[str, DependencySource]:
    """Resolve version constraints to specific versions
    
    Args:
        dependencies: Dictionary mapping dependency name to DependencySource
        Example: {"foo": DependencySource(type="registry", version=">=1.0.0")}
        
    Returns:
        Dictionary mapping dependency name to resolved DependencySource
        Example: {"foo": DependencySource(type="registry", version="2.0.0")}
        
    Raises:
        ValueError: If version constraint cannot be satisfied or conflict detected
    """
    resolved = {}
    
    for name, source in dependencies.items():
        if source.type == "registry":
            # Resolve version constraint
            constraint = source.version
            if not constraint:
                raise ValueError(f"Dependency '{name}' has no version constraint")
            
            # Get available versions from mock registry
            available_versions = MOCK_REGISTRY.get(name, ["1.0.0"])  # Default to 1.0.0 if not in registry
            
            # Parse constraint and select version
            selected_version = _select_version(constraint, available_versions)
            
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


# _compare_versions, _latest_version, and _select_version are now imported from version_bridge (or defined above as fallback)


def _compute_registry_checksum(name: str, version: str, project_dir: Path) -> Optional[str]:
    """Compute checksum for registry package
    
    Args:
        name: Package name
        version: Package version
        project_dir: Project directory (for resolving cache paths)
        
    Returns:
        Hex string of SHA-256 hash, or None if package not found
    """
    # Try to import compute_package_checksum from publisher
    try:
        from .publisher import compute_package_checksum
    except ImportError:
        # Fallback: try absolute import
        import importlib.util
        publisher_path = Path(__file__).parent / "publisher.py"
        if publisher_path.exists():
            spec = importlib.util.spec_from_file_location("publisher", publisher_path)
            publisher_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(publisher_module)
            compute_package_checksum = publisher_module.compute_package_checksum
        else:
            return None
    
    # Look for package in cache/registry
    cache_dir = Path.home() / ".quarry" / "cache" / "packages"
    package_path = cache_dir / name / version
    
    # Also check local registry
    registry_dir = Path.home() / ".quarry" / "registry"
    if not package_path.exists():
        package_path = registry_dir / name / version
    
    if package_path.exists() and package_path.is_dir():
        try:
            return compute_package_checksum(package_path)
        except Exception:
            return None
    
    return None


def _get_git_commit_hash(git_url: str, git_branch: Optional[str], project_dir: Path) -> Optional[str]:
    """Get commit hash for git dependency
    
    Args:
        git_url: Git repository URL
        git_branch: Optional branch/tag/commit
        project_dir: Project directory (for resolving deps directory)
        
    Returns:
        Commit hash string, or None if not available
    """
    import subprocess
    
    # Check if dependency is already installed in deps/
    deps_dir = project_dir / "deps"
    # Try to find the dependency directory (name might be inferred from URL)
    # For MVP, we'll try to get commit from a temporary clone or existing clone
    
    # If we have an existing clone, get commit from there
    # Otherwise, we can't get commit without cloning (which is expensive)
    # For MVP, return None if not already cloned
    # In a real implementation, this would be called after installation
    
    return None  # MVP: commit hash will be set during install


def _compute_path_hash(path: str, project_dir: Path) -> Optional[str]:
    """Compute hash for path dependency
    
    Args:
        path: Path to dependency (relative or absolute)
        project_dir: Project directory (for resolving relative paths)
        
    Returns:
        Hex string of SHA-256 hash, or None if path doesn't exist
    """
    # Resolve path
    try:
        is_absolute_ffi  # Check if imported
        if is_absolute_ffi(path):
            dep_path = Path(path)
        else:
            resolved = resolve_path_ffi(path, str(project_dir))
            dep_path = Path(resolved)
    except NameError:
        # Python fallback
        if Path(path).is_absolute():
            dep_path = Path(path)
        else:
            dep_path = (project_dir / path).resolve()
    
    if not dep_path.exists() or not dep_path.is_dir():
        return None
    
    # Use same checksum computation as registry packages
    try:
        from .publisher import compute_package_checksum
    except ImportError:
        # Fallback: try absolute import
        import importlib.util
        publisher_path = Path(__file__).parent / "publisher.py"
        if publisher_path.exists():
            spec = importlib.util.spec_from_file_location("publisher", publisher_path)
            publisher_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(publisher_module)
            compute_package_checksum = publisher_module.compute_package_checksum
        else:
            # Fallback: simple hash computation
            import hashlib
            sha256 = hashlib.sha256()
            for file_path in sorted(dep_path.rglob("*")):
                if file_path.is_file():
                    rel_path = file_path.relative_to(dep_path)
                    sha256.update(str(rel_path).encode('utf-8'))
                    sha256.update(file_path.read_bytes())
            return sha256.hexdigest()
    
    try:
        return compute_package_checksum(dep_path)
    except Exception:
        return None


def generate_lockfile(resolved_deps: Dict[str, DependencySource], lockfile_path: str = "Quarry.lock", project_dir: Path = None) -> None:
    """Generate Quarry.lock file from resolved dependencies
    
    Args:
        resolved_deps: Dictionary mapping dependency name to resolved DependencySource
        lockfile_path: Path to Quarry.lock file (default: "Quarry.lock")
        project_dir: Project directory (for resolving relative paths, default: current directory)
    """
    # Try to normalize dependencies before processing
    try:
        from .bridge.dep_fingerprint_bridge import normalize_dependency_set_ffi
        normalized_deps = normalize_dependency_set_ffi(resolved_deps)
    except (NameError, ImportError):
        # Fallback: use as-is
        normalized_deps = resolved_deps
    
    # Try to use FFI bridge if available
    try:
        generate_lockfile_ffi  # Check if imported
        return generate_lockfile_ffi(normalized_deps, lockfile_path, project_dir)
    except NameError:
        # Python fallback (original implementation)
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
                # For registry packages, checksum should be computed during resolution
                # or retrieved from registry metadata. For MVP, we'll compute it if
                # the package is available in cache/registry.
                checksum = _compute_registry_checksum(name, source.version, project_dir)
                if checksum:
                    new_source.checksum = f"sha256:{checksum}"
            
            elif source.type == "git" and not source.commit:
                # Get commit hash from git repository
                commit = _get_git_commit_hash(source.git_url, source.git_branch, project_dir)
                if commit:
                    new_source.commit = commit
            
            elif source.type == "path" and not source.hash:
                # Compute hash of path dependency directory
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


def read_lockfile(lockfile_path: str = "Quarry.lock") -> Dict[str, DependencySource]:
    """Read Quarry.lock file and extract locked dependencies
    
    Args:
        lockfile_path: Path to Quarry.lock file (default: "Quarry.lock")
        
    Returns:
        Dictionary mapping dependency name to DependencySource
        Example: {"foo": DependencySource(type="registry", version="1.0.0", checksum="sha256:...")}
    """
    # Try to use FFI bridge if available
    try:
        read_lockfile_ffi  # Check if imported
        return read_lockfile_ffi(lockfile_path)
    except NameError:
        # Python fallback (original implementation)
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
