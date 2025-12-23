import pytest
from src.middle import analyze_ownership
from src.frontend import lex, parse
from src.types import StructType, STRING

def test_partial_move():
    """Test partial move of struct fields (SPEC-LANG-0309)"""
    source = """struct Data:
    name: String
    id: int

fn test():
    let d = Data { name: "test", id: 1 }
    let n = d.name  # Partial move
    print(d.id)     # OK: id is still valid
"""
    tokens = lex(source)
    ast = parse(tokens)
    
    # Manually setup type environment
    data_type = StructType("Data", {"name": STRING, "id": 1}) # 1 is INT type width placeholder or similar
    # Actually, let's use the INT instance
    from src.types import INT
    data_type = StructType("Data", {"name": STRING, "id": INT})
    
    type_env = {"d": data_type}
    analyzer = analyze_ownership(ast, type_env)
    
    assert not analyzer.has_errors()

def test_use_after_partial_move():
    """Test error when using a partially moved field"""
    source = """struct Data:
    name: String
    id: int

fn test():
    let d = Data { name: "test", id: 1 }
    let n = d.name  # Partial move
    let n2 = d.name # Error: name already moved
"""
    tokens = lex(source)
    ast = parse(tokens)
    
    from src.types import INT
    data_type = StructType("Data", {"name": STRING, "id": INT})
    type_env = {"d": data_type}
    analyzer = analyze_ownership(ast, type_env)
    
    assert analyzer.has_errors()
    assert any("already moved field 'name'" in err.message for err in analyzer.errors)

def test_use_struct_after_partial_move():
    """Test error when using the whole struct after a partial move"""
    source = """struct Data:
    name: String
    id: int

fn test():
    let d = Data { name: "test", id: 1 }
    let n = d.name  # Partial move
    let d2 = d      # Error: d is partially moved
"""
    tokens = lex(source)
    ast = parse(tokens)
    
    from src.types import INT
    data_type = StructType("Data", {"name": STRING, "id": INT})
    type_env = {"d": data_type}
    analyzer = analyze_ownership(ast, type_env)
    
    assert analyzer.has_errors()
    assert any("partially moved fields" in err.message for err in analyzer.errors)

