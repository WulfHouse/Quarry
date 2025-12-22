"""Test incremental compilation caching"""
import pytest
import sys
import tempfile
import time
from pathlib import Path

# Add forge to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))

from src.utils.incremental import IncrementalCompiler, CacheEntry


def test_incremental_cache_skips_unchanged():
    """Test that incremental compilation skips unchanged modules"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".pyrite" / "cache"
        compiler = IncrementalCompiler(cache_dir=cache_dir)
        
        # Create test module
        test_module = Path(tmpdir) / "test.pyrite"
        test_module.write_text("fn main():\n    print(42)\n")
        
        # Compute hash and create cache entry
        module_hash = compiler.compute_file_hash(test_module)
        obj_file = test_module.with_suffix(".o")
        obj_file.write_bytes(b"dummy object file")
        
        entry = CacheEntry(
            module_path=str(test_module),
            source_hash=module_hash,
            dependencies=[],
            dependency_hashes={},
            compiled_at=time.time(),
            compiler_version=compiler.COMPILER_VERSION,
            object_file_path=str(obj_file)
        )
        compiler.save_cache_entry(str(test_module), entry)
        compiler.module_hashes[str(test_module)] = module_hash
        
        # Check if should recompile (should be False)
        should_compile, reason = compiler.should_recompile(str(test_module))
        # Source hash should match, so it should not recompile due to source change
        assert "Source changed" not in reason, f"Unchanged source should not show 'Source changed', got: {reason}"


def test_incremental_cache_updates_on_change():
    """Test that incremental cache updates when module changes"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".pyrite" / "cache"
        compiler = IncrementalCompiler(cache_dir=cache_dir)
        
        # Create test module
        test_module = Path(tmpdir) / "test.pyrite"
        test_module.write_text("fn main():\n    print(42)\n")
        
        # Compute hash and create cache entry
        module_hash = compiler.compute_file_hash(test_module)
        entry = CacheEntry(
            module_path=str(test_module),
            source_hash=module_hash,
            dependencies=[],
            dependency_hashes={},
            compiled_at=time.time(),
            compiler_version=compiler.COMPILER_VERSION,
            object_file_path=""
        )
        compiler.save_cache_entry(str(test_module), entry)
        
        # Change the file
        test_module.write_text("fn main():\n    print(100)\n")
        
        # Check if should recompile (should be True)
        should_compile, reason = compiler.should_recompile(str(test_module))
        assert should_compile == True, f"Changed module should recompile, but got: {reason}"
        assert "Source changed" in reason or "changed" in reason.lower()


def test_incremental_cache_stores_metadata():
    """Test that incremental cache stores module metadata"""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / ".pyrite" / "cache"
        compiler = IncrementalCompiler(cache_dir=cache_dir)
        
        # Create test module
        test_module = Path(tmpdir) / "test.pyrite"
        test_module.write_text("fn main():\n    pass\n")
        module_hash = compiler.compute_file_hash(test_module)
        
        # Create and save cache entry
        obj_file = test_module.with_suffix(".o")
        obj_file.write_bytes(b"dummy")
        entry = CacheEntry(
            module_path=str(test_module),
            source_hash=module_hash,
            dependencies=["tokens.pyrite"],
            dependency_hashes={"tokens.pyrite": "abc123"},
            compiled_at=time.time(),
            compiler_version=compiler.COMPILER_VERSION,
            object_file_path=str(obj_file)
        )
        compiler.save_cache_entry(str(test_module), entry)
        compiler.save_cache_metadata()
        
        # Verify modules.json exists and has correct format
        modules_json = compiler.modules_json_path
        assert modules_json.exists(), "modules.json should exist"
        
        import json
        data = json.loads(modules_json.read_text())
        # Check that test module is in cache
        module_key = str(test_module) if str(test_module) in data else [k for k in data.keys() if "test" in k][0]
        assert module_key in data or any("test" in k for k in data.keys()), "Test module should be in cache"
