"""Test build graph construction"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.build_graph import BuildGraph, construct_build_graph, PackageNode


def test_build_graph_single_package():
    """Test build graph with single package (no deps)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create Quarry.toml without dependencies
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "test"
version = "0.1.0"
""")
        
        # Create empty lockfile
        lockfile = project_dir / "Quarry.lock"
        lockfile.write_text("""[dependencies]
""")
        
        graph = construct_build_graph(str(project_dir))
        assert len(graph.nodes) == 1, "Should have one package (main)"
        assert "main" in graph.nodes


def test_build_graph_with_dependencies():
    """Test build graph with dependencies"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create main Quarry.toml
        toml_file = project_dir / "Quarry.toml"
        toml_file.write_text("""[package]
name = "main"
version = "0.1.0"

[dependencies]
foo = "1.0.0"
""")
        
        # Create lockfile
        lockfile = project_dir / "Quarry.lock"
        lockfile.write_text("""[dependencies]
foo = "1.0.0"
""")
        
        graph = construct_build_graph(str(project_dir))
        assert len(graph.nodes) >= 1, "Should have at least main package"
        assert "main" in graph.nodes
        deps = graph.get_dependencies("main")
        assert "foo" in deps, "Main should depend on foo"


def test_build_graph_circular_dependency():
    """Test that circular dependencies are detected"""
    graph = BuildGraph()
    graph.add_package("A", "1.0.0", Path("a"), ["B"])
    graph.add_package("B", "1.0.0", Path("b"), ["A"])
    
    assert graph.has_cycle() == True, "Should detect cycle A -> B -> A"


def test_build_graph_no_cycle():
    """Test that acyclic graph is detected correctly"""
    graph = BuildGraph()
    graph.add_package("A", "1.0.0", Path("a"), ["B"])
    graph.add_package("B", "1.0.0", Path("b"), [])
    
    assert graph.has_cycle() == False, "Should not detect cycle in A -> B"


def test_build_graph_get_dependencies():
    """Test getting dependencies from graph"""
    graph = BuildGraph()
    graph.add_package("main", "1.0.0", Path("main"), ["foo", "bar"])
    graph.add_package("foo", "1.0.0", Path("foo"), [])
    graph.add_package("bar", "1.0.0", Path("bar"), ["baz"])
    
    deps = graph.get_dependencies("main")
    assert "foo" in deps
    assert "bar" in deps
    assert len(deps) == 2
    
    foo_deps = graph.get_dependencies("foo")
    assert len(foo_deps) == 0


def test_topological_sort_simple():
    """Test topological sort with simple graph"""
    graph = BuildGraph()
    graph.add_package("A", "1.0.0", Path("a"), ["B"])
    graph.add_package("B", "1.0.0", Path("b"), [])
    
    order = graph.topological_sort()
    assert "B" in order
    assert "A" in order
    assert order.index("B") < order.index("A"), "B should come before A (dependency first)"


def test_topological_sort_complex():
    """Test topological sort with complex graph"""
    graph = BuildGraph()
    graph.add_package("main", "1.0.0", Path("main"), ["foo", "bar"])
    graph.add_package("foo", "1.0.0", Path("foo"), ["baz"])
    graph.add_package("bar", "1.0.0", Path("bar"), ["baz"])
    graph.add_package("baz", "1.0.0", Path("baz"), [])
    
    order = graph.topological_sort()
    # baz should come first (no deps)
    assert order[0] == "baz", "baz should be first (no dependencies)"
    # main should come last (depends on everything)
    assert order[-1] == "main", "main should be last (depends on others)"
    # foo and bar should come after baz but before main
    assert "foo" in order
    assert "bar" in order
    assert order.index("baz") < order.index("foo")
    assert order.index("baz") < order.index("bar")
    assert order.index("foo") < order.index("main")
    assert order.index("bar") < order.index("main")


def test_topological_sort_detects_cycle():
    """Test that topological sort detects cycles"""
    graph = BuildGraph()
    graph.add_package("A", "1.0.0", Path("a"), ["B"])
    graph.add_package("B", "1.0.0", Path("b"), ["A"])
    
    with pytest.raises(ValueError):
        graph.topological_sort()
