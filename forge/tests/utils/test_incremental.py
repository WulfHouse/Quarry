"""Tests for incremental compilation"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
import json
import tempfile
import time
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.incremental import (
    DependencyGraph,
    IncrementalCompiler,
    IncrementalBuildCache,
    CacheEntry,
    compute_module_hash
)


class TestDependencyGraph:
    """Test dependency graph operations"""
    
    def test_add_node(self):
        """Test adding nodes to graph"""
        graph = DependencyGraph()
        graph.add_node("main.pyrite")
        
        assert "main.pyrite" in graph.nodes
    
    def test_add_dependency(self):
        """Test adding dependencies"""
        graph = DependencyGraph()
        graph.add_dependency("main.pyrite", "utils.pyrite")
        
        assert "main.pyrite" in graph.nodes
        assert "utils.pyrite" in graph.nodes
        assert "main.pyrite" in graph.edges["utils.pyrite"]
    
    def test_get_dependents_simple(self):
        """Test getting direct dependents"""
        graph = DependencyGraph()
        graph.add_dependency("main.pyrite", "utils.pyrite")
        
        dependents = graph.get_dependents("utils.pyrite")
        
        assert "main.pyrite" in dependents
    
    def test_get_dependents_transitive(self):
        """Test getting transitive dependents"""
        graph = DependencyGraph()
        graph.add_dependency("main.pyrite", "utils.pyrite")
        graph.add_dependency("utils.pyrite", "math.pyrite")
        
        dependents = graph.get_dependents("math.pyrite")
        
        # Both utils and main depend on math (transitively)
        assert "utils.pyrite" in dependents
        assert "main.pyrite" in dependents
    
    def test_topological_sort_simple(self):
        """Test topological sort"""
        graph = DependencyGraph()
        graph.add_dependency("main.pyrite", "utils.pyrite")
        graph.add_dependency("main.pyrite", "config.pyrite")
        
        modules = {"main.pyrite", "utils.pyrite", "config.pyrite"}
        order = graph.topological_sort(modules)
        
        # Dependencies should come before dependents
        main_idx = order.index("main.pyrite")
        utils_idx = order.index("utils.pyrite")
        config_idx = order.index("config.pyrite")
        
        assert utils_idx < main_idx
        assert config_idx < main_idx
    
    def test_topological_sort_chain(self):
        """Test topological sort with chain"""
        graph = DependencyGraph()
        graph.add_dependency("main.pyrite", "utils.pyrite")
        graph.add_dependency("utils.pyrite", "math.pyrite")
        
        modules = {"main.pyrite", "utils.pyrite", "math.pyrite"}
        order = graph.topological_sort(modules)
        
        # Should be: math, utils, main
        assert order.index("math.pyrite") < order.index("utils.pyrite")
        assert order.index("utils.pyrite") < order.index("main.pyrite")
    
    def test_serialize_deserialize(self):
        """Test graph serialization"""
        graph = DependencyGraph()
        graph.add_dependency("main.pyrite", "utils.pyrite")
        graph.add_dependency("utils.pyrite", "math.pyrite")
        
        # Serialize
        data = graph.to_dict()
        
        # Deserialize
        graph2 = DependencyGraph.from_dict(data)
        
        assert graph2.nodes == graph.nodes
        assert graph2.edges == graph.edges
    
    def test_topological_sort_cycle_detection(self):
        """Test topological sort with cycle detection (covers lines 98-100)"""
        graph = DependencyGraph()
        # Create a cycle: A -> B -> C -> A
        graph.add_dependency("A.pyrite", "B.pyrite")
        graph.add_dependency("B.pyrite", "C.pyrite")
        graph.add_dependency("C.pyrite", "A.pyrite")
        
        modules = {"A.pyrite", "B.pyrite", "C.pyrite"}
        order = graph.topological_sort(modules)
        
        # Should fall back to arbitrary order (all modules present)
        assert len(order) == 3
        assert set(order) == modules
    
    def test_get_dependents_visited_check(self):
        """Test get_dependents() with visited check (covers lines 56-57)"""
        graph = DependencyGraph()
        # Create: A -> B -> C, and A -> C (C appears twice in traversal)
        graph.add_dependency("A.pyrite", "B.pyrite")
        graph.add_dependency("B.pyrite", "C.pyrite")
        graph.add_dependency("A.pyrite", "C.pyrite")
        
        dependents = graph.get_dependents("C.pyrite")
        
        # Should include both A and B, but not duplicate
        assert "A.pyrite" in dependents
        assert "B.pyrite" in dependents
        assert len(dependents) == 2
    
    def test_add_dependency_duplicate(self):
        """Test add_dependency() doesn't add duplicates (covers line 46-47)"""
        graph = DependencyGraph()
        graph.add_dependency("A.pyrite", "B.pyrite")
        graph.add_dependency("A.pyrite", "B.pyrite")  # Add again
        
        # Should only appear once
        assert graph.edges["B.pyrite"].count("A.pyrite") == 1


