"""Package publishing for Quarry"""

import sys
import shutil
from pathlib import Path
from typing import Optional, List

# Import path_utils bridge (FFI to Pyrite implementation)
try:
    from .bridge.path_utils_bridge import relative_path_ffi
except ImportError:
    # Fallback to local implementation if bridge not available
    pass

# Import version bridge (FFI to Pyrite implementation)
try:
    from .bridge.version_bridge import _is_semver, _is_valid_package_name
except ImportError:
    # Fallback to local implementation if bridge not available
    pass


def package_project(project_dir: str = ".") -> Optional[Path]:
    """Package a project for publishing
    
    Creates a package directory containing:
    - Quarry.toml
    - src/ directory (all .pyrite files)
    - tests/ directory (all .pyrite files)
    - Excludes: target/, deps/, .git/, build artifacts
    
    Args:
        project_dir: Path to project directory (default: current directory)
        
    Returns:
        Path to packaged directory, or None on error
    """
    project_path = Path(project_dir).resolve()
    
    # Check for Quarry.toml
    toml_path = project_path / "Quarry.toml"
    if not toml_path.exists():
        return None
    
    # Read package name and version from Quarry.toml
    try:
        import tomllib
        with open(toml_path, 'rb') as f:
            toml_data = tomllib.load(f)
    except ImportError:
        try:
            import tomli as tomllib
            with open(toml_path, 'rb') as f:
                toml_data = tomllib.load(f)
        except ImportError:
            # Fallback: simple parsing
            return _package_project_simple(project_path)
    
    package_name = toml_data.get("package", {}).get("name", "unknown")
    package_version = toml_data.get("package", {}).get("version", "0.1.0")
    
    # Create package directory name
    package_dir_name = f"{package_name}-{package_version}"
    
    # Create temporary directory for package
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    package_dir = temp_dir / package_dir_name
    package_dir.mkdir()
    
    # Copy Quarry.toml
    shutil.copy2(toml_path, package_dir / "Quarry.toml")
    
    # Copy src/ directory if it exists
    src_dir = project_path / "src"
    if src_dir.exists() and src_dir.is_dir():
        shutil.copytree(src_dir, package_dir / "src", ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
    
    # Copy tests/ directory if it exists
    tests_dir = project_path / "tests"
    if tests_dir.exists() and tests_dir.is_dir():
        shutil.copytree(tests_dir, package_dir / "tests", ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
    
    # Copy README.md if it exists
    readme_path = project_path / "README.md"
    if readme_path.exists():
        shutil.copy2(readme_path, package_dir / "README.md")
    
    # Exclude: target/, deps/, .git/, .pyrite/, build artifacts
    # (Already handled by only copying src/ and tests/)
    
    return package_dir


def _package_project_simple(project_path: Path) -> Optional[Path]:
    """Simple packaging without TOML parser (fallback)"""
    # For MVP: create basic package structure
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    package_dir = temp_dir / "package"
    package_dir.mkdir()
    
    # Copy Quarry.toml
    toml_path = project_path / "Quarry.toml"
    if toml_path.exists():
        shutil.copy2(toml_path, package_dir / "Quarry.toml")
    
    # Copy src/ if exists
    src_dir = project_path / "src"
    if src_dir.exists():
        shutil.copytree(src_dir, package_dir / "src", ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
    
    return package_dir


def get_source_files(project_dir: Path) -> List[Path]:
    """Get all source files to include in package
    
    Args:
        project_dir: Path to project directory
        
    Returns:
        List of source file paths
    """
    source_files = []
    
    # Find all .pyrite files in src/
    src_dir = project_dir / "src"
    if src_dir.exists():
        for pyrite_file in src_dir.rglob("*.pyrite"):
            source_files.append(pyrite_file)
    
    # Find all .pyrite files in tests/
    tests_dir = project_dir / "tests"
    if tests_dir.exists():
        for pyrite_file in tests_dir.rglob("*.pyrite"):
            source_files.append(pyrite_file)
    
    return source_files


def validate_for_publish(project_dir: str = ".") -> tuple[bool, List[str]]:
    """Validate project for publishing
    
    Checks:
    - Quarry.toml has required fields: name, version, license
    - Version is semver format
    - License is declared
    
    Args:
        project_dir: Path to project directory (default: current directory)
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    project_path = Path(project_dir).resolve()
    errors = []
    
    # Check for Quarry.toml
    toml_path = project_path / "Quarry.toml"
    if not toml_path.exists():
        return (False, ["Quarry.toml not found"])
    
    # Read Quarry.toml
    try:
        import tomllib
        with open(toml_path, 'rb') as f:
            toml_data = tomllib.load(f)
    except ImportError:
        try:
            import tomli as tomllib
            with open(toml_path, 'rb') as f:
                toml_data = tomllib.load(f)
        except ImportError:
            # Fallback: simple validation
            return _validate_for_publish_simple(project_path)
    
    package_info = toml_data.get("package", {})
    
    # Check required fields
    if "name" not in package_info:
        errors.append("Package name is required in Quarry.toml")
    else:
        package_name = package_info["name"]
        # Validate package name format
        if not _is_valid_package_name(package_name):
            errors.append(f"Package name must be alphanumeric with hyphens/underscores (cannot start/end with - or _), got: {package_name}")
    
    if "version" not in package_info:
        errors.append("Package version is required in Quarry.toml")
    else:
        version = package_info["version"]
        # Validate semver format (simple check: x.y.z)
        if not _is_semver(version):
            errors.append(f"Version must be semantic version (e.g., 1.0.0), got: {version}")
    
    if "license" not in package_info:
        errors.append("License must be declared in Quarry.toml")
    
    return (len(errors) == 0, errors)


# _is_semver and _is_valid_package_name are imported from version_bridge above
# If import fails, define fallback implementations here
try:
    _is_semver  # Check if imported
except NameError:
    def _is_semver(version: str) -> bool:
        """Check if version string is semantic version format
        
        Args:
            version: Version string
            
        Returns:
            True if valid semver format
        """
        # Simple check: should be in format x.y.z (or x.y.z-pre)
        import re
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$'
        return bool(re.match(pattern, version))

try:
    _is_valid_package_name  # Check if imported
except NameError:
    def _is_valid_package_name(name: str) -> bool:
        """Check if package name is valid
        
        Args:
            name: Package name string
            
        Returns:
            True if valid package name format
        """
        if not name or len(name) == 0:
            return False
        
        # Cannot start or end with hyphen or underscore
        if name[0] == '-' or name[0] == '_' or name[-1] == '-' or name[-1] == '_':
            return False
        
        # All characters must be alphanumeric, hyphen, or underscore
        import re
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, name))


def _validate_for_publish_simple(project_path: Path) -> tuple[bool, List[str]]:
    """Simple validation without TOML parser (fallback)"""
    errors = []
    
    # Check Quarry.toml exists
    toml_path = project_path / "Quarry.toml"
    if not toml_path.exists():
        errors.append("Quarry.toml not found")
        return (False, errors)
    
    # Simple text-based checks
    toml_text = toml_path.read_text(encoding='utf-8')
    
    if "name" not in toml_text:
        errors.append("Package name is required")
    
    if "version" not in toml_text:
        errors.append("Package version is required")
    
    if "license" not in toml_text:
        errors.append("License must be declared")
    
    return (len(errors) == 0, errors)


def compute_package_checksum(package_path: Path) -> str:
    """Compute SHA-256 checksum for package
    
    Args:
        package_path: Path to package directory or tarball
        
    Returns:
        Hex string of SHA-256 hash
    """
    import hashlib
    
    if package_path.is_file():
        # Hash file directly
        sha256 = hashlib.sha256()
        with open(package_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    else:
        # Hash directory contents (sorted by path)
        sha256 = hashlib.sha256()
        
        # Collect all files
        files = []
        for item in package_path.rglob("*"):
            if item.is_file():
                files.append(item)
        
        # Sort by path for deterministic hashing
        files.sort(key=lambda p: str(p))
        
        # Hash each file
        for file_path in files:
            # Include relative path in hash
            try:
                relative_path_ffi  # Check if imported
                rel_path_str = relative_path_ffi(str(file_path), str(package_path))
                if rel_path_str:
                    rel_path = rel_path_str
                else:
                    # Fallback if no relative path
                    rel_path = file_path.relative_to(package_path)
            except NameError:
                # Python fallback
                rel_path = file_path.relative_to(package_path)
            sha256.update(str(rel_path).encode('utf-8'))
            
            # Hash file contents
            with open(file_path, 'rb') as f:
                sha256.update(f.read())
        
        return sha256.hexdigest()
