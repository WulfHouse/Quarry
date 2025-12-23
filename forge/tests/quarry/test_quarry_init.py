import os
import shutil
import tempfile
from pathlib import Path
from quarry.main import cmd_init

def test_quarry_init():
    """Test quarry init (SPEC-QUARRY-0013)"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        original_cwd = os.getcwd()
        os.chdir(tmp_dir)
        try:
            # Run init
            result = cmd_init()
            assert result == 0
            
            # Check structure
            assert os.path.exists("Quarry.toml")
            assert os.path.exists("src/main.pyrite")
            assert os.path.exists(".gitignore")
            assert os.path.isdir("tests")
            
            # Check contents
            with open("Quarry.toml", "r") as f:
                content = f.read()
                assert 'name = "' in content
                assert 'version = "0.1.0"' in content
        finally:
            os.chdir(original_cwd)