class TestIncrementalCompiler:
    """Test incremental compiler"""
    
    def test_compiler_creation(self):
        """Test creating incremental compiler"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            assert compiler.cache_dir.exists()
            assert compiler.modules_dir.exists()
    
    def test_compute_file_hash(self):
        """Test file hashing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            
            hash1 = compiler.compute_file_hash(test_file)
            
            assert hash1
            assert len(hash1) > 0
            
            # Same content = same hash
            hash2 = compiler.compute_file_hash(test_file)
            assert hash1 == hash2
            
            # Different content = different hash
            test_file.write_text("fn main():\n    print('world')")
            hash3 = compiler.compute_file_hash(test_file)
            assert hash3 != hash1
    
    def test_should_recompile_no_cache(self):
        """Test recompilation when no cache exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            should, reason = compiler.should_recompile("main.pyrite")
            
            assert should is True
            assert "No cache entry" in reason
    
    def test_should_recompile_source_changed(self):
        """Test recompilation when source changes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            
            # Create cache entry with old hash
            entry = CacheEntry(
                module_path=str(test_file),
                source_hash="old_hash",
                dependencies=[],
                dependency_hashes={},
                compiled_at=time.time(),
                compiler_version=compiler.COMPILER_VERSION
            )
            compiler.cache_entries[str(test_file)] = entry
            
            should, reason = compiler.should_recompile(str(test_file))
            
            assert should is True
            assert "Source changed" in reason
    
    def test_should_recompile_cache_valid(self):
        """Test no recompilation when cache is valid"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            
            # Create cache entry with current hash
            current_hash = compiler.compute_file_hash(test_file)
            entry = CacheEntry(
                module_path=str(test_file),
                source_hash=current_hash,
                dependencies=[],
                dependency_hashes={},
                compiled_at=time.time(),
                compiler_version=compiler.COMPILER_VERSION,
                object_file_path=str(test_file.with_suffix('.o'))
            )
            compiler.cache_entries[str(test_file)] = entry
            
            # Create dummy object file
            Path(entry.object_file_path).touch()
            
            should, reason = compiler.should_recompile(str(test_file))
            
            assert should is False
            assert "Cache valid" in reason
    
    def test_save_and_load_cache_entry(self):
        """Test cache entry persistence"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            entry = CacheEntry(
                module_path="main.pyrite",
                source_hash="abc123",
                dependencies=["utils.pyrite"],
                dependency_hashes={"utils.pyrite": "def456"},
                compiled_at=time.time(),
                compiler_version="2.0.0"
            )
            
            compiler.save_cache_entry("main.pyrite", entry)
            
            # Load in new compiler instance
            compiler2 = IncrementalCompiler(Path(tmpdir))
            compiler2.load_cache_metadata()
            
            loaded_entry = compiler2.cache_entries.get("main.pyrite")
            assert loaded_entry is not None
            assert loaded_entry.source_hash == "abc123"
            assert loaded_entry.dependencies == ["utils.pyrite"]


