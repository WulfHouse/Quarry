"""Type information utilities for LSP hover"""

from typing import List, Tuple, Optional, Dict
from src.types import (
    Type, IntType, FloatType, BoolType, CharType, StringType,
    ReferenceType, PointerType, ArrayType, SliceType, StructType,
    GenericType, is_copy_type
)


def get_type_badges(typ: Type) -> List[str]:
    """Get type badges for hover display"""
    badges = []
    
    # Stack vs Heap
    if is_heap_allocated(typ):
        badges.append("[Heap]")
    else:
        badges.append("[Stack]")
    
    # Copy vs Move
    if is_copy_type(typ):
        badges.append("[Copy]")
    else:
        badges.append("[Move]")
    
    # MayAlloc (for types that can allocate)
    if may_allocate(typ):
        badges.append("[MayAlloc]")
    
    return badges


def is_heap_allocated(typ: Type) -> bool:
    """Check if type is heap-allocated"""
    # Generic types (List, Map, Set, String) are heap-allocated
    if isinstance(typ, GenericType):
        return True
    
    # String is heap-allocated
    if isinstance(typ, StringType):
        return True
    
    # References and pointers point to heap or stack, but themselves are stack
    if isinstance(typ, (ReferenceType, PointerType)):
        return False
    
    # Arrays and structs are stack-allocated (unless they contain heap types)
    if isinstance(typ, (ArrayType, StructType)):
        return False
    
    # Primitives are stack-allocated
    return False


def may_allocate(typ: Type) -> bool:
    """Check if type may allocate memory"""
    # Generic types may allocate when growing
    if isinstance(typ, GenericType):
        return True
    
    # String may allocate when modified
    if isinstance(typ, StringType):
        return True
    
    return False


def calculate_memory_layout(typ: Type) -> Tuple[int, int]:
    """Calculate stack and heap bytes for a type
    
    Returns:
        (stack_bytes, heap_bytes) tuple
    """
    stack_bytes = 0
    heap_bytes = 0
    
    if isinstance(typ, IntType):
        stack_bytes = typ.width // 8  # Convert bits to bytes
    elif isinstance(typ, FloatType):
        stack_bytes = typ.width // 8
    elif isinstance(typ, BoolType):
        stack_bytes = 1
    elif isinstance(typ, CharType):
        stack_bytes = 4  # Unicode code point
    elif isinstance(typ, StringType):
        stack_bytes = 16  # { i8*, i64 } - pointer + length
        heap_bytes = 0  # Actual string data is heap, but size varies
    elif isinstance(typ, ReferenceType):
        stack_bytes = 8  # Pointer on 64-bit
    elif isinstance(typ, PointerType):
        stack_bytes = 8  # Pointer on 64-bit
    elif isinstance(typ, ArrayType):
        elem_stack, elem_heap = calculate_memory_layout(typ.element)
        stack_bytes = typ.size * elem_stack
        heap_bytes = typ.size * elem_heap
    elif isinstance(typ, SliceType):
        stack_bytes = 16  # { T*, i64 } - pointer + length
    elif isinstance(typ, GenericType):
        # Generic types have a stack handle
        if typ.name == "List":
            stack_bytes = 24  # { T*, i64, i64 } - pointer, len, cap
            heap_bytes = 0  # Actual elements are heap, but size varies
        elif typ.name == "Map":
            stack_bytes = 24  # Similar structure
            heap_bytes = 0
        elif typ.name == "Set":
            stack_bytes = 24
            heap_bytes = 0
        else:
            stack_bytes = 8  # Default: pointer
    elif isinstance(typ, StructType):
        # Sum of field sizes
        for field_type in typ.fields.values():
            field_stack, field_heap = calculate_memory_layout(field_type)
            stack_bytes += field_stack
            heap_bytes += field_heap
    
    return (stack_bytes, heap_bytes)


def estimate_copy_cost(typ: Type) -> str:
    """Estimate copy cost for a type"""
    if is_copy_type(typ):
        stack_bytes, _ = calculate_memory_layout(typ)
        if stack_bytes <= 8:
            return "O(1) - register copy"
        elif stack_bytes <= 64:
            return "O(1) - small stack copy"
        else:
            return f"O(1) - {stack_bytes}B copy"
    else:
        return "O(n) - deep copy required"


def get_ownership_state_info(var_name: str, ownership_state) -> Dict:
    """Get ownership state information for a variable"""
    if not ownership_state:
        return {
            'state': 'unknown',
            'moved_to': None,
            'is_owned': False
        }
    
    value_info = ownership_state.get_value_info(var_name)
    if not value_info:
        return {
            'state': 'unknown',
            'moved_to': None,
            'is_owned': False
        }
    
    is_owned = ownership_state.is_owned_by_name(var_name)
    
    if not is_owned:
        return {
            'state': 'moved',
            'moved_to': value_info.moved_to,
            'is_owned': False
        }
    else:
        return {
            'state': 'owned',
            'moved_to': None,
            'is_owned': True
        }


def generate_next_risks(typ: Type, ownership_info: Dict, var_name: str) -> List[str]:
    """Generate "next risks" warnings for hover"""
    risks = []
    
    # Check if passing will move
    if not is_copy_type(typ) and ownership_info.get('is_owned', False):
        risks.append(f"⚠️ Passing `{var_name}` will move (use `&{var_name}` to borrow)")
    
    # Check if already moved
    if ownership_info.get('state') == 'moved':
        moved_to = ownership_info.get('moved_to')
        if moved_to:
            risks.append(f"⚠️ Value moved to `{moved_to}`")
        else:
            risks.append("⚠️ Value has been moved")
    
    # Check for large stack allocation
    stack_bytes, _ = calculate_memory_layout(typ)
    if stack_bytes > 1024:  # 1KB
        risks.append(f"⚠️ Large stack allocation ({stack_bytes}B) - consider heap allocation")
    
    # Check for heap allocation
    if is_heap_allocated(typ):
        risks.append("⚠️ Heap-allocated - may allocate on growth")
    
    return risks

