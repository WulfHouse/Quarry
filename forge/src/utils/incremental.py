"""Incremental compilation system for Pyrite"""

import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    """Metadata for a cached module compilation"""
    module_path: str
    source_hash: str
    dependencies: List[str]
    dependency_hashes: Dict[str, str]
    compiled_at: float
    compiler_version: str
    ast_cache_path: Optional[str] = None
    llvm_ir_path: Optional[str] = None
    object_file_path: Optional[str] = None


class DependencyGraph:
    """Track module dependencies for incremental compilation"""
    
    def __init__(self):
        self.edges: Dict[str, List[str]] = {}  # target -> [sources that depend on target]
        self.nodes: Set[str] = set()
    
    def add_node(self, module: str):
        """Add a module to the graph"""
        self.nodes.add(module)
        if module not in self.edges:
            self.edges[module] = []
    
    def add_dependency(self, source: str, target: str):
        """Add dependency: source imports/depends on target"""
        self.add_node(source)
        self.add_node(target)
        
        if target not in self.edges:
            self.edges[target] = []
        
        if source not in self.edges[target]:
            self.edges[target].append(source)
    
    def get_dependents(self, module: str) -> Set[str]:
        """Get all modules that transitively depend on this module"""
        visited = set()
        queue = [module]
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            
            visited.add(current)
            
            # Add modules that depend on current
            if current in self.edges:
                for dependent in self.edges[current]:
                    if dependent not in visited:
                        queue.append(dependent)
        
        # Don't include the module itself
        visited.discard(module)
        return visited
    
    def topological_sort(self, modules: Set[str]) -> List[str]:
        """Return modules in build order (dependencies first)"""
        # Build in-degree map for modules to compile
        in_degree = {m: 0 for m in modules}
        adj_list = {m: [] for m in modules}
        
        # Build adjacency list for modules in compilation set
        for target in modules:
            if target in self.edges:
                for source in self.edges[target]:
                    if source in modules:
                        adj_list[target].append(source)
                        in_degree[source] += 1
        
        # Kahn's algorithm
        queue = [m for m in modules if in_degree[m] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        if len(result) != len(modules):
            # Cycle detected - fall back to arbitrary order
            return list(modules)
        
        return result
    
    def to_dict(self) -> Dict:
        """Serialize to dict"""
        return {
            'nodes': list(self.nodes),
            'edges': self.edges
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DependencyGraph':
        """Deserialize from dict"""
        graph = cls()
        graph.nodes = set(data.get('nodes', []))
        graph.edges = data.get('edges', {})
        return graph


class IncrementalCompiler:
    """Manages incremental compilation with caching"""
    
    COMPILER_VERSION = "2.0.0"
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path(".pyrite/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.modules_dir = self.cache_dir / "modules"
        self.modules_dir.mkdir(exist_ok=True)
        
        self.dep_graph = DependencyGraph()
        self.module_hashes: Dict[str, str] = {}
        self.cache_entries: Dict[str, CacheEntry] = {}
        self.modules_json_path = self.cache_dir / "modules.json"  # Store module metadata in modules.json
    
    def load_cache_metadata(self):
        """Load cached metadata from previous build"""
        # Load modules.json (new format)
        if self.modules_json_path.exists():
            try:
                modules_data = json.loads(self.modules_json_path.read_text())
                for module_name, module_info in modules_data.items():
                    # Convert modules.json format to CacheEntry
                    source_hash = module_info.get("hash", "")
                    deps = module_info.get("deps", [])
                    last_compiled_str = module_info.get("last_compiled", "")
                    object_file = module_info.get("object_file", "")
                    
                    # Parse last_compiled timestamp
                    compiled_at = 0.0
                    if last_compiled_str:
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(last_compiled_str.replace('Z', '+00:00'))
                            compiled_at = dt.timestamp()
                        except Exception:
                            pass
                    
                    # Build dependency hashes
                    dep_hashes = {}
                    for dep in deps:
                        dep_hash = modules_data.get(dep, {}).get("hash", "")
                        if dep_hash:
                            dep_hashes[dep] = dep_hash
                    
                    entry = CacheEntry(
                        module_path=module_name,
                        source_hash=source_hash,
                        dependencies=deps,
                        dependency_hashes=dep_hashes,
                        compiled_at=compiled_at,
                        compiler_version=self.COMPILER_VERSION,
                        object_file_path=object_file
                    )
                    self.cache_entries[module_name] = entry
                    self.module_hashes[module_name] = source_hash
                    
                    # Update dependency graph
                    for dep in deps:
                        self.dep_graph.add_dependency(module_name, dep)
            except Exception as e:
                print(f"Warning: Failed to load modules.json: {e}")
        
        # Also load old format for backwards compatibility
        dep_graph_file = self.cache_dir / "dependency_graph.json"
        if dep_graph_file.exists():
            try:
                data = json.loads(dep_graph_file.read_text())
                self.dep_graph = DependencyGraph.from_dict(data)
            except Exception as e:
                pass  # Ignore if modules.json already loaded
        
        # Load cache entries from .meta files (backwards compatibility)
        for meta_file in self.modules_dir.glob("*.meta"):
            try:
                data = json.loads(meta_file.read_text())
                entry = CacheEntry(**data)
                if entry.module_path not in self.cache_entries:
                    self.cache_entries[entry.module_path] = entry
            except Exception as e:
                pass  # Ignore errors
    
    def save_cache_metadata(self):
        """Save cache metadata for next build"""
        # Save in modules.json format (as specified in task)
        modules_data = {}
        for module_path, entry in self.cache_entries.items():
            # Format last_compiled as ISO string
            from datetime import datetime
            last_compiled_str = datetime.fromtimestamp(entry.compiled_at).isoformat() if entry.compiled_at else ""
            
            modules_data[module_path] = {
                "hash": entry.source_hash,
                "deps": entry.dependencies,
                "last_compiled": last_compiled_str,
                "object_file": entry.object_file_path or ""
            }
        
        self.modules_json_path.write_text(json.dumps(modules_data, indent=2))
        
        # Also save dependency graph (for backwards compatibility)
        dep_graph_file = self.cache_dir / "dependency_graph.json"
        dep_graph_file.write_text(json.dumps(self.dep_graph.to_dict(), indent=2))
        
        # Save module hashes (for backwards compatibility)
        hashes_file = self.cache_dir / "module_hashes.json"
        hashes_file.write_text(json.dumps(self.module_hashes, indent=2))
    
    def compute_file_hash(self, filepath: Path) -> str:
        """Compute hash of file contents"""
        hasher = hashlib.blake2b()
        
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
    
    def should_recompile(self, module_path: str) -> Tuple[bool, str]:
        """Check if module needs recompilation"""
        # Check if cache entry exists
        cache_entry = self.cache_entries.get(module_path)
        if not cache_entry:
            return True, "No cache entry"
        
        # Check source hash
        current_hash = self.compute_file_hash(Path(module_path))
        if current_hash != cache_entry.source_hash:
            return True, "Source changed"
        
        # Check compiler version
        if self.COMPILER_VERSION != cache_entry.compiler_version:
            return True, "Compiler version changed"
        
        # Check if object file exists
        if cache_entry.object_file_path:
            obj_path = Path(cache_entry.object_file_path)
            if not obj_path.exists():
                return True, "Object file missing"
        
        # Check dependency hashes
        for dep, old_hash in cache_entry.dependency_hashes.items():
            current_dep_hash = self.module_hashes.get(dep, "")
            if current_dep_hash != old_hash:
                return True, f"Dependency {dep} changed"
        
        return False, "Cache valid"
    
    def save_cache_entry(self, module_path: str, entry: CacheEntry):
        """Save cache entry for a module"""
        self.cache_entries[module_path] = entry
        
        # Save to disk
        meta_file = self.modules_dir / f"{Path(module_path).stem}.meta"
        meta_file.write_text(json.dumps(asdict(entry), indent=2))
        
        # Update hash cache
        self.module_hashes[module_path] = entry.source_hash
    
    def invalidate_dependents(self, changed_module: str) -> Set[str]:
        """Get all modules that need recompilation due to change"""
        return self.dep_graph.get_dependents(changed_module)
    
    def discover_modules(self, entry_point: Path) -> List[str]:
        """Discover all modules in project"""
        # For MVP, just return entry point
        # Full implementation would traverse imports
        return [str(entry_point)]
    
    def extract_dependencies(self, program_ast) -> List[str]:
        """Extract module dependencies from AST
        
        Args:
            program_ast: Program AST node
            
        Returns:
            List of module names (dependencies)
        """
        dependencies = []
        
        # Program has imports list
        if hasattr(program_ast, 'imports'):
            for import_stmt in program_ast.imports:
                # ImportStmt has path attribute (list of strings like ["std", "collections"])
                if hasattr(import_stmt, 'path'):
                    # Convert path list to string (e.g., ["std", "collections"] -> "std::collections")
                    module_path = "::".join(import_stmt.path)
                    dependencies.append(module_path)
        
        # Also check function bodies for imports (if any)
        if hasattr(program_ast, 'items'):
            for item in program_ast.items:
                if hasattr(item, '__class__') and item.__class__.__name__ == 'FunctionDef':
                    if hasattr(item, 'body') and hasattr(item.body, 'statements'):
                        for stmt in item.body.statements:
                            if hasattr(stmt, '__class__') and stmt.__class__.__name__ == 'ImportStmt':
                                if hasattr(stmt, 'path'):
                                    # Convert path list to string
                                    module_path = "::".join(stmt.path)
                                    dependencies.append(module_path)
        
        return dependencies


class IncrementalBuildCache:
    """Simple file-based cache for incremental builds"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get(self, key: str) -> Optional[bytes]:
        """Get cached data"""
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            return cache_file.read_bytes()
        return None
    
    def set(self, key: str, data: bytes):
        """Store data in cache"""
        cache_file = self.cache_dir / f"{key}.cache"
        cache_file.write_bytes(data)
    
    def clear(self):
        """Clear all cached data"""
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
    
    def size(self) -> int:
        """Get total cache size in bytes"""
        total = 0
        for cache_file in self.cache_dir.glob("*.cache"):
            total += cache_file.stat().st_size
        return total


def compute_module_hash(module_path: Path, dep_hashes: Dict[str, str]) -> str:
    """Compute hash including source and dependencies"""
    hasher = hashlib.blake2b()
    
    # Source content
    with open(module_path, 'rb') as f:
        hasher.update(f.read())
    
    # Dependency hashes (sorted for consistency)
    for dep in sorted(dep_hashes.keys()):
        hasher.update(dep.encode())
        hasher.update(dep_hashes[dep].encode())
    
    return hasher.hexdigest()


# Example usage
if __name__ == '__main__':
    compiler = IncrementalCompiler()
    compiler.load_cache_metadata()
    
    # Check a module
    should_compile, reason = compiler.should_recompile("src/main.pyrite")
    print(f"Should recompile: {should_compile} ({reason})")

