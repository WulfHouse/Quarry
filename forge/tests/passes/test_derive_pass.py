"""Tests for derive pass (SPEC-LANG-0841)"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from forge.src import ast
from forge.src.passes.derive_pass import DerivePass
from forge.src.frontend import lex, parse
from forge.src.frontend.tokens import Span, TokenType


def test_derive_pass_detects_derive_attribute():
    """Test that derive pass detects @derive attributes on structs"""
    source = """@derive(Serialize, Deserialize)
struct Config:
    name: String
    value: int
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    derive_pass = DerivePass()
    result = derive_pass.derive_program(program)
    
    # Should have original struct plus 2 impl blocks (Serialize and Deserialize)
    structs = [item for item in result.items if isinstance(item, ast.StructDef) and item.name == 'Config']
    assert len(structs) == 1, "Should have Config struct"
    
    impls = [item for item in result.items if isinstance(item, ast.ImplBlock) and item.trait_name]
    assert len(impls) >= 2, "Should have at least 2 impl blocks generated"


def test_derive_pass_ignores_structs_without_derive():
    """Test that derive pass ignores structs without @derive attribute"""
    source = """struct Config:
    name: String
    value: int
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    derive_pass = DerivePass()
    result = derive_pass.derive_program(program)
    
    # Should have original struct but no impl blocks
    structs = [item for item in result.items if isinstance(item, ast.StructDef) and item.name == 'Config']
    assert len(structs) == 1, "Should have Config struct"
    
    impls = [item for item in result.items if isinstance(item, ast.ImplBlock) and item.trait_name]
    assert len(impls) == 0, "Should not have any impl blocks for struct without @derive"


def test_derive_pass_generates_serialize_impl():
    """Test that derive pass generates Serialize impl block"""
    source = """@derive(Serialize)
struct Config:
    name: String
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    derive_pass = DerivePass()
    result = derive_pass.derive_program(program)
    
    # Find Serialize impl block
    serialize_impls = [item for item in result.items 
                      if isinstance(item, ast.ImplBlock) and item.trait_name == 'Serialize']
    assert len(serialize_impls) == 1, "Should have one Serialize impl block"
    
    impl = serialize_impls[0]
    assert impl.type_name == "Config", "Impl should be for Config"
    assert len(impl.methods) > 0, "Impl should have at least one method"


def test_derive_pass_generates_deserialize_impl():
    """Test that derive pass generates Deserialize impl block"""
    source = """@derive(Deserialize)
struct Config:
    name: String
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    derive_pass = DerivePass()
    result = derive_pass.derive_program(program)
    
    # Find Deserialize impl block
    deserialize_impls = [item for item in result.items 
                        if isinstance(item, ast.ImplBlock) and item.trait_name == 'Deserialize']
    assert len(deserialize_impls) == 1, "Should have one Deserialize impl block"
    
    impl = deserialize_impls[0]
    assert impl.type_name == "Config", "Impl should be for Config"
    assert len(impl.methods) > 0, "Impl should have at least one method"

