"""Tests for linker.py"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
import subprocess
import sys
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from io import StringIO

from src.backend import (
    LinkerError, find_clang, find_gcc,
    link_llvm_ir, link_object_files, link_with_stdlib, compile_stdlib_c
)


def test_linker_error():
    """Test LinkerError exception"""
    error = LinkerError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_find_clang_success():
    """Test find_clang() when clang is available"""
    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = find_clang()
        assert result is not None
        assert result in ['clang', 'clang-15', 'clang-14', 'clang-13']


def test_find_clang_not_found():
    """Test find_clang() when clang is not available"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError()
        
        result = find_clang()
        assert result is None


def test_find_clang_timeout():
    """Test find_clang() handles timeout"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired('clang', 5)
        
        result = find_clang()
        # Should continue trying other names or return None
        assert isinstance(result, (str, type(None)))


def test_find_clang_nonzero_exit():
    """Test find_clang() when clang returns non-zero exit code"""
    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 1  # Error
        mock_run.return_value = mock_result
        
        # Should try next name or return None
        result = find_clang()
        # May return None if all fail, or a name if one succeeds
        assert isinstance(result, (str, type(None)))


def test_find_gcc_success():
    """Test find_gcc() when gcc is available"""
    with patch('subprocess.run') as mock_run:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = find_gcc()
        assert result == 'gcc'


def test_find_gcc_not_found():
    """Test find_gcc() when gcc is not available"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError()
        
        result = find_gcc()
        assert result is None


def test_find_gcc_timeout():
    """Test find_gcc() handles timeout"""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired('gcc', 5)
        
        result = find_gcc()
        assert result is None


def test_link_llvm_ir_no_compiler():
    """Test link_llvm_ir() when no compiler is found"""
    with patch('src.backend.linker.find_clang', return_value=None):
        with patch('src.backend.linker.find_gcc', return_value=None):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                result = link_llvm_ir("test.ll", "test.out")
                assert result == False
                output = mock_stdout.getvalue()
                assert "No C compiler found" in output or "Warning" in output


def test_link_llvm_ir_with_clang():
    """Test link_llvm_ir() with clang"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
        f.write(b"define i32 @main() { ret i32 42 }")
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('src.backend.linker.find_gcc', return_value=None):
                with patch('subprocess.run') as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    
                    with patch('os.path.exists', return_value=True):
                        result = link_llvm_ir(llvm_ir_path, output_path)
                        assert isinstance(result, bool)
                        mock_run.assert_called_once()
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_llvm_ir_with_gcc():
    """Test link_llvm_ir() with gcc"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value=None):
            with patch('src.backend.linker.find_gcc', return_value='gcc'):
                with patch('subprocess.run') as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    
                    with patch('os.path.exists', return_value=True):
                        result = link_llvm_ir(llvm_ir_path, output_path)
                        assert isinstance(result, bool)
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_llvm_ir_with_stdlib_paths():
    """Test link_llvm_ir() with stdlib paths"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result
                
                with patch('os.path.exists', return_value=True):
                    stdlib_paths = ["lib1.o", "lib2.o"]
                    result = link_llvm_ir(llvm_ir_path, output_path, stdlib_paths)
                    assert isinstance(result, bool)
                    # Verify stdlib paths were added to command
                    call_args = mock_run.call_args[0][0]
                    assert "lib1.o" in call_args or "lib2.o" in call_args
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_llvm_ir_with_math_library():
    """Test link_llvm_ir() adds math library on non-Windows"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('sys.platform', 'linux'):
                with patch('subprocess.run') as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    
                    with patch('os.path.exists', return_value=True):
                        result = link_llvm_ir(llvm_ir_path, output_path)
                        assert isinstance(result, bool)
                        # Verify -lm was added on non-Windows
                        call_args = mock_run.call_args[0][0]
                        assert '-lm' in call_args
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_llvm_ir_link_failure():
    """Test link_llvm_ir() when linking fails"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "error: linking failed"
                mock_run.return_value = mock_result
                
                with patch('sys.stdout', new=StringIO()) as mock_stdout:
                    result = link_llvm_ir(llvm_ir_path, output_path)
                    assert result == False
                    output = mock_stdout.getvalue()
                    assert "Linking failed" in output or "error" in output.lower()
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_llvm_ir_executable_not_created():
    """Test link_llvm_ir() when executable is not created"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result
                
                with patch('os.path.exists', return_value=False):
                    with patch('sys.stdout', new=StringIO()) as mock_stdout:
                        result = link_llvm_ir(llvm_ir_path, output_path)
                        assert result == False
                        output = mock_stdout.getvalue()
                        assert "not created" in output.lower() or "failed" in output.lower()
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_llvm_ir_subprocess_error():
    """Test link_llvm_ir() handles subprocess errors"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.SubprocessError("Test error")
                
                with patch('sys.stdout', new=StringIO()) as mock_stdout:
                    result = link_llvm_ir(llvm_ir_path, output_path)
                    assert result == False
                    output = mock_stdout.getvalue()
                    assert "error" in output.lower() or "Error" in output
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_compile_stdlib_c_no_compiler():
    """Test compile_stdlib_c() when no compiler is found"""
    stdlib_dir = Path("test_stdlib")
    
    with patch('src.backend.linker.find_clang', return_value=None):
        with patch('src.backend.linker.find_gcc', return_value=None):
            result = compile_stdlib_c(stdlib_dir)
            assert result == []


def test_compile_stdlib_c_no_c_files():
    """Test compile_stdlib_c() when no .c files exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        stdlib_dir = Path(tmpdir)
        
        with patch('src.backend.linker.find_clang', return_value='clang'):
            result = compile_stdlib_c(stdlib_dir)
            assert result == []