class TestBuildCache:
    """Test build cache operations"""
    
    def test_cache_creation(self):
        """Test creating cache"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = IncrementalBuildCache(Path(tmpdir))
            assert cache.cache_dir.exists()
    
    def test_cache_get_set(self):
        """Test cache get/set"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = IncrementalBuildCache(Path(tmpdir))
            
            # Set data
            cache.set("test_key", b"test_data")
            
            # Get data
            data = cache.get("test_key")
            assert data == b"test_data"
    
    def test_cache_get_missing(self):
        """Test getting non-existent key"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = IncrementalBuildCache(Path(tmpdir))
            
            data = cache.get("nonexistent")
            assert data is None
    
    def test_cache_clear(self):
        """Test clearing cache"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = IncrementalBuildCache(Path(tmpdir))
            
            # Add some data
            cache.set("key1", b"data1")
            cache.set("key2", b"data2")
            
            # Clear
            cache.clear()
            
            # Should be empty
            assert cache.get("key1") is None
            assert cache.get("key2") is None
    
    def test_cache_size(self):
        """Test cache size calculation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = IncrementalBuildCache(Path(tmpdir))
            
            # Add data
            cache.set("key1", b"x" * 1000)
            cache.set("key2", b"y" * 2000)
            
            size = cache.size()
            assert size >= 3000  # At least the data we wrote


class TestModuleHashing:
    """Test module hashing"""
    
    def test_compute_module_hash(self):
        """Test module hash computation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            
            hash1 = compute_module_hash(test_file, {})
            
            assert hash1
            assert len(hash1) > 0
            
            # Same content = same hash
            hash2 = compute_module_hash(test_file, {})
            assert hash1 == hash2
    
    def test_module_hash_includes_dependencies(self):
        """Test that module hash includes dependency hashes"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            
            # Hash with no dependencies
            hash1 = compute_module_hash(test_file, {})
            
            # Hash with dependencies
            hash2 = compute_module_hash(test_file, {"utils.pyrite": "abc123"})
            
            # Should be different
            assert hash1 != hash2


    def test_topological_sort_cycle_detection(self):
        """Test topological sort with cycle detection (covers lines 98-100)"""
        graph = DependencyGraph()
        # Create a cycle: A -> B -> C -> A
        graph.add_dependency("A.pyrite", "B.pyrite")
        graph.add_dependency("B.pyrite", "C.pyrite")
        graph.add_dependency("C.pyrite", "A.pyrite")
        
        modules = {"A.pyrite", "B.pyrite", "C.pyrite"}
        order = graph.topological_sort(modules)
        
        # Should fall back to arbitrary order (all modules present)
        assert len(order) == 3
        assert set(order) == modules
    
    def test_get_dependents_visited_check(self):
        """Test get_dependents() with visited check (covers lines 56-57)"""
        graph = DependencyGraph()
        # Create: A -> B -> C, and A -> C (C appears twice in traversal)
        graph.add_dependency("A.pyrite", "B.pyrite")
        graph.add_dependency("B.pyrite", "C.pyrite")
        graph.add_dependency("A.pyrite", "C.pyrite")
        
        dependents = graph.get_dependents("C.pyrite")
        
        # Should include both A and B, but not duplicate
        assert "A.pyrite" in dependents
        assert "B.pyrite" in dependents
        assert len(dependents) == 2
    
    def test_add_dependency_duplicate(self):
        """Test add_dependency() doesn't add duplicates (covers line 46-47)"""
        graph = DependencyGraph()
        graph.add_dependency("A.pyrite", "B.pyrite")
        graph.add_dependency("A.pyrite", "B.pyrite")  # Add again
        
        # Should only appear once
        assert graph.edges["B.pyrite"].count("A.pyrite") == 1
    
    def test_compute_file_hash_error(self):
        """Test compute_file_hash() with file error (covers line 185-186)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Try to hash non-existent file
            non_existent = Path(tmpdir) / "nonexistent.pyrite"
            hash_result = compiler.compute_file_hash(non_existent)
            
            # Should return empty string on error
            assert hash_result == ""
    
    def test_load_cache_metadata_json_error(self):
        """Test load_cache_metadata() with invalid JSON (covers lines 144-146, 153-155, 163-164)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            modules_dir = cache_dir / "modules"
            modules_dir.mkdir()
            
            # Create invalid JSON files
            dep_graph_file = cache_dir / "dependency_graph.json"
            dep_graph_file.write_text("invalid json{")
            
            hashes_file = cache_dir / "module_hashes.json"
            hashes_file.write_text("invalid json{")
            
            meta_file = modules_dir / "test.meta"
            meta_file.write_text("invalid json{")
            
            # Should not crash, should create empty structures
            compiler = IncrementalCompiler(cache_dir)
            assert isinstance(compiler.dep_graph, DependencyGraph)
            assert isinstance(compiler.module_hashes, dict)
            assert len(compiler.cache_entries) == 0


    def test_should_recompile_compiler_version_changed(self):
        """Test recompilation when compiler version changes (covers lines 201-202)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            current_hash = compiler.compute_file_hash(test_file)
            
            # Create cache entry with old compiler version
            entry = CacheEntry(
                module_path=str(test_file),
                source_hash=current_hash,
                dependencies=[],
                dependency_hashes={},
                compiled_at=time.time(),
                compiler_version="1.0.0"  # Old version
            )
            compiler.cache_entries[str(test_file)] = entry
            
            should, reason = compiler.should_recompile(str(test_file))
            
            assert should is True
            assert "Compiler version changed" in reason
    
    def test_should_recompile_object_file_missing(self):
        """Test recompilation when object file is missing (covers lines 205-208)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            current_hash = compiler.compute_file_hash(test_file)
            
            # Create cache entry with object file path, but file doesn't exist
            entry = CacheEntry(
                module_path=str(test_file),
                source_hash=current_hash,
                dependencies=[],
                dependency_hashes={},
                compiled_at=time.time(),
                compiler_version=compiler.COMPILER_VERSION,
                object_file_path=str(Path(tmpdir) / "test.o")  # File doesn't exist
            )
            compiler.cache_entries[str(test_file)] = entry
            
            should, reason = compiler.should_recompile(str(test_file))
            
            assert should is True
            assert "Object file missing" in reason
    
    def test_should_recompile_dependency_changed(self):
        """Test recompilation when dependency hash changes (covers lines 210-214)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            current_hash = compiler.compute_file_hash(test_file)
            
            # Create cache entry with old dependency hash
            entry = CacheEntry(
                module_path=str(test_file),
                source_hash=current_hash,
                dependencies=["utils.pyrite"],
                dependency_hashes={"utils.pyrite": "old_hash"},
                compiled_at=time.time(),
                compiler_version=compiler.COMPILER_VERSION,
                object_file_path=str(Path(tmpdir) / "test.o")
            )
            compiler.cache_entries[str(test_file)] = entry
            compiler.module_hashes["utils.pyrite"] = "new_hash"  # Different hash
            
            # Create dummy object file
            Path(entry.object_file_path).touch()
            
            should, reason = compiler.should_recompile(str(test_file))
            
            assert should is True
            assert "Dependency" in reason and "changed" in reason
    
    def test_should_recompile_dependency_not_in_hashes(self):
        """Test recompilation when dependency not in module_hashes (covers line 212)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create test file
            test_file = Path(tmpdir) / "test.pyrite"
            test_file.write_text("fn main():\n    print('hello')")
            current_hash = compiler.compute_file_hash(test_file)
            
            # Create cache entry with dependency, but dependency not in module_hashes
            entry = CacheEntry(
                module_path=str(test_file),
                source_hash=current_hash,
                dependencies=["utils.pyrite"],
                dependency_hashes={"utils.pyrite": "some_hash"},
                compiled_at=time.time(),
                compiler_version=compiler.COMPILER_VERSION,
                object_file_path=str(Path(tmpdir) / "test.o")
            )
            compiler.cache_entries[str(test_file)] = entry
            # Don't add utils.pyrite to module_hashes - should trigger recompile
            
            # Create dummy object file
            Path(entry.object_file_path).touch()
            
            should, reason = compiler.should_recompile(str(test_file))
            
            assert should is True
            assert "Dependency" in reason
    
    def test_discover_modules(self):
        """Test module discovery (covers lines 233-237)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            entry_point = Path(tmpdir) / "main.pyrite"
            entry_point.write_text("fn main():\n    pass")
            
            modules = compiler.discover_modules(entry_point)
            
            assert len(modules) == 1
            assert str(entry_point) in modules
    
    def test_extract_dependencies_no_statements(self):
        """Test extract_dependencies with AST without statements (covers line 244)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create mock AST without statements attribute
            class MockAST:
                pass
            
            ast = MockAST()
            deps = compiler.extract_dependencies(ast)
            
            assert deps == []
    
    def test_extract_dependencies_with_imports(self):
        """Test extract_dependencies with import statements (covers lines 245-247)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Create mock AST with import statements
            # Create a proper Program AST with imports
            from src import ast as pyrite_ast
            from src.frontend.tokens import Span
            
            # Create ImportStmt nodes
            import1 = pyrite_ast.ImportStmt(
                path=["utils"],
                alias=None,
                span=Span("<test>", 1, 1, 1, 10)
            )
            import2 = pyrite_ast.ImportStmt(
                path=["math"],
                alias=None,
                span=Span("<test>", 2, 1, 2, 10)
            )
            
            # Create Program with imports
            program_ast = pyrite_ast.Program(
                imports=[import1, import2],
                items=[],
                span=Span("<test>", 1, 1, 1, 1)
            )
            
            deps = compiler.extract_dependencies(program_ast)
            
            # extract_dependencies returns module paths as strings (e.g., "utils", "math")
            assert len(deps) == 2, f"Expected 2 dependencies, got {deps}"
            assert "utils" in deps, f"utils not found in {deps}"
            assert "math" in deps, f"math not found in {deps}"
    
    def test_invalidate_dependents(self):
        """Test invalidate_dependents method (covers line 231)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Build dependency graph
            compiler.dep_graph.add_dependency("main.pyrite", "utils.pyrite")
            compiler.dep_graph.add_dependency("utils.pyrite", "math.pyrite")
            
            # Get dependents of math.pyrite
            dependents = compiler.invalidate_dependents("math.pyrite")
            
            assert "utils.pyrite" in dependents
            assert "main.pyrite" in dependents
    
    def test_empty_dependency_graph_topological_sort(self):
        """Test topological sort with empty graph"""
        graph = DependencyGraph()
        modules = set()
        order = graph.topological_sort(modules)
        
        assert order == []
    
    def test_single_node_topological_sort(self):
        """Test topological sort with single node"""
        graph = DependencyGraph()
        graph.add_node("main.pyrite")
        
        modules = {"main.pyrite"}
        order = graph.topological_sort(modules)
        
        assert order == ["main.pyrite"]
    
    def test_get_dependents_no_dependents(self):
        """Test get_dependents when module has no dependents"""
        graph = DependencyGraph()
        graph.add_node("main.pyrite")
        
        dependents = graph.get_dependents("main.pyrite")
        
        assert len(dependents) == 0
    
    def test_get_dependents_excludes_self(self):
        """Test get_dependents excludes the module itself (covers line 68)"""
        graph = DependencyGraph()
        graph.add_dependency("A.pyrite", "B.pyrite")
        graph.add_dependency("B.pyrite", "B.pyrite")  # Self-dependency (edge case)
        
        dependents = graph.get_dependents("B.pyrite")
        
        # Should include A but not B itself
        assert "A.pyrite" in dependents
        assert "B.pyrite" not in dependents
    
    def test_save_cache_metadata_creates_files(self):
        """Test save_cache_metadata creates files (covers lines 166-174)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            compiler = IncrementalCompiler(Path(tmpdir))
            
            # Add some data
            compiler.dep_graph.add_node("main.pyrite")
            compiler.module_hashes["main.pyrite"] = "abc123"
            
            # Save
            compiler.save_cache_metadata()
            
            # Check files exist
            dep_graph_file = compiler.cache_dir / "dependency_graph.json"
            hashes_file = compiler.cache_dir / "module_hashes.json"
            
            assert dep_graph_file.exists()
            assert hashes_file.exists()
            
            # Verify content
            dep_data = json.loads(dep_graph_file.read_text())
            assert "main.pyrite" in dep_data["nodes"]
            
            hash_data = json.loads(hashes_file.read_text())
            assert hash_data["main.pyrite"] == "abc123"
    
    def test_cache_entry_with_optional_fields(self):
        """Test CacheEntry with optional fields (ast_cache_path, llvm_ir_path)"""
        entry = CacheEntry(
            module_path="main.pyrite",
            source_hash="abc123",
            dependencies=[],
            dependency_hashes={},
            compiled_at=time.time(),
            compiler_version="2.0.0",
            ast_cache_path="main.ast",
            llvm_ir_path="main.ll"
        )
        
        assert entry.ast_cache_path == "main.ast"
        assert entry.llvm_ir_path == "main.ll"
        assert entry.object_file_path is None
    
    def test_add_node_creates_edge_entry(self):
        """Test add_node creates edge entry if not exists (covers lines 35-36)"""
        graph = DependencyGraph()
        graph.add_node("main.pyrite")
        
        assert "main.pyrite" in graph.nodes
        assert "main.pyrite" in graph.edges
        assert graph.edges["main.pyrite"] == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

