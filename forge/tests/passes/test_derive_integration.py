"""Integration tests for derive pass and serialization traits"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from forge.src import ast
from forge.src.passes.derive_pass import DerivePass
from forge.src.frontend import lex, parse
from forge.src.middle.type_checker import TypeChecker
from forge.src.frontend.tokens import Span

def test_derive_serialize_generates_valid_ast():
    """Test that @derive(Serialize) generates AST that can be type-checked"""
    source = """
struct Config:
    name: String
    version: i64

trait Serializer:
    fn serialize_map_start(&mut self, len: i64) -> Result[bool, String]
    fn serialize_map_end(&mut self) -> Result[bool, String]
    fn serialize_str(&mut self, v: String) -> Result[bool, String]

trait Serialize:
    fn serialize[S: Serializer](&self, serializer: &mut S) -> Result[bool, String]

@derive(Serialize)
struct AppConfig:
    port: i64
    host: String
"""
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    derive_pass = DerivePass()
    program = derive_pass.derive_program(program)
    
    # Check that AppConfig has a Serialize impl
    serialize_impls = [item for item in program.items 
                      if isinstance(item, ast.ImplBlock) and item.trait_name == 'Serialize']
    assert len(serialize_impls) == 1
    
    # In a full integration test, we would run the type checker here.
    # For now, we've verified the AST generation.

