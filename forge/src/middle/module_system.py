"""Module system for Pyrite"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from .. import ast
from ..frontend.lexer import lex
from ..frontend.parser import parse


class ModuleError(Exception):
    """Module resolution error"""
    pass


class Module:
    """Represents a compiled module"""
    def __init__(self, path: Path, ast: ast.Program):
        self.path = path
        self.ast = ast
        self.name = path.stem
        self.dependencies: Set[str] = set()


class ModuleResolver:
    """Resolves and loads modules"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.modules: Dict[str, Module] = {}
        self.loading: Set[str] = set()  # For circular import detection
    
    def resolve_import(self, import_path: List[str]) -> Optional[Path]:
        """Resolve import path to file path"""
        # Handle stdlib imports: std::string -> stdlib/string/string.pyrite
        # Pattern: if path starts with 'std', remove it and resolve in stdlib
        if import_path and import_path[0] == 'std':
            # Remove 'std' prefix
            path_parts = import_path[1:]
            if not path_parts:
                return None
            
            # Build stdlib path based on structure:
            # - std::string -> pyrite/string/string.pyrite
            # - std::collections::list -> pyrite/collections/list.pyrite
            # - std::io::path -> pyrite/io/path.pyrite
            # - std::core::option -> pyrite/core/option.pyrite
            # stdlib is now in pyrite/ directory at repo root
            repo_root = Path(__file__).parent.parent.parent.parent  # forge/src/middle -> forge/src -> forge -> repo root
            if len(path_parts) == 1:
                # Single part: part -> part/part.pyrite
                module_name = path_parts[0]
                stdlib_path = repo_root / 'pyrite' / module_name / f'{module_name}.pyrite'
            else:
                # Multiple parts: part1::part2 -> part1/part2.pyrite
                dir_name = path_parts[0]
                file_name = path_parts[-1]
                stdlib_path = repo_root / 'pyrite' / dir_name / f'{file_name}.pyrite'
            
            if stdlib_path.exists():
                return stdlib_path
        
        # Try relative to root (for non-stdlib imports)
        relative_path = Path(*import_path).with_suffix('.pyrite')
        full_path = self.root_dir / relative_path
        if full_path.exists():
            return full_path
        
        return None
    
    def load_module(self, import_path: List[str]) -> Optional[Module]:
        """Load a module by import path"""
        module_name = '::'.join(import_path)
        
        # Check if already loaded
        if module_name in self.modules:
            return self.modules[module_name]
        
        # Detect circular imports
        if module_name in self.loading:
            raise ModuleError(f"Circular import detected: {module_name}")
        
        # Resolve to file path
        file_path = self.resolve_import(import_path)
        if not file_path:
            raise ModuleError(f"Module not found: {module_name}")
        
        # Mark as loading
        self.loading.add(module_name)
        
        # Parse module
        source = file_path.read_text(encoding='utf-8')
        tokens = lex(source, str(file_path))
        module_ast = parse(tokens)
        
        # Create module
        module = Module(file_path, module_ast)
        
        # Load dependencies recursively
        for import_stmt in module_ast.imports:
            dep_module = self.load_module(import_stmt.path)
            if dep_module:
                module.dependencies.add('::'.join(import_stmt.path))
        
        # Done loading
        self.loading.remove(module_name)
        self.modules[module_name] = module
        
        return module
    
    def get_all_modules(self) -> List[Module]:
        """Get all loaded modules in dependency order"""
        # Topological sort
        result = []
        visited = set()
        
        def visit(module_name: str):
            if module_name in visited:
                return
            visited.add(module_name)
            
            if module_name not in self.modules:
                return
            
            module = self.modules[module_name]
            
            # Visit dependencies first
            for dep in module.dependencies:
                visit(dep)
            
            result.append(module)
        
        # Visit all modules
        for module_name in self.modules:
            visit(module_name)
        
        return result


def resolve_modules(main_file: Path) -> List[Module]:
    """Resolve all modules starting from main file"""
    resolver = ModuleResolver(main_file.parent)
    
    # Load main module
    source = main_file.read_text(encoding='utf-8')
    tokens = lex(source, str(main_file))
    main_ast = parse(tokens)
    
    main_module = Module(main_file, main_ast)
    resolver.modules['main'] = main_module
    
    # Load all imports
    for import_stmt in main_ast.imports:
        try:
            resolver.load_module(import_stmt.path)
        except ModuleError as e:
            print(f"Warning: {e}")
    
    return resolver.get_all_modules()

