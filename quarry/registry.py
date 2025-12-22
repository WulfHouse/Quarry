"""Local development registry for Quarry packages"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

# Registry path override for testing
_REGISTRY_PATH_OVERRIDE: Optional[Path] = None


def set_registry_path(path: Optional[Path]):
    """Set registry path override (for testing)
    
    Args:
        path: Path to use as registry root, or None to clear override
    """
    global _REGISTRY_PATH_OVERRIDE
    _REGISTRY_PATH_OVERRIDE = path


def get_registry_path() -> Path:
    """Get the registry root path
    
    Returns:
        Path to registry root (~/.quarry/registry/ or ./.quarry/registry/)
    """
    # Check for override (for testing)
    if _REGISTRY_PATH_OVERRIDE is not None:
        return _REGISTRY_PATH_OVERRIDE
    
    # For MVP: prefer local registry in current directory
    # In production: would use ~/.quarry/registry/
    local_registry = Path.cwd() / ".quarry" / "registry"
    
    # If local registry exists, use it; otherwise use home directory
    if local_registry.exists():
        return local_registry
    
    # Use home directory as fallback
    home_registry = Path.home() / ".quarry" / "registry"
    return home_registry


def ensure_registry() -> Path:
    """Ensure registry directory exists, create if missing
    
    Returns:
        Path to registry root
    """
    registry_path = get_registry_path()
    registry_path.mkdir(parents=True, exist_ok=True)
    return registry_path


def list_packages() -> List[str]:
    """List all package names in registry
    
    Returns:
        List of package names
    """
    registry_path = get_registry_path()
    
    packages = []
    if registry_path.exists():
        for item in registry_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                packages.append(item.name)
    
    return sorted(packages)


def get_package_versions(name: str) -> List[str]:
    """Get all versions for a package
    
    Args:
        name: Package name
        
    Returns:
        List of version strings
    """
    registry_path = ensure_registry()
    package_dir = registry_path / name
    
    versions = []
    if package_dir.exists() and package_dir.is_dir():
        for item in package_dir.iterdir():
            if item.is_dir():
                versions.append(item.name)
    
    return sorted(versions)


def get_package_metadata(name: str, version: str) -> Optional[Dict[str, Any]]:
    """Get package metadata
    
    Args:
        name: Package name
        version: Package version
        
    Returns:
        Metadata dictionary, or None if not found
    """
    registry_path = ensure_registry()
    metadata_path = registry_path / name / version / "metadata.json"
    
    if not metadata_path.exists():
        return None
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def get_package_path(name: str, version: str) -> Optional[Path]:
    """Get path to package directory or tarball
    
    Args:
        name: Package name
        version: Package version
        
    Returns:
        Path to package, or None if not found
    """
    registry_path = ensure_registry()
    package_path = registry_path / name / version
    
    # Check for tarball first
    tarball = package_path.with_suffix(".tar.gz")
    if tarball.exists():
        return tarball
    
    # Check for directory
    if package_path.exists() and package_path.is_dir():
        return package_path
    
    return None


def store_package_metadata(name: str, version: str, metadata: Dict[str, Any]) -> bool:
    """Store package metadata in registry
    
    Args:
        name: Package name
        version: Package version
        metadata: Metadata dictionary
        
    Returns:
        True if successful, False otherwise
    """
    registry_path = ensure_registry()
    version_dir = registry_path / name / version
    version_dir.mkdir(parents=True, exist_ok=True)
    
    metadata_path = version_dir / "metadata.json"
    
    try:
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        return True
    except Exception:
        return False


def remove_package(name: str, version: str) -> bool:
    """Remove package from registry
    
    Args:
        name: Package name
        version: Package version
        
    Returns:
        True if successful, False otherwise
    """
    registry_path = ensure_registry()
    package_path = registry_path / name / version
    
    if not package_path.exists():
        return False
    
    try:
        import shutil
        shutil.rmtree(package_path)
        # Update index after removal
        remove_from_index(name, version)
        return True
    except Exception:
        return False


def read_index() -> Dict[str, List[str]]:
    """Read registry index
    
    Returns:
        Dictionary mapping package names to lists of versions
    """
    registry_path = ensure_registry()
    index_path = registry_path / "index.json"
    
    if not index_path.exists():
        return {}
    
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("packages", {})
    except Exception:
        return {}


def update_index() -> bool:
    """Rebuild registry index from registry contents
    
    Returns:
        True if successful, False otherwise
    """
    registry_path = ensure_registry()
    index_path = registry_path / "index.json"
    
    # Scan registry directory for packages
    packages = {}
    
    if registry_path.exists():
        for package_dir in registry_path.iterdir():
            if package_dir.is_dir() and not package_dir.name.startswith('.'):
                package_name = package_dir.name
                versions = []
                
                for version_dir in package_dir.iterdir():
                    if version_dir.is_dir():
                        versions.append(version_dir.name)
                
                if versions:
                    packages[package_name] = sorted(versions)
    
    # Write index
    index_data = {"packages": packages}
    
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        return True
    except Exception:
        return False


def add_to_index(name: str, version: str) -> bool:
    """Add package to index
    
    Args:
        name: Package name
        version: Package version
        
    Returns:
        True if successful, False otherwise
    """
    index = read_index()
    
    if name not in index:
        index[name] = []
    
    if version not in index[name]:
        index[name].append(version)
        index[name] = sorted(index[name])
    
    # Write updated index
    registry_path = ensure_registry()
    index_path = registry_path / "index.json"
    index_data = {"packages": index}
    
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        return True
    except Exception:
        return False


def remove_from_index(name: str, version: str) -> bool:
    """Remove package from index
    
    Args:
        name: Package name
        version: Package version
        
    Returns:
        True if successful, False otherwise
    """
    index = read_index()
    
    if name in index and version in index[name]:
        index[name].remove(version)
        
        # Remove package entry if no versions left
        if not index[name]:
            del index[name]
    
    # Write updated index
    registry_path = ensure_registry()
    index_path = registry_path / "index.json"
    index_data = {"packages": index}
    
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2)
        return True
    except Exception:
        return False
