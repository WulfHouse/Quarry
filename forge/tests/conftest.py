"""Pytest configuration and shared fixtures"""

import pytest
import sys
import os
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def temp_dir(tmp_path):
    """Deterministic temp directory for test file I/O"""
    return tmp_path


@pytest.fixture
def sample_source():
    """Small sample Pyrite source code for testing"""
    return "fn main() -> int:\n    return 42\n"


@pytest.fixture
def sample_tokens():
    """Pre-lexed tokens for parser tests"""
    from src.frontend import lex
    source = "fn main() -> int:\n    return 42\n"
    return lex(source, "<test>")


@pytest.fixture
def sample_ast():
    """Pre-parsed AST for type checker tests"""
    from src.frontend import lex
    from src.frontend import parse
    source = "fn main() -> int:\n    return 42\n"
    tokens = lex(source, "<test>")
    return parse(tokens)


@pytest.fixture
def repo_root():
    """Get the repository root directory"""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def compiler_dir(repo_root):
    """Get the forge directory"""
    return repo_root / "forge"


@pytest.fixture
def examples_dir(compiler_dir):
    """Get the examples directory"""
    return compiler_dir / "examples"

