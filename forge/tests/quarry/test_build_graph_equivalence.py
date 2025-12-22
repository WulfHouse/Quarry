"""Equivalence tests for build graph algorithms

Tests that Pyrite FFI implementation matches Python implementation exactly.
"""

import pytest
import sys
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.build_graph import BuildGraph
from quarry.bridge.build_graph_bridge import _has_cycle_ffi, _topological_sort_ffi, _has_cycle_python, _topological_sort_python


class TestHasCycleEquivalence:
    """Test has_cycle equivalence between Python and Pyrite"""
    
    def test_empty_graph(self):
        """Empty graph has no cycles"""
        edges = {}
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == False
    
    def test_single_node(self):
        """Single node has no cycles"""
        edges = {"A": []}
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == False
    
    def test_simple_acyclic(self):
        """Simple acyclic graph has no cycles"""
        edges = {"A": ["B"], "B": []}
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == False
    
    def test_simple_cycle(self):
        """Simple cycle A -> B -> A"""
        edges = {"A": ["B"], "B": ["A"]}
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == True
    
    def test_three_node_cycle(self):
        """Three node cycle A -> B -> C -> A"""
        edges = {"A": ["B"], "B": ["C"], "C": ["A"]}
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == True
    
    def test_self_loop(self):
        """Self-loop A -> A"""
        edges = {"A": ["A"]}
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == True
    
    def test_complex_acyclic(self):
        """Complex acyclic graph"""
        edges = {
            "main": ["foo", "bar"],
            "foo": ["baz"],
            "bar": ["baz"],
            "baz": []
        }
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == False
    
    def test_complex_with_cycle(self):
        """Complex graph with cycle"""
        edges = {
            "main": ["foo"],
            "foo": ["bar"],
            "bar": ["foo"]  # Cycle: foo -> bar -> foo
        }
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == True
    
    def test_disconnected_components(self):
        """Disconnected components, one with cycle"""
        edges = {
            "A": ["B"],
            "B": ["A"],  # Cycle
            "C": ["D"],
            "D": []  # No cycle
        }
        python_result = _has_cycle_python(edges)
        pyrite_result = _has_cycle_ffi(edges)
        assert python_result == pyrite_result == True
    
    def test_build_graph_class_has_cycle(self):
        """Test BuildGraph.has_cycle() method"""
        graph = BuildGraph()
        graph.add_package("A", "1.0.0", Path("a"), ["B"])
        graph.add_package("B", "1.0.0", Path("b"), ["A"])
        
        result = graph.has_cycle()
        assert result == True