def test_compile_stdlib_c_with_files():
    """Test compile_stdlib_c() with .c files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        stdlib_dir = Path(tmpdir)
        
        # Create a test .c file
        test_c = stdlib_dir / "test.c"
        test_c.write_text("int test() { return 42; }")
        
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result
                
                result = compile_stdlib_c(stdlib_dir)
                assert isinstance(result, list)
                mock_run.assert_called()


def test_compile_stdlib_c_compilation_failure():
    """Test compile_stdlib_c() when compilation fails"""
    with tempfile.TemporaryDirectory() as tmpdir:
        stdlib_dir = Path(tmpdir)
        
        test_c = stdlib_dir / "test.c"
        test_c.write_text("invalid c code")
        
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 1  # Compilation failed
                mock_run.return_value = mock_result
                
                with patch('sys.stdout', new=StringIO()) as mock_stdout:
                    result = compile_stdlib_c(stdlib_dir)
                    # Should continue and return list (may be empty)
                    assert isinstance(result, list)


def test_link_object_files_no_compiler():
    """Test link_object_files() when no compiler is found"""
    with patch('src.backend.linker.find_clang', return_value=None):
        with patch('src.backend.linker.find_gcc', return_value=None):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                result = link_object_files(["test.o"], "test.out")
                assert result == False
                output = mock_stdout.getvalue()
                assert "No C compiler found" in output or "Warning" in output


def test_link_object_files_success():
    """Test link_object_files() successful linking"""
    with tempfile.NamedTemporaryFile(suffix='.o', delete=False) as f:
        obj_file = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('src.backend.linker.find_gcc', return_value=None):
                with patch('subprocess.run') as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    
                    with patch('os.path.exists', return_value=True):
                        result = link_object_files([obj_file], output_path)
                        assert result == True
                        # May be called multiple times (for find_gcc check, then linking)
                        assert mock_run.call_count >= 1
    finally:
        if os.path.exists(obj_file):
            os.unlink(obj_file)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_object_files_failure():
    """Test link_object_files() when linking fails"""
    with tempfile.NamedTemporaryFile(suffix='.o', delete=False) as f:
        obj_file = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "linking error"
                mock_result.stdout = "stdout"
                mock_run.return_value = mock_result
                
                with patch('sys.stdout', new=StringIO()) as mock_stdout:
                    result = link_object_files([obj_file], output_path)
                    assert result == False
                    output = mock_stdout.getvalue()
                    assert "Linking failed" in output or "error" in output.lower()
    finally:
        if os.path.exists(obj_file):
            os.unlink(obj_file)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_object_files_executable_not_created():
    """Test link_object_files() when executable is not created"""
    with tempfile.NamedTemporaryFile(suffix='.o', delete=False) as f:
        obj_file = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result
                
                with patch('os.path.exists', return_value=False):
                    with patch('sys.stdout', new=StringIO()) as mock_stdout:
                        result = link_object_files([obj_file], output_path)
                        assert result == False
    finally:
        if os.path.exists(obj_file):
            os.unlink(obj_file)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_object_files_subprocess_error():
    """Test link_object_files() handles subprocess errors"""
    with tempfile.NamedTemporaryFile(suffix='.o', delete=False) as f:
        obj_file = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.SubprocessError("Test error")
                
                with patch('sys.stdout', new=StringIO()) as mock_stdout:
                    result = link_object_files([obj_file], output_path)
                    assert result == False
    finally:
        if os.path.exists(obj_file):
            os.unlink(obj_file)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_with_stdlib_with_runtime():
    """Test link_with_stdlib() when runtime objects exist"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir)
            runtime_obj = runtime_dir / "test.o"
            runtime_obj.write_bytes(b"object file")
            
            with patch('src.backend.linker.Path') as mock_path:
                mock_path.return_value.parent.parent.__truediv__.return_value = runtime_dir
                with patch('src.backend.linker.link_llvm_ir', return_value=True) as mock_link:
                    result = link_with_stdlib(llvm_ir_path, output_path)
                    assert result == True
                    mock_link.assert_called_once()
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_with_stdlib_no_runtime():
    """Test link_with_stdlib() when no runtime objects exist"""
    with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as f:
        llvm_ir_path = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            runtime_dir = Path(tmpdir)
            # No .o files in runtime directory
            
            with patch('src.backend.linker.Path') as mock_path:
                mock_path.return_value.parent.parent.__truediv__.return_value = runtime_dir
                with patch('src.backend.linker.link_llvm_ir', return_value=True) as mock_link:
                    result = link_with_stdlib(llvm_ir_path, output_path)
                    assert result == True
                    mock_link.assert_called_once()
                    # Should be called with empty stdlib_paths
                    call_args = mock_link.call_args[0]
                    assert len(call_args) >= 3
                    assert call_args[2] == []  # stdlib_paths should be empty
    finally:
        if os.path.exists(llvm_ir_path):
            os.unlink(llvm_ir_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_link_object_files_windows_exe():
    """Test link_object_files() handles .exe extension on Windows"""
    with tempfile.NamedTemporaryFile(suffix='.o', delete=False) as f:
        obj_file = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('src.backend.linker.find_gcc', return_value=None):
                with patch('subprocess.run') as mock_run:
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_run.return_value = mock_result
                    
                    # Check for .exe on Windows
                    with patch('os.path.exists') as mock_exists:
                        def exists_side_effect(path):
                            return path == output_path + '.exe'
                        mock_exists.side_effect = exists_side_effect
                        
                        result = link_object_files([obj_file], output_path)
                        assert result == True
    finally:
        if os.path.exists(obj_file):
            os.unlink(obj_file)
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_compile_stdlib_c_subprocess_error():
    """Test compile_stdlib_c() handles subprocess errors"""
    with tempfile.TemporaryDirectory() as tmpdir:
        stdlib_dir = Path(tmpdir)
        
        test_c = stdlib_dir / "test.c"
        test_c.write_text("int test() { return 42; }")
        
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = subprocess.SubprocessError("Test error")
                
                with patch('sys.stdout', new=StringIO()) as mock_stdout:
                    result = compile_stdlib_c(stdlib_dir)
                    assert isinstance(result, list)
                    # Should handle error gracefully


def test_link_object_files_with_math_library():
    """Test link_object_files() adds math library on non-Windows"""
    with tempfile.NamedTemporaryFile(suffix='.o', delete=False) as f:
        obj_file = f.name
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        output_path = f.name
    
    try:
        with patch('src.backend.linker.find_clang', return_value='clang'):
            with patch('src.backend.linker.find_gcc', return_value=None):
                with patch('sys.platform', 'linux'):
                    with patch('subprocess.run') as mock_run:
                        mock_result = MagicMock()
                        mock_result.returncode = 0
                        mock_run.return_value = mock_result
                        
                        with patch('os.path.exists', return_value=True):
                            result = link_object_files([obj_file], output_path)
                            assert result == True
                            # Verify -lm was added on non-Windows
                            call_args = mock_run.call_args[0][0]
                            assert '-lm' in call_args
    finally:
        if os.path.exists(obj_file):
            os.unlink(obj_file)
        if os.path.exists(output_path):
            os.unlink(output_path)
