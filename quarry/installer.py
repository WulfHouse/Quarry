"""Dependency installation for Quarry"""

import sys
import subprocess
from pathlib import Path
from typing import Optional

# Import path_utils bridge (FFI to Pyrite implementation)
try:
    from .bridge.path_utils_bridge import resolve_path_ffi
except ImportError:
    # Fallback to local implementation if bridge not available
    pass

# Import DependencySource (handle both relative and absolute imports)
try:
    from .dependency import DependencySource
except ImportError:
    # Fallback for when module is loaded directly
    import importlib.util
    dependency_path = Path(__file__).parent / "dependency.py"
    spec = importlib.util.spec_from_file_location("dependency", dependency_path)
    dependency_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dependency_module)
    DependencySource = dependency_module.DependencySource


def verify_package_checksum(package_path: Path, expected_checksum: str) -> bool:
    """Verify package checksum matches expected value
    
    Args:
        package_path: Path to package directory
        expected_checksum: Expected checksum (format: "sha256:..." or just hex string)
        
    Returns:
        True if checksum matches, False otherwise
        
    Raises:
        RuntimeError: If checksum computation fails
    """
    # Extract hex part if format is "sha256:..."
    if expected_checksum.startswith("sha256:"):
        expected_hex = expected_checksum[7:]
    else:
        expected_hex = expected_checksum
    
    # Compute actual checksum
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
            raise RuntimeError("Cannot compute checksum: publisher module not found")
    
    try:
        actual_hex = compute_package_checksum(package_path)
        return actual_hex.lower() == expected_hex.lower()
    except Exception as e:
        raise RuntimeError(f"Failed to compute checksum: {e}")


