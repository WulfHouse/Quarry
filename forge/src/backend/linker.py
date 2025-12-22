"""Linker for Pyrite - creates executables from LLVM IR"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Optional


class LinkerError(Exception):
    """Linking error"""
    pass


def find_clang() -> Optional[str]:
    """Find clang compiler on system"""
    # Try common locations
    clang_names = ['clang', 'clang-15', 'clang-14', 'clang-13']
    
    for name in clang_names:
        try:
            result = subprocess.run([name, '--version'], 
                                  capture_output=True, 
                                  text=True,
                                  timeout=5)
            if result.returncode == 0:
                return name
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    
    return None


def find_gcc() -> Optional[str]:
    """Find gcc compiler on system"""
    try:
        result = subprocess.run(['gcc', '--version'], 
                              capture_output=True, 
                              text=True,
                              timeout=5)
        if result.returncode == 0:
            return 'gcc'
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return None


def link_llvm_ir(llvm_ir_path: str, output_path: str, stdlib_paths: list = None) -> bool:
    """Link LLVM IR to executable"""
    
    if stdlib_paths is None:
        stdlib_paths = []
    
    # Find clang (preferred) or gcc
    clang = find_clang()
    gcc = find_gcc()
    
    if not clang and not gcc:
        print("Warning: No C compiler found (clang or gcc required).")
        print("Please install LLVM/clang or GCC to create executables.")
        print(f"LLVM IR generated: {llvm_ir_path}")
        print(f"To compile manually: clang {llvm_ir_path} -o {output_path}")
        return False
    
    compiler = clang if clang else gcc
    
    # Compile with clang (can handle LLVM IR directly) or gcc
    if clang:
        cmd = [clang, llvm_ir_path, '-o', output_path, '-Wno-override-module']
    else:
        # GCC can also compile LLVM IR
        cmd = [gcc, llvm_ir_path, '-o', output_path]
    
    # Add stdlib paths if provided
    for lib_path in stdlib_paths:
        cmd.append(lib_path)
    
    # Add math library
    if sys.platform != 'win32':
        cmd.append('-lm')
    
    try:
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              text=True,
                              timeout=30)
        
        if result.returncode != 0:
            # Check if it's just warnings
            if 'error:' in result.stderr.lower():
                print(f"Linking failed:")
                print(result.stderr)
                return False
            # Just warnings, probably worked
        
        # Check if executable was created
        if os.path.exists(output_path) or os.path.exists(output_path + '.exe'):
            print(f"[OK] Linked executable: {output_path}")
            return True
        else:
            print(f"Linking failed - executable not created")
            return False
    
    except subprocess.SubprocessError as e:
        print(f"Linking error: {e}")
        return False


def compile_stdlib_c(stdlib_dir: Path) -> list:
    """Compile C standard library files to object files"""
    object_files = []
    compiler = find_clang() or find_gcc()
    
    if not compiler:
        return []
    
    # Find all .c files in stdlib
    c_files = list(stdlib_dir.rglob("*.c"))
    
    for c_file in c_files:
        # Compile to object file
        obj_file = c_file.with_suffix('.o')
        
        cmd = [compiler, '-c', str(c_file), '-o', str(obj_file), '-O2']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                object_files.append(str(obj_file))
            else:
                print(f"Warning: Failed to compile {c_file}")
        except subprocess.SubprocessError:
            print(f"Warning: Error compiling {c_file}")
    
    return object_files


def link_object_files(object_files: list, output_path: str) -> bool:
    """Link object files to executable - prefers Clang, falls back to GCC"""
    
    # Find clang (preferred) or gcc - same logic as link_llvm_ir
    clang = find_clang()
    gcc = find_gcc()
    
    if not clang and not gcc:
        print("Warning: No C compiler found (clang or gcc required for linking).")
        print("Please install LLVM/clang or GCC to create executables.")
        return False
    
    compiler = clang if clang else gcc
    
    # Link with the chosen compiler
    cmd = [compiler] + object_files + ['-o', output_path]
    
    # On Windows, if using Clang with MSVC target, we may need additional flags
    # But for now, let's try without extra flags first
    
    # Add math library on Unix
    if sys.platform != 'win32':
        cmd.append('-lm')
    
    try:
        result = subprocess.run(cmd, 
                              capture_output=True, 
                              text=True,
                              timeout=30)
        
        if result.returncode != 0:
            print(f"Linking failed:")
            print(result.stderr)
            if result.stdout:
                print(result.stdout)
            return False
        
        # Check if executable was created
        if os.path.exists(output_path) or os.path.exists(output_path + '.exe'):
            return True
        else:
            print(f"Linking failed - executable not created")
            return False
    
    except subprocess.SubprocessError as e:
        print(f"Linking error: {e}")
        return False


def link_with_stdlib(llvm_ir_path: str, output_path: str) -> bool:
    """Link LLVM IR with compiled standard library"""
    
    # Get runtime directory
    compiler_root = Path(__file__).parent.parent
    runtime_dir = compiler_root / 'runtime'
    
    # Check if runtime objects exist
    if runtime_dir.exists():
        object_files = list(runtime_dir.glob("*.o"))
        if object_files:
            print(f"  Linking with {len(object_files)} runtime modules")
            return link_llvm_ir(llvm_ir_path, output_path, [str(f) for f in object_files])
    
    # No runtime objects, link without them
    return link_llvm_ir(llvm_ir_path, output_path, [])

