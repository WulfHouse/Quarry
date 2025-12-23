import os
import tempfile
from pathlib import Path
from quarry.main import cmd_build

def test_quarry_build_lib():
    """Test building a library project (SPEC-QUARRY-0020)"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        original_cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            # Create lib project
            os.makedirs("src")
            with open("Quarry.toml", "w") as f:
                f.write('[package]\nname = "mylib"\nversion = "0.1.0"\n\n[lib]\n')
            with open("src/lib.pyrite", "w") as f:
                f.write('fn add(a: int, b: int) -> int:\n    return a + b\n')
            
            # Run build
            result = cmd_build()
            assert result == 0
            
            # Check artifact
            assert os.path.exists("target/debug/libmylib.a")
        finally:
            os.chdir(original_cwd)