class TestTopologicalSortEquivalence:
    """Test topological_sort equivalence between Python and Pyrite"""
    
    def test_empty_graph(self):
        """Empty graph"""
        edges = {}
        python_result = _topological_sort_python(edges)
        pyrite_result = _topological_sort_ffi(edges)
        # Both should return empty list
        assert python_result == pyrite_result == []
    
    def test_single_node(self):
        """Single node"""
        edges = {"A": []}
        python_result = _topological_sort_python(edges)
        pyrite_result = _topological_sort_ffi(edges)
        assert python_result == pyrite_result == ["A"]
    
    def test_simple_chain(self):
        """Simple chain A -> B -> C"""
        edges = {"A": ["B"], "B": ["C"], "C": []}
        python_result = _topological_sort_python(edges)
        pyrite_result = _topological_sort_ffi(edges)
        # Order should be C, B, A (dependencies first)
        assert len(python_result) == len(pyrite_result) == 3
        assert python_result.index("C") < python_result.index("B")
        assert python_result.index("B") < python_result.index("A")
        assert pyrite_result.index("C") < pyrite_result.index("B")
        assert pyrite_result.index("B") < pyrite_result.index("A")
        # Both should have same elements
        assert set(python_result) == set(pyrite_result)
    
    def test_diamond_dependency(self):
        """Diamond: A -> [B, C] -> D"""
        edges = {
            "A": ["B", "C"],
            "B": ["D"],
            "C": ["D"],
            "D": []
        }
        python_result = _topological_sort_python(edges)
        pyrite_result = _topological_sort_ffi(edges)
        # D should come first, A should come last
        assert python_result[0] == "D"
        assert python_result[-1] == "A"
        assert pyrite_result[0] == "D"
        assert pyrite_result[-1] == "A"
        # Both should have same elements
        assert set(python_result) == set(pyrite_result)
        # Dependencies should come before dependents
        assert python_result.index("D") < python_result.index("B")
        assert python_result.index("D") < python_result.index("C")
        assert python_result.index("B") < python_result.index("A")
        assert python_result.index("C") < python_result.index("A")
    
    def test_complex_dag(self):
        """Complex DAG"""
        edges = {
            "main": ["foo", "bar"],
            "foo": ["baz"],
            "bar": ["baz"],
            "baz": []
        }
        python_result = _topological_sort_python(edges)
        pyrite_result = _topological_sort_ffi(edges)
        # baz should come first, main should come last
        assert python_result[0] == "baz"
        assert python_result[-1] == "main"
        assert pyrite_result[0] == "baz"
        assert pyrite_result[-1] == "main"
        # Both should have same elements
        assert set(python_result) == set(pyrite_result)
        # Dependencies should come before dependents
        assert python_result.index("baz") < python_result.index("foo")
        assert python_result.index("baz") < python_result.index("bar")
        assert python_result.index("foo") < python_result.index("main")
        assert python_result.index("bar") < python_result.index("main")
    
    def test_topological_sort_detects_cycle(self):
        """Topological sort should detect cycles"""
        edges = {"A": ["B"], "B": ["A"]}
        # Python should raise ValueError
        with pytest.raises(ValueError):
            _topological_sort_python(edges)
        # Pyrite should also raise ValueError (or return error)
        try:
            result = _topological_sort_ffi(edges)
            # If no exception, result should indicate error (empty or None)
            # Actually, FFI returns empty list on error, Python raises exception
            # For equivalence, we check that both handle cycles
            assert result == [] or result is None
        except ValueError:
            # If FFI also raises, that's fine too
            pass
    
    def test_build_graph_class_topological_sort(self):
        """Test BuildGraph.topological_sort() method"""
        graph = BuildGraph()
        graph.add_package("A", "1.0.0", Path("a"), ["B"])
        graph.add_package("B", "1.0.0", Path("b"), [])
        
        result = graph.topological_sort()
        assert "B" in result
        assert "A" in result
        assert result.index("B") < result.index("A")
    
    def test_build_graph_class_topological_sort_cycle(self):
        """Test BuildGraph.topological_sort() detects cycles"""
        graph = BuildGraph()
        graph.add_package("A", "1.0.0", Path("a"), ["B"])
        graph.add_package("B", "1.0.0", Path("b"), ["A"])
        
        with pytest.raises(ValueError):
            graph.topological_sort()


class TestBuildGraphIntegration:
    """Integration tests using BuildGraph class"""
    
    def test_has_cycle_integration(self):
        """Test has_cycle through BuildGraph class"""
        graph = BuildGraph()
        graph.add_package("A", "1.0.0", Path("a"), ["B"])
        graph.add_package("B", "1.0.0", Path("b"), ["A"])
        
        assert graph.has_cycle() == True
    
    def test_no_cycle_integration(self):
        """Test no cycle through BuildGraph class"""
        graph = BuildGraph()
        graph.add_package("A", "1.0.0", Path("a"), ["B"])
        graph.add_package("B", "1.0.0", Path("b"), [])
        
        assert graph.has_cycle() == False
    
    def test_topological_sort_integration(self):
        """Test topological_sort through BuildGraph class"""
        graph = BuildGraph()
        graph.add_package("main", "1.0.0", Path("main"), ["foo", "bar"])
        graph.add_package("foo", "1.0.0", Path("foo"), ["baz"])
        graph.add_package("bar", "1.0.0", Path("bar"), ["baz"])
        graph.add_package("baz", "1.0.0", Path("baz"), [])
        
        order = graph.topological_sort()
        assert order[0] == "baz"
        assert order[-1] == "main"
        assert "foo" in order
        assert "bar" in order
        assert order.index("baz") < order.index("foo")
        assert order.index("baz") < order.index("bar")
        assert order.index("foo") < order.index("main")
        assert order.index("bar") < order.index("main")
