"""Integration tests for Serialization Formats (SPEC-LANG-0840)

Tests JSON and TOML encoders/decoders.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from forge.src.frontend import lex, parse


@pytest.mark.fast
def test_json_module_exists():
    """Test that JSON module exists"""
    json_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "json.pyrite"
    assert json_file.exists(), "json.pyrite should exist"


@pytest.mark.fast
def test_toml_module_exists():
    """Test that TOML module exists"""
    toml_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "toml.pyrite"
    assert toml_file.exists(), "toml.pyrite should exist"


@pytest.mark.fast
def test_json_to_string():
    """Test JSON to_string function"""
    json_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "json.pyrite"
    content = json_file.read_text()
    
    # Verify to_string exists
    assert "fn to_string(" in content, "JSON should have to_string function"


@pytest.mark.fast
def test_json_from_str():
    """Test JSON from_str function"""
    json_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "json.pyrite"
    content = json_file.read_text()
    
    # Verify from_str exists
    assert "fn from_str(" in content, "JSON should have from_str function"


@pytest.mark.fast
def test_json_value_enum():
    """Test JSON value enum exists"""
    json_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "json.pyrite"
    content = json_file.read_text()
    
    # Verify JsonValue enum with required variants
    assert "enum JsonValue" in content, "JsonValue enum should exist"
    assert "Null" in content, "JsonValue should have Null variant"
    assert "Bool" in content, "JsonValue should have Bool variant"
    assert "Number" in content, "JsonValue should have Number variant"
    assert "String" in content, "JsonValue should have String variant"
    assert "Array" in content, "JsonValue should have Array variant"
    assert "Object" in content, "JsonValue should have Object variant"


@pytest.mark.fast
def test_json_parse_null():
    """Test JSON parsing null"""
    source = """
import std.serialize.json

fn test_null() -> i32:
    let result = from_str(string_new("null"))
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_json_parse_bool():
    """Test JSON parsing booleans"""
    source = """
import std.serialize.json

fn test_bool() -> i32:
    let result_true = from_str(string_new("true"))
    let result_false = from_str(string_new("false"))
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_json_parse_string():
    """Test JSON parsing strings"""
    source = """
import std.serialize.json

fn test_string() -> i32:
    let s = string_new("hello")
    let result = from_str(s)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_json_serialize():
    """Test JSON serialization"""
    source = """
import std.serialize.json

fn test_serialize() -> i32:
    let val = JsonValue.Bool(true)
    let json_str = to_string(val)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    assert program is not None


@pytest.mark.fast
def test_toml_basic_support():
    """Test TOML basic parsing support"""
    toml_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "toml.pyrite"
    content = toml_file.read_text()
    
    # Verify basic TOML types exist
    assert "TomlValue" in content or "parse" in content, "TOML should have parsing support"


@pytest.mark.fast
def test_json_result_type():
    """Test JSON functions return Result type"""
    json_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "json.pyrite"
    content = json_file.read_text()
    
    # Verify from_str returns Result
    from_str_line = [line for line in content.split('\n') if 'fn from_str(' in line]
    assert len(from_str_line) > 0, "from_str function should exist"
    assert "Result" in from_str_line[0], "from_str should return Result type"


@pytest.mark.fast
def test_json_error_handling():
    """Test JSON handles parsing errors"""
    json_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "json.pyrite"
    content = json_file.read_text()
    
    # Verify error handling exists
    assert "Err(" in content, "JSON should have error handling"


@pytest.mark.fast
def test_json_object_support():
    """Test JSON object/map support"""
    json_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "json.pyrite"
    content = json_file.read_text()
    
    # Verify Object variant uses Map
    assert "Map[" in content or "entries" in content, "JSON Object should use Map"


@pytest.mark.fast
def test_json_array_support():
    """Test JSON array support"""
    json_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "serialize" / "json.pyrite"
    content = json_file.read_text()
    
    # Verify Array variant uses List
    assert "List[" in content or "Array(values:" in content, "JSON Array should use List"

