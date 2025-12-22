"""Build graph construction for multi-package projects"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass

# Import dependency resolution
try:
    from .dependency import read_lockfile, parse_quarry_toml, resolve_dependencies
except ImportError:
    # Fallback if relative import fails
    import importlib.util
    dependency_path = Path(__file__).parent / "dependency.py"
    spec = importlib.util.spec_from_file_location("dependency", dependency_path)
    dependency_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dependency_module)
    read_lockfile = dependency_module.read_lockfile
    parse_quarry_toml = dependency_module.parse_quarry_toml
    resolve_dependencies = dependency_module.resolve_dependencies

# Import build graph bridge (FFI to Pyrite implementation)
try:
    from .bridge.build_graph_bridge import _has_cycle_ffi, _topological_sort_ffi
except ImportError:
    # Fallback to local implementation if bridge not available
    pass


@dataclass
class PackageNode:
    """Represents a package in the build graph"""
    name: str
    version: str
    path: Path  # Path to package directory
    dependencies: List[str]  # List of dependency package names


class BuildGraph:
    """Represents dependency graph for building packages"""
    
    def __init__(self):
        self.nodes: Dict[str, PackageNode] = {}  # package name -> PackageNode
        self.edges: Dict[str, List[str]] = {}  # package name -> [dependencies]
    
    def add_package(self, name: str, version: str, path: Path, dependencies: List[str]):
        """Add a package to the graph"""
        node = PackageNode(name=name, version=version, path=path, dependencies=dependencies)
        self.nodes[name] = node
        self.edges[name] = dependencies
    
    def get_dependencies(self, package: str) -> List[str]:
        """Get direct dependencies of a package"""
        return self.edges.get(package, [])
    
    def has_cycle(self) -> bool:
        """Check if graph has cycles"""
        # Try to use FFI bridge if available
        try:
            _has_cycle_ffi  # Check if imported
            return _has_cycle_ffi(self.edges)
        except NameError:
            # Python fallback (original implementation)
            visited = set()
            rec_stack = set()
            
            def has_cycle_helper(node: str) -> bool:
                visited.add(node)
                rec_stack.add(node)
                
                for dep in self.get_dependencies(node):
                    if dep not in visited:
                        if has_cycle_helper(dep):
                            return True
                    elif dep in rec_stack:
                        return True
                
                rec_stack.remove(node)
                return False
            
            for node in self.nodes:
                if node not in visited:
                    if has_cycle_helper(node):
                        return True
            
            return False
    
    def topological_sort(self) -> List[str]:
        """Return packages in build order (dependencies first)
        
        Uses Kahn's algorithm for topological sorting.
        
        Returns:
            List of package names in build order (dependencies first)
            
        Raises:
            ValueError: If graph contains cycles
        """
        # Try to use FFI bridge if available
        try:
            _topological_sort_ffi  # Check if imported
            return _topological_sort_ffi(self.edges)
        except NameError:
            # Python fallback (original implementation)
            if self.has_cycle():
                raise ValueError("Build graph contains circular dependencies")
            
            # Build in-degree map
            # In-degree = number of dependencies a package has (unbuilt dependencies)
            # If A depends on [B, C], then A has in-degree 2
            # Packages with in-degree 0 have no dependencies and can be built first
            in_degree = {}
            for name in self.nodes:
                # In-degree = number of dependencies this package has
                in_degree[name] = len(self.get_dependencies(name))
            
            # Start with packages that have no dependencies (in-degree 0)
            queue = [name for name, degree in in_degree.items() if degree == 0]
            result = []
            
            while queue:
                current = queue.pop(0)
                result.append(current)
                
                # For packages that depend on current, reduce their in-degree
                # (current is now "built", so one less dependency for them)
                for name, deps in self.edges.items():
                    if current in deps:
                        # name depends on current, so reduce name's in-degree
                        in_degree[name] -= 1
                        if in_degree[name] == 0:
                            queue.append(name)
            
            # Check if all nodes were processed
            if len(result) != len(self.nodes):
                # Cycle detected (shouldn't happen if has_cycle() worked)
                raise ValueError("Topological sort failed: cycle detected")
            
            return result


def construct_build_graph(project_dir: str = ".") -> BuildGraph:
    """Construct build graph from Quarry.lock or resolve dependencies
    
    Args:
        project_dir: Path to project directory (default: current directory)
        
    Returns:
        BuildGraph instance with all packages and dependencies
    """
    project_path = Path(project_dir)
    graph = BuildGraph()
    
    # Check for workspace
    try:
        import importlib.util
        workspace_path = Path(__file__).parent / "workspace.py"
        spec = importlib.util.spec_from_file_location("workspace", workspace_path)
        workspace_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(workspace_module)
        
        workspace_root = workspace_module.find_workspace_root(project_path)
        if workspace_root:
            # Add workspace packages
            workspace_packages = workspace_module.get_workspace_packages(workspace_root)
            for pkg_path in workspace_packages:
                pkg_toml = pkg_path / "Quarry.toml"
                if pkg_toml.exists():
                    pkg_deps = parse_quarry_toml(str(pkg_toml))
                    pkg_name = pkg_path.name
                    graph.add_package(pkg_name, "0.1.0", pkg_path, list(pkg_deps.keys()))
    except Exception:
        # Workspace support failed, continue with single package
        pass
    
    # Read or resolve dependencies for main project
    lockfile_path = project_path / "Quarry.lock"
    toml_path = project_path / "Quarry.toml"
    
    if not toml_path.exists():
        return graph  # Empty graph if no Quarry.toml
    
    # Try to read lockfile, otherwise resolve
    if lockfile_path.exists():
        resolved_deps = read_lockfile(str(lockfile_path))
    else:
        # Auto-resolve if lockfile missing
        deps = parse_quarry_toml(str(toml_path))
        try:
            resolved_deps = resolve_dependencies(deps)
        except Exception as e:
            print(f"Warning: Failed to resolve dependencies: {e}", file=sys.stderr)
            resolved_deps = {}
    
    # Add main package
    toml_data = parse_quarry_toml(str(toml_path))
    package_name = "main"  # Default, could be read from [package] section
    graph.add_package(package_name, "0.1.0", project_path, list(resolved_deps.keys()))
    
    # For MVP: Assume all dependencies are local packages
    # Look for dependencies in deps/ directory or sibling directories
    deps_dir = project_path / "deps"
    parent_dir = project_path.parent
    
    for dep_name, dep_source in resolved_deps.items():
        # Try to find dependency package
        dep_path = None
        
        # Check deps/ directory
        if deps_dir.exists():
            potential_path = deps_dir / dep_name
            if potential_path.exists() and (potential_path / "Quarry.toml").exists():
                dep_path = potential_path
        
        # Check sibling directories
        if not dep_path:
            potential_path = parent_dir / dep_name
            if potential_path.exists() and (potential_path / "Quarry.toml").exists():
                dep_path = potential_path
        
        # If found, recursively add its dependencies
        if dep_path:
            dep_toml = dep_path / "Quarry.toml"
            if dep_toml.exists():
                dep_deps = parse_quarry_toml(str(dep_toml))
                dep_resolved = {}
                try:
                    dep_resolved = resolve_dependencies(dep_deps)
                except Exception:
                    pass
                
                # Get version from source
                version = dep_source.version if dep_source.type == "registry" else "0.0.0"
                graph.add_package(dep_name, version, dep_path, list(dep_resolved.keys()))
        else:
            # Dependency not found locally - add to graph anyway (may be from registry later)
            version = dep_source.version if dep_source.type == "registry" else "0.0.0"
            graph.add_package(dep_name, version, None, [])
    
    return graph
