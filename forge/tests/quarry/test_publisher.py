"""Test package publishing"""
import pytest
import sys
import tempfile
from pathlib import Path

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.publisher import package_project, get_source_files, validate_for_publish


def test_package_project_creates_package():
    """Test that package_project() creates package"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        # Create Quarry.toml
        (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "1.0.0"
""")
        
        # Create src/ directory with a file
        (project_dir / "src").mkdir()
        (project_dir / "src" / "main.pyrite").write_text("fn main():\n    print(42)\n")
        
        # Package project
        package_path = package_project(str(project_dir))
        
        assert package_path is not None
        assert package_path.exists()
        assert (package_path / "Quarry.toml").exists()
        assert (package_path / "src").exists()
        assert (package_path / "src" / "main.pyrite").exists()


def test_package_project_includes_all_source_files():
    """Test that package includes all source files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        # Create Quarry.toml
        (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "1.0.0"
""")
        
        # Create src/ with multiple files
        (project_dir / "src").mkdir()
        (project_dir / "src" / "main.pyrite").write_text("fn main():\n    print(42)\n")
        (project_dir / "src" / "lib.pyrite").write_text("fn helper():\n    return 42\n")
        
        # Create tests/
        (project_dir / "tests").mkdir()
        (project_dir / "tests" / "test_main.pyrite").write_text("@test\nfn test_main():\n    assert true\n")
        
        # Package project
        package_path = package_project(str(project_dir))
        
        assert package_path is not None
        assert (package_path / "src" / "main.pyrite").exists()
        assert (package_path / "src" / "lib.pyrite").exists()
        assert (package_path / "tests" / "test_main.pyrite").exists()


def test_package_project_excludes_build_artifacts():
    """Test that package excludes build artifacts"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        # Create Quarry.toml
        (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "1.0.0"
""")
        
        # Create src/
        (project_dir / "src").mkdir()
        (project_dir / "src" / "main.pyrite").write_text("fn main():\n    print(42)\n")
        
        # Create target/ (should be excluded)
        (project_dir / "target").mkdir()
        (project_dir / "target" / "main.exe").write_text("binary")
        
        # Create deps/ (should be excluded)
        (project_dir / "deps").mkdir()
        (project_dir / "deps" / "dep1").mkdir()
        
        # Package project
        package_path = package_project(str(project_dir))
        
        assert package_path is not None
        # target/ and deps/ should not be in package
        assert not (package_path / "target").exists()
        assert not (package_path / "deps").exists()
        # But src/ should be included
        assert (package_path / "src").exists()


def test_get_source_files():
    """Test that get_source_files() finds all source files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        # Create src/ with files
        (project_dir / "src").mkdir()
        (project_dir / "src" / "main.pyrite").write_text("fn main():\n    print(42)\n")
        (project_dir / "src" / "subdir").mkdir()
        (project_dir / "src" / "subdir" / "lib.pyrite").write_text("fn helper():\n    return 42\n")
        
        # Create tests/
        (project_dir / "tests").mkdir()
        (project_dir / "tests" / "test.pyrite").write_text("@test\nfn test():\n    assert true\n")
        
        source_files = get_source_files(project_dir)
        
        # Should find all .pyrite files
        file_names = [f.name for f in source_files]
        assert "main.pyrite" in file_names
        assert "lib.pyrite" in file_names
        assert "test.pyrite" in file_names


def test_validate_for_publish_valid_project():
    """Test that validation passes for valid project"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        # Create valid Quarry.toml
        (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "1.0.0"
license = "MIT"
""")
        
        is_valid, errors = validate_for_publish(str(project_dir))
        assert is_valid
        assert len(errors) == 0


def test_validate_for_publish_missing_license():
    """Test that validation fails for missing license"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        # Create Quarry.toml without license
        (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "1.0.0"
""")
        
        is_valid, errors = validate_for_publish(str(project_dir))
        assert not is_valid
        assert any("license" in error.lower() for error in errors)


def test_validate_for_publish_invalid_version():
    """Test that validation fails for invalid version"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        # Create Quarry.toml with invalid version
        (project_dir / "Quarry.toml").write_text("""[package]
name = "test-pkg"
version = "invalid"
license = "MIT"
""")
        
        is_valid, errors = validate_for_publish(str(project_dir))
        assert not is_valid
        assert any("version" in error.lower() for error in errors)