def install_git_dependency(name: str, git_url: str, git_branch: Optional[str] = None, deps_dir: Path = None, expected_commit: Optional[str] = None) -> Path:
    """Install a git dependency by cloning the repository
    
    Args:
        name: Dependency name
        git_url: Git repository URL
        git_branch: Optional branch/tag/commit to checkout (default: main/master)
        deps_dir: Directory to install dependencies (default: Path("deps"))
        expected_commit: Expected commit hash to verify after cloning
        
    Returns:
        Path to installed dependency directory
        
    Raises:
        RuntimeError: If git clone or checkout fails, or commit hash mismatch
        FileNotFoundError: If git command is not available
    """
    if deps_dir is None:
        deps_dir = Path("deps")
    
    deps_dir.mkdir(parents=True, exist_ok=True)
    
    # Target directory for this dependency
    target_dir = deps_dir / name
    
    # Check if already installed
    if target_dir.exists() and (target_dir / "Quarry.toml").exists():
        # If commit verification is requested, verify even if already installed
        if expected_commit:
            commit_cmd = ["git", "-C", str(target_dir), "rev-parse", "HEAD"]
            commit_result = subprocess.run(commit_cmd, capture_output=True, text=True, timeout=10)
            
            if commit_result.returncode != 0:
                # Remove corrupted installation
                import shutil
                shutil.rmtree(target_dir)
                raise RuntimeError(f"Failed to get commit hash for {git_url}: {commit_result.stderr}")
            
            actual_commit = commit_result.stdout.strip()
            if actual_commit != expected_commit:
                # Try to remove corrupted installation, but don't fail if Windows locks files
                try:
                    import shutil
                    shutil.rmtree(target_dir)
                except (PermissionError, OSError):
                    # On Windows, git files may be locked - just warn
                    pass
                raise RuntimeError(
                    f"Commit hash mismatch for {name}: expected {expected_commit}, got {actual_commit} (already installed package is corrupted)"
                )
        # Already installed, return existing path
        return target_dir
    
    # Clone repository
    try:
        # Use subprocess to call git
        clone_cmd = ["git", "clone", git_url, str(target_dir)]
        result = subprocess.run(clone_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to clone {git_url}: {result.stderr}")
        
        # Checkout specified branch/tag if provided
        if git_branch:
            checkout_cmd = ["git", "-C", str(target_dir), "checkout", git_branch]
            checkout_result = subprocess.run(checkout_cmd, capture_output=True, text=True, timeout=60)
            
            if checkout_result.returncode != 0:
                # Try to clean up on failure
                import shutil
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                raise RuntimeError(f"Failed to checkout branch '{git_branch}' in {git_url}: {checkout_result.stderr}")
        
        # Verify Quarry.toml exists
        if not (target_dir / "Quarry.toml").exists():
            import shutil
            if target_dir.exists():
                shutil.rmtree(target_dir)
            raise RuntimeError(f"Cloned repository {git_url} does not contain Quarry.toml")
        
        # Verify commit hash if expected_commit is provided
        if expected_commit:
            commit_cmd = ["git", "-C", str(target_dir), "rev-parse", "HEAD"]
            commit_result = subprocess.run(commit_cmd, capture_output=True, text=True, timeout=10)
            
            if commit_result.returncode != 0:
                import shutil
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                raise RuntimeError(f"Failed to get commit hash for {git_url}: {commit_result.stderr}")
            
            actual_commit = commit_result.stdout.strip()
            if actual_commit != expected_commit:
                import shutil
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                raise RuntimeError(
                    f"Commit hash mismatch for {name}: expected {expected_commit}, got {actual_commit}"
                )
        
        return target_dir
    
    except FileNotFoundError:
        raise FileNotFoundError("git command not found. Please install git to use git dependencies.")
    except subprocess.TimeoutExpired:
        import shutil
        if target_dir.exists():
            shutil.rmtree(target_dir)
        raise RuntimeError(f"Git clone timed out for {git_url}")
    except Exception as e:
        import shutil
        if target_dir.exists():
            shutil.rmtree(target_dir)
        raise RuntimeError(f"Failed to install git dependency {name}: {e}")


def install_path_dependency(name: str, path: str, deps_dir: Path = None) -> Path:
    """Install a path dependency by creating symlink or copy
    
    Args:
        name: Dependency name
        path: Path to dependency (relative or absolute)
        deps_dir: Directory to install dependencies (default: Path("deps"))
        
    Returns:
        Path to installed dependency directory
        
    Raises:
        FileNotFoundError: If path doesn't exist
        RuntimeError: If Quarry.toml is missing or installation fails
    """
    if deps_dir is None:
        deps_dir = Path("deps")
    
    deps_dir.mkdir(parents=True, exist_ok=True)
    
    # Resolve path (relative to current directory or absolute)
    try:
        resolve_path_ffi  # Check if imported
        resolved = resolve_path_ffi(path)
        source_path = Path(resolved)
    except NameError:
        # Python fallback
        source_path = Path(path).resolve()
    
    if not source_path.exists():
        raise FileNotFoundError(f"Path dependency '{name}' not found at {path}")
    
    # Verify Quarry.toml exists
    if not (source_path / "Quarry.toml").exists():
        raise RuntimeError(f"Path dependency '{name}' at {path} does not contain Quarry.toml")
    
    # Target directory for this dependency
    target_dir = deps_dir / name
    
    # Check if already installed
    if target_dir.exists():
        # Verify it's still valid
        if (target_dir / "Quarry.toml").exists():
            return target_dir
        # Remove invalid installation
        import shutil
        if target_dir.is_symlink():
            target_dir.unlink()
        else:
            shutil.rmtree(target_dir)
    
    # Try to create symlink (works on Unix and Windows with admin rights)
    try:
        target_dir.symlink_to(source_path, target_is_directory=True)
        return target_dir
    except (OSError, NotImplementedError):
        # Symlink failed, fall back to copying
        import shutil
        shutil.copytree(source_path, target_dir)
        return target_dir


def install_registry_dependency(name: str, version: str, cache_dir: Path = None, deps_dir: Path = None, expected_checksum: Optional[str] = None) -> Path:
    """Install a registry dependency from cache or mock registry
    
    Args:
        name: Package name
        version: Package version
        cache_dir: Registry cache directory (default: ~/.quarry/cache/packages)
        deps_dir: Directory to install dependencies (default: Path("deps"))
        expected_checksum: Expected SHA-256 checksum (format: "sha256:..." or hex string)
        
    Returns:
        Path to installed dependency directory
        
    Raises:
        RuntimeError: If package not found, installation fails, or checksum mismatch
    """
    if deps_dir is None:
        deps_dir = Path("deps")
    
    if cache_dir is None:
        from pathlib import Path as PathLib
        cache_dir = PathLib.home() / ".quarry" / "cache" / "packages"
    
    deps_dir.mkdir(parents=True, exist_ok=True)
    
    # Target directory: deps/<name>-<version>/
    target_dir = deps_dir / f"{name}-{version}"
    
    # Check if already installed
    if target_dir.exists() and (target_dir / "Quarry.toml").exists():
        # If checksum verification is requested, verify even if already installed
        if expected_checksum:
            if not verify_package_checksum(target_dir, expected_checksum):
                # Remove corrupted installation
                import shutil
                shutil.rmtree(target_dir)
                raise RuntimeError(f"Checksum mismatch for package '{name}' version '{version}' (already installed package is corrupted)")
        return target_dir
    
    # Look for package in cache first
    package_cache = cache_dir / name / version
    
    # If not in cache, check registry directory
    if not package_cache.exists() or not (package_cache / "Quarry.toml").exists():
        # Check home registry first (most common location)
        home_registry = Path.home() / ".quarry" / "registry" / name / version
        if home_registry.exists() and (home_registry / "Quarry.toml").exists():
            package_cache = home_registry
        else:
            # Check local registry (current directory)
            local_registry = Path.cwd() / ".quarry" / "registry" / name / version
            if local_registry.exists() and (local_registry / "Quarry.toml").exists():
                package_cache = local_registry
            else:
                # Try using registry module if available
                try:
                    from .registry import get_registry_path
                    registry_path = get_registry_path()
                    registry_package_path = registry_path / name / version
                    if registry_package_path.exists() and (registry_package_path / "Quarry.toml").exists():
                        package_cache = registry_package_path
                    else:
                        raise RuntimeError(f"Package '{name}' version '{version}' not found in registry cache or registry")
                except (ImportError, AttributeError):
                    # Registry module not available, but we already checked home/local
                    if not package_cache.exists() or not (package_cache / "Quarry.toml").exists():
                        raise RuntimeError(f"Package '{name}' version '{version}' not found in registry cache or registry")
    
    # Copy package to deps directory
    import shutil
    shutil.copytree(package_cache, target_dir)
    
    # Verify checksum if expected_checksum is provided
    if expected_checksum:
        if not verify_package_checksum(target_dir, expected_checksum):
            # Clean up on checksum mismatch
            if target_dir.exists():
                shutil.rmtree(target_dir)
            raise RuntimeError(f"Checksum mismatch for package '{name}' version '{version}'")
    
    return target_dir
