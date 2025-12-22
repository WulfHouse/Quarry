"""Tests for enhanced LSP hover functionality"""

import pytest

pytestmark = pytest.mark.slow  # All tests in this file are slow LSP tests

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lsp.server import PyriteLanguageServer, Position
from lsp.type_info import (
    get_type_badges, calculate_memory_layout,
    estimate_copy_cost, is_heap_allocated
)
from src.types import INT, F64, STRING, BOOL, ArrayType, GenericType


class TestLSPHoverEnhanced:
    """Test enhanced hover functionality"""
    
    def test_type_badges_int(self):
        """Test type badges for int"""
        badges = get_type_badges(INT)
        assert "[Stack]" in badges
        assert "[Copy]" in badges
        assert "[Heap]" not in badges
        assert "[Move]" not in badges
    
    def test_type_badges_string(self):
        """Test type badges for String"""
        badges = get_type_badges(STRING)
        assert "[Heap]" in badges
        assert "[Move]" in badges
        assert "[MayAlloc]" in badges
    
    def test_memory_layout_int(self):
        """Test memory layout for int"""
        stack_bytes, heap_bytes = calculate_memory_layout(INT)
        assert stack_bytes == 4  # 32-bit int
        assert heap_bytes == 0
    
    def test_memory_layout_string(self):
        """Test memory layout for String"""
        stack_bytes, heap_bytes = calculate_memory_layout(STRING)
        assert stack_bytes == 16  # { i8*, i64 }
        assert heap_bytes == 0  # Actual data size varies
    
    def test_memory_layout_array(self):
        """Test memory layout for array"""
        array_type = ArrayType(INT, 10)
        stack_bytes, heap_bytes = calculate_memory_layout(array_type)
        assert stack_bytes == 40  # 10 * 4 bytes
        assert heap_bytes == 0
    
    def test_memory_layout_list(self):
        """Test memory layout for List"""
        list_type = GenericType("List", base_type=None, type_args=[INT])
        stack_bytes, heap_bytes = calculate_memory_layout(list_type)
        assert stack_bytes == 24  # { T*, i64, i64 }
        assert heap_bytes == 0  # Actual elements size varies
    
    def test_copy_cost_int(self):
        """Test copy cost for int"""
        cost = estimate_copy_cost(INT)
        assert "O(1)" in cost
        assert "register" in cost or "copy" in cost
    
    def test_copy_cost_string(self):
        """Test copy cost for String"""
        cost = estimate_copy_cost(STRING)
        assert "O(n)" in cost or "deep copy" in cost
    
    def test_is_heap_allocated(self):
        """Test heap allocation detection"""
        assert not is_heap_allocated(INT)
        assert not is_heap_allocated(F64)
        assert not is_heap_allocated(BOOL)
        assert is_heap_allocated(STRING)
        
        list_type = GenericType("List", base_type=None, type_args=[INT])
        assert is_heap_allocated(list_type)
    
    def test_hover_with_type_info(self):
        """Test hover with comprehensive type information"""
        server = PyriteLanguageServer()
        
        # Create symbol info with type object
        from src.types import INT
        symbol_info = {
            'name': 'x',
            'type': 'int',
            'type_obj': INT,
            'kind': 'variable',
            'ownership_state': None
        }
        
        content = server._format_hover_content(symbol_info)
        
        # Should include type
        assert 'x: int' in content
        
        # Should include badges
        assert '[Stack]' in content or '[Copy]' in content
        
        # Should include memory info
        assert 'Stack' in content or 'Memory' in content
    
    def test_hover_with_ownership_state(self):
        """Test hover with ownership state"""
        server = PyriteLanguageServer()
        
        # Create mock ownership state
        from src.middle import OwnershipState
        from src.types import INT
        from src.frontend.tokens import Span
        
        ownership_state = OwnershipState()
        ownership_state.allocate('x', INT, Span(0, 0, 0, 0, '<test>'))
        
        symbol_info = {
            'name': 'x',
            'type': 'int',
            'type_obj': INT,
            'kind': 'variable',
            'ownership_state': ownership_state
        }
        
        content = server._format_hover_content(symbol_info)
        
        # Should include ownership info
        assert 'Ownership' in content or 'Owned' in content
    
    def test_hover_with_moved_state(self):
        """Test hover with moved ownership state"""
        server = PyriteLanguageServer()
        
        from src.middle import OwnershipState
        from src.types import GenericType
        from src.frontend.tokens import Span
        
        ownership_state = OwnershipState()
        list_type = GenericType("List", base_type=None, type_args=[INT])
        ownership_state.allocate('data', list_type, Span(0, 0, 0, 0, '<test>'))
        ownership_state.move_value('data', 'other', Span(1, 0, 1, 0, '<test>'))
        
        symbol_info = {
            'name': 'data',
            'type': 'List[int]',
            'type_obj': list_type,
            'kind': 'variable',
            'ownership_state': ownership_state
        }
        
        content = server._format_hover_content(symbol_info)
        
        # Should indicate moved state
        assert 'Moved' in content or 'moved' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

