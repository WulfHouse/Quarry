"""Workspace support for multi-package projects"""

import sys
from pathlib import Path
from typing import List, Optional, Dict

# Import path_utils bridge (FFI to Pyrite implementation)
try:
    from .bridge.path_utils_bridge import resolve_path_ffi, join_paths_ffi
except ImportError:
    # Fallback to local implementation if bridge not available
    pass

# Try to import TOML parser
try:
    import tomllib  # Python 3.11+
    TOML_LOAD = tomllib.loads
except ImportError:
    try:
        import tomli
        TOML_LOAD = tomli.loads
    except ImportError:
        TOML_LOAD = None

# Import TOML bridge (FFI to Pyrite implementation)
try:
    from .bridge.toml_bridge import _parse_workspace_simple
except ImportError:
    # Fallback to local implementation if bridge not available
    pass


def parse_workspace_toml(workspace_path: str = "Workspace.toml") -> List[str]:
    """Parse Workspace.toml and extract workspace members
    
    Args:
        workspace_path: Path to Workspace.toml file (default: "Workspace.toml")
        
    Returns:
        List of workspace member package paths
        Example: ["pkg1", "pkg2", "pkg3"]
    """
    workspace_file = Path(workspace_path)
    
    if not workspace_file.exists():
        return []
    
    try:
        if TOML_LOAD:
            workspace_text = workspace_file.read_text(encoding='utf-8')
            data = TOML_LOAD(workspace_text)
            workspace = data.get("workspace", {})
            members = workspace.get("members", [])
            return members if isinstance(members, list) else []
        else:
            # Fallback: simple parsing
            return _parse_workspace_simple(workspace_file.read_text(encoding='utf-8'))
    
    except Exception as e:
        print(f"Warning: Failed to parse {workspace_path}: {e}", file=sys.stderr)
        return []


# _parse_workspace_simple is imported from toml_bridge above
# If import fails, define fallback implementation here
try:
    _parse_workspace_simple  # Check if imported
except NameError:
    def _parse_workspace_simple(workspace_text: str) -> List[str]:
        """Simple parser for Workspace.toml (fallback)"""
        members = []
        in_workspace = False
        in_members = False
        
        for line in workspace_text.split('\n'):
            line = line.strip()
            
            if line == "[workspace]":
                in_workspace = True
                continue
            
            if in_workspace and line.startswith("members"):
                in_members = True
                # Parse members = ["pkg1", "pkg2"]
                if '=' in line:
                    value_part = line.split('=', 1)[1].strip()
                    # Simple parsing for array
                    if '[' in value_part and ']' in value_part:
                        # Extract quoted strings
                        import re
                        matches = re.findall(r'"([^"]+)"', value_part)
                        members.extend(matches)
                continue
            
            if line.startswith('['):
                break
        
        return members


def find_workspace_root(start_path: Path = None) -> Optional[Path]:
    """Find workspace root by looking for Workspace.toml
    
    Args:
        start_path: Path to start searching from (default: current directory)
        
    Returns:
        Path to workspace root, or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()
    
    # Try to use FFI bridge if available
    try:
        resolve_path_ffi  # Check if imported
        current = Path(resolve_path_ffi(str(start_path)))
    except NameError:
        # Python fallback
        current = Path(start_path).resolve()
    
    # Walk up directory tree looking for Workspace.toml
    while current != current.parent:
        workspace_file = current / "Workspace.toml"
        if workspace_file.exists():
            return current
        current = current.parent
    
    return None


def get_workspace_packages(workspace_root: Path) -> List[Path]:
    """Get all package paths in workspace
    
    Args:
        workspace_root: Path to workspace root
        
    Returns:
        List of package directory paths
    """
    members = parse_workspace_toml(str(workspace_root / "Workspace.toml"))
    
    packages = []
    for member in members:
        # Resolve member path relative to workspace root
        try:
            join_paths_ffi  # Check if imported
            joined = join_paths_ffi(str(workspace_root), member)
            member_path = Path(resolve_path_ffi(joined, str(workspace_root)))
        except NameError:
            # Python fallback
            member_path = (workspace_root / member).resolve()
        if member_path.exists() and (member_path / "Quarry.toml").exists():
            packages.append(member_path)
    
    return packages
