"""Tests for deterministic builds"""

import hashlib
import os
import tempfile
from pathlib import Path
import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests

from quarry.deterministic import DeterministicBuilder, BuildManifest


def test_deterministic_builder_init():
    """Test DeterministicBuilder initialization"""
    builder = DeterministicBuilder()
    assert builder.source_date_epoch is not None
    assert isinstance(builder.source_date_epoch, int)


def test_compute_binary_hash():
    """Test binary hash computation"""
    builder = DeterministicBuilder()
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test binary content")
        temp_path = Path(f.name)
    
    try:
        hash1 = builder.compute_binary_hash(temp_path)
        hash2 = builder.compute_binary_hash(temp_path)
        
        # Same file should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length
    finally:
        temp_path.unlink()


def test_hash_file():
    """Test file hashing"""
    builder = DeterministicBuilder()
    
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test content")
        temp_path = Path(f.name)
    
    try:
        hash1 = builder.hash_file(temp_path)
        hash2 = builder.hash_file(temp_path)
        
        assert hash1 == hash2
        assert len(hash1) == 64
    finally:
        temp_path.unlink()


def test_find_all_source_files():
    """Test finding source files"""
    builder = DeterministicBuilder()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        
        # Create some source files
        (src_dir / "main.pyrite").write_text("fn main() {}")
        (src_dir / "lib.pyrite").write_text("fn helper() {}")
        (src_dir / "other.txt").write_text("not a source file")
        
        source_files = builder.find_all_source_files(src_dir)
        
        # Should find .pyrite files, sorted
        assert len(source_files) == 2
        assert all(f.suffix == ".pyrite" for f in source_files)
        assert source_files == sorted(source_files)


def test_generate_manifest():
    """Test manifest generation"""
    builder = DeterministicBuilder()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create a binary file
        binary_path = tmp_path / "main"
        binary_path.write_bytes(b"fake binary")
        
        # Create source files
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        source1 = src_dir / "main.pyrite"
        source1.write_text("fn main() {}")
        
        source_files = [source1]
        
        manifest = builder.generate_manifest(
            binary_path,
            source_files,
            compiler_version="1.0.0",
            build_flags=["--deterministic"]
        )
        
        assert manifest.build_hash is not None
        assert manifest.compiler_version == "1.0.0"
        assert len(manifest.source_files) == 1
        assert str(source1) in manifest.source_files


def test_verify_build_matching():
    """Test build verification with matching binary"""
    builder = DeterministicBuilder()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create binary
        binary_path = tmp_path / "main"
        binary_path.write_bytes(b"test binary")
        
        # Create manifest
        manifest = builder.generate_manifest(
            binary_path,
            [],
            compiler_version="1.0.0"
        )
        
        # Save manifest as JSON
        manifest_path = tmp_path / "BuildManifest.json"
        import json
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))
        
        # Verify should pass
        assert builder.verify_build(binary_path, manifest_path) is True


def test_verify_build_mismatch():
    """Test build verification with mismatched binary"""
    builder = DeterministicBuilder()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create binary
        binary_path = tmp_path / "main"
        binary_path.write_bytes(b"test binary")
        
        # Create manifest for different content
        other_binary = tmp_path / "other"
        other_binary.write_bytes(b"different content")
        manifest = builder.generate_manifest(
            other_binary,
            [],
            compiler_version="1.0.0"
        )
        
        # Save manifest
        manifest_path = tmp_path / "BuildManifest.json"
        import json
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))
        
        # Verify should fail
        assert builder.verify_build(binary_path, manifest_path) is False


def test_source_date_epoch_from_env():
    """Test SOURCE_DATE_EPOCH from environment"""
    original = os.environ.get('SOURCE_DATE_EPOCH')
    
    try:
        os.environ['SOURCE_DATE_EPOCH'] = '1234567890'
        builder = DeterministicBuilder()
        assert builder.source_date_epoch == 1234567890
    finally:
        if original:
            os.environ['SOURCE_DATE_EPOCH'] = original
        elif 'SOURCE_DATE_EPOCH' in os.environ:
            del os.environ['SOURCE_DATE_EPOCH']

