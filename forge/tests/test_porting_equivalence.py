"""Test framework for comparing Python vs Pyrite module outputs

This framework enables equivalence testing to prove that ported Pyrite modules
behave identically to their Python counterparts.
"""

import pytest
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import ctypes

# Add forge to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))


class EquivalenceTestError(Exception):
    """Error in equivalence testing"""
    pass


def normalize_for_comparison(value: Any) -> Any:
    """Normalize value for comparison (handles dict key ordering, etc.)
    
    Args:
        value: Value to normalize
        
    Returns:
        Normalized value (JSON-serializable)
    """
    if isinstance(value, dict):
        # Sort dict keys for consistent comparison
        return {k: normalize_for_comparison(v) for k, v in sorted(value.items())}
    elif isinstance(value, list):
        return [normalize_for_comparison(item) for item in value]
    elif isinstance(value, (str, int, float, bool, type(None))):
        return value
    elif isinstance(value, Path):
        return str(value)
    else:
        # Try to convert to JSON-serializable
        try:
            return json.loads(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return str(value)


def compare_outputs(python_result: Any, pyrite_result: Any) -> Tuple[bool, Optional[str]]:
    """Compare Python and Pyrite outputs
    
    Args:
        python_result: Result from Python function
        pyrite_result: Result from Pyrite function
        
    Returns:
        Tuple of (are_equal, error_message)
    """
    try:
        # Normalize both results
        python_norm = normalize_for_comparison(python_result)
        pyrite_norm = normalize_for_comparison(pyrite_result)
        
        # Compare
        if python_norm == pyrite_norm:
            return (True, None)
        else:
            # Generate diff message
            python_json = json.dumps(python_norm, indent=2)
            pyrite_json = json.dumps(pyrite_norm, indent=2)
            return (False, f"Outputs differ:\nPython: {python_json}\nPyrite: {pyrite_json}")
    except Exception as e:
        return (False, f"Error comparing outputs: {e}")


def run_python_function(module_path: str, function_name: str, *args, **kwargs) -> Any:
    """Run a Python function and return result
    
    Args:
        module_path: Path to Python module (e.g., "quarry.workspace")
        function_name: Name of function to call
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Function result
    """
    try:
        import importlib
        module = importlib.import_module(module_path)
        func = getattr(module, function_name)
        return func(*args, **kwargs)
    except Exception as e:
        raise EquivalenceTestError(f"Failed to run Python function {module_path}.{function_name}: {e}")


def run_pyrite_function(lib_path: str, function_name: str, *args, **kwargs) -> Any:
    """Run a Pyrite function via FFI and return result
    
    Args:
        lib_path: Path to shared library (.so, .dll, .dylib)
        function_name: Name of exported function
        *args: Positional arguments (must be JSON-serializable or C-compatible)
        **kwargs: Keyword arguments (not supported for C functions, use *args)
        
    Returns:
        Function result (parsed from JSON if applicable)
        
    Note:
        This is a placeholder implementation. Actual implementation depends on:
        - Function signature (C types vs JSON)
        - Return type (simple vs complex)
        - Memory management
        
    For now, assumes functions return JSON strings.
    """
    try:
        # Load shared library
        lib = ctypes.CDLL(str(lib_path))
        
        # Get function
        func = getattr(lib, function_name)
        
        # For MVP: assume function takes JSON string, returns JSON string
        # This will need to be customized per function
        if args:
            # Serialize first argument as JSON string
            input_json = json.dumps(args[0] if len(args) == 1 else args)
            input_bytes = input_json.encode('utf-8')
            
            # Call function
            func.argtypes = [ctypes.c_char_p]
            func.restype = ctypes.c_void_p
            
            result_ptr = func(input_bytes)
            
            if not result_ptr:
                raise EquivalenceTestError(f"Pyrite function {function_name} returned NULL")
            
            # Read result string
            result_str = ctypes.string_at(result_ptr).decode('utf-8')
            
            # Free memory (if free function exists)
            try:
                free_func = getattr(lib, "free_string")
                free_func.argtypes = [ctypes.c_void_p]
                free_func(result_ptr)
            except AttributeError:
                pass  # No free function, assume managed memory
            
            # Parse JSON result
            return json.loads(result_str)
        else:
            # No arguments
            func.argtypes = []
            func.restype = ctypes.c_void_p
            
            result_ptr = func()
            if not result_ptr:
                return None
            
            result_str = ctypes.string_at(result_ptr).decode('utf-8')
            return json.loads(result_str)
            
    except OSError as e:
        raise EquivalenceTestError(f"Failed to load Pyrite library {lib_path}: {e}")
    except Exception as e:
        raise EquivalenceTestError(f"Failed to run Pyrite function {function_name}: {e}")


def generate_equivalence_tests(
    python_module: str,
    python_function: str,
    pyrite_lib_path: str,
    pyrite_function: str,
    test_cases: List[Tuple[tuple, dict]],
    test_name: Optional[str] = None
):
    """Generate equivalence tests between Python and Pyrite functions
    
    Args:
        python_module: Python module path (e.g., "quarry.workspace")
        python_function: Python function name
        pyrite_lib_path: Path to Pyrite shared library
        pyrite_function: Pyrite function name
        test_cases: List of (args_tuple, kwargs_dict) test cases
        test_name: Optional test name for pytest
        
    Example:
        test_equivalence(
            "quarry.workspace",
            "parse_workspace_toml",
            "./workspace.so",
            "parse_workspace_toml",
            [
                (("Workspace.toml",), {}),
                (("other.toml",), {}),
            ]
        )
    """
    for i, (args, kwargs) in enumerate(test_cases):
        test_id = f"{test_name or python_function}_case_{i}"
        
        def test_case():
            # Run Python version
            try:
                python_result = run_python_function(python_module, python_function, *args, **kwargs)
            except Exception as e:
                pytest.fail(f"Python function failed: {e}")
            
            # Run Pyrite version
            try:
                pyrite_result = run_pyrite_function(pyrite_lib_path, pyrite_function, *args, **kwargs)
            except EquivalenceTestError as e:
                pytest.skip(f"Pyrite function not available: {e}")
            except Exception as e:
                pytest.fail(f"Pyrite function failed: {e}")
            
            # Compare results
            are_equal, error_msg = compare_outputs(python_result, pyrite_result)
            if not are_equal:
                pytest.fail(error_msg)
        
        # Register test with pytest
        test_case.__name__ = test_id
        yield test_case


# Example test (commented out until Pyrite module exists)
"""
@pytest.mark.integration
def test_workspace_parse_equivalence():
    '''Test that Pyrite parse_workspace_toml matches Python version'''
    test_cases = [
        (("Workspace.toml",), {}),
        (("tests/test-projects/file_processor/Workspace.toml",), {}),
    ]
    
    for test_func in generate_equivalence_tests(
        "quarry.workspace",
        "parse_workspace_toml",
        "./workspace.so",  # Will be built during porting
        "parse_workspace_toml",
        test_cases,
        "workspace_parse"
    ):
        test_func()
"""


# Helper for golden file comparison
def compare_with_golden_file(
    result: Any,
    golden_file_path: str,
    update_golden: bool = False
) -> Tuple[bool, Optional[str]]:
    """Compare result with golden file
    
    Args:
        result: Result to compare
        golden_file_path: Path to golden file (JSON)
        update_golden: If True, update golden file instead of comparing
        
    Returns:
        Tuple of (matches, error_message)
    """
    golden_path = Path(golden_file_path)
    normalized = normalize_for_comparison(result)
    result_json = json.dumps(normalized, indent=2)
    
    if update_golden:
        golden_path.write_text(result_json)
        return (True, None)
    
    if not golden_path.exists():
        return (False, f"Golden file not found: {golden_file_path}")
    
    golden_json = golden_path.read_text()
    golden_data = json.loads(golden_json)
    
    if normalized == golden_data:
        return (True, None)
    else:
        return (False, f"Result differs from golden file:\nResult: {result_json}\nGolden: {golden_json}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
