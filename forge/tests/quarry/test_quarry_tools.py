"""Tests for quarry tooling (cost, bloat, perf, fix)"""

import pytest

pytestmark = pytest.mark.slow  # All tests in this file are slow E2E tests

import tempfile
import json
from pathlib import Path
import sys

# Add forge and repo root to path
repo_root = Path(__file__).parent.parent.parent
compiler_dir = repo_root / "forge"
sys.path.insert(0, str(compiler_dir))
sys.path.insert(0, str(repo_root))  # For quarry imports

from quarry.cost_analysis import CostAnalyzer, AllocationSite, CopySite
from quarry.binary_size import BinarySizeAnalyzer, Symbol, SizeReport
from quarry.perf_lock import PerformanceProfiler, PerformanceLockfile, FunctionProfile
from quarry.deterministic import DeterministicBuilder, BuildManifest
from quarry.auto_fix import AutoFixer, Fix


class TestCostAnalysis:
    """Test cost analysis"""
    
    def test_cost_analyzer_creation(self):
        """Test creating cost analyzer"""
        analyzer = CostAnalyzer()
        assert analyzer is not None
        assert analyzer.allocations == []
        assert analyzer.copies == []
    
    def test_allocation_site_creation(self):
        """Test allocation site dataclass"""
        alloc = AllocationSite(
            file="main.pyrite",
            line=10,
            function="main",
            type_allocated="List[int]",
            estimated_bytes=24,
            in_loop=False
        )
        
        assert alloc.file == "main.pyrite"
        assert alloc.line == 10
        assert alloc.estimated_bytes == 24
    
    def test_copy_site_creation(self):
        """Test copy site dataclass"""
        copy = CopySite(
            file="main.pyrite",
            line=15,
            function="process",
            type_copied="ImageBuffer",
            bytes_copied=4096
        )
        
        assert copy.file == "main.pyrite"
        assert copy.bytes_copied == 4096


class TestBinarySizeAnalysis:
    """Test binary size analysis"""
    
    def test_size_analyzer_creation(self):
        """Test creating size analyzer"""
        analyzer = BinarySizeAnalyzer()
        assert analyzer is not None
    
    def test_symbol_creation(self):
        """Test symbol dataclass"""
        symbol = Symbol(
            name="main",
            size=1024,
            section=".text",
            type="function"
        )
        
        assert symbol.name == "main"
        assert symbol.size == 1024
    
    def test_size_report_format_size(self):
        """Test size formatting"""
        report = SizeReport(
            total_size=1024 * 1024,
            text_size=512 * 1024,
            rodata_size=256 * 1024,
            data_size=128 * 1024,
            bss_size=128 * 1024,
            symbols=[]
        )
        
        assert "MB" in report.format_size(1024 * 1024)
        assert "KB" in report.format_size(1024)
        assert "B" in report.format_size(100)


class TestPerformanceLockfile:
    """Test performance lockfile"""
    
    def test_function_profile_creation(self):
        """Test function profile dataclass"""
        profile = FunctionProfile(
            name="main",
            time_ms=100.5,
            time_percent=50.0,
            call_count=1,
            alloc_sites=2
        )
        
        assert profile.name == "main"
        assert profile.time_ms == 100.5
    
    def test_lockfile_creation(self):
        """Test lockfile dataclass"""
        lockfile = PerformanceLockfile(
            version="1.0",
            generated="2025-12-19T10:00:00Z",
            build_config="release",
            platform="linux",
            hot_functions=[
                FunctionProfile("main", 100.0, 100.0, 1, 0)
            ],
            total_time_ms=100.0
        )
        
        assert lockfile.version == "1.0"
        assert len(lockfile.hot_functions) == 1
    
    def test_lockfile_serialization(self):
        """Test lockfile to/from dict"""
        lockfile = PerformanceLockfile(
            version="1.0",
            generated="2025-12-19T10:00:00Z",
            build_config="release",
            platform="linux",
            hot_functions=[
                FunctionProfile("main", 100.0, 100.0, 1, 0)
            ],
            total_time_ms=100.0
        )
        
        # Serialize
        data = lockfile.to_dict()
        
        # Deserialize
        lockfile2 = PerformanceLockfile.from_dict(data)
        
        assert lockfile2.version == lockfile.version
        assert lockfile2.total_time_ms == lockfile.total_time_ms
    
    def test_regression_detection_no_change(self):
        """Test no regression when performance is stable"""
        baseline = PerformanceLockfile(
            version="1.0",
            generated="2025-12-19T10:00:00Z",
            build_config="release",
            platform="linux",
            hot_functions=[],
            total_time_ms=100.0
        )
        
        current = PerformanceLockfile(
            version="1.0",
            generated="2025-12-19T10:05:00Z",
            build_config="release",
            platform="linux",
            hot_functions=[],
            total_time_ms=102.0  # 2% change, within 5% threshold
        )
        
        profiler = PerformanceProfiler()
        no_regression = profiler.check_regression(current, baseline, threshold=5.0)
        
        assert no_regression is True
    
    def test_regression_detection_with_regression(self):
        """Test regression detected when performance degrades"""
        baseline = PerformanceLockfile(
            version="1.0",
            generated="2025-12-19T10:00:00Z",
            build_config="release",
            platform="linux",
            hot_functions=[],
            total_time_ms=100.0
        )
        
        current = PerformanceLockfile(
            version="1.0",
            generated="2025-12-19T10:05:00Z",
            build_config="release",
            platform="linux",
            hot_functions=[],
            total_time_ms=120.0  # 20% slower, exceeds 5% threshold
        )
        
        profiler = PerformanceProfiler()
        no_regression = profiler.check_regression(current, baseline, threshold=5.0)
        
        assert no_regression is False


class TestDeterministicBuilds:
    """Test deterministic build system"""
    
    def test_deterministic_builder_creation(self):
        """Test creating deterministic builder"""
        builder = DeterministicBuilder()
        assert builder is not None
        assert builder.source_date_epoch
    
    def test_compute_binary_hash(self):
        """Test binary hashing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.bin"
            test_file.write_bytes(b"test binary content")
            
            builder = DeterministicBuilder()
            hash1 = builder.compute_binary_hash(test_file)
            
            assert hash1
            assert len(hash1) == 64  # SHA-256 hex
            
            # Same content = same hash
            hash2 = builder.compute_binary_hash(test_file)
            assert hash1 == hash2
    
    def test_build_manifest_creation(self):
        """Test build manifest creation"""
        manifest = BuildManifest(
            build_hash="abc123",
            timestamp="2025-12-19T10:00:00Z",
            compiler_version="2.0.0",
            target="x86_64-linux",
            build_flags=["--release"],
            source_files={"main.pyrite": {"hash": "def456", "size": 100}},
            dependencies={}
        )
        
        assert manifest.build_hash == "abc123"
        assert manifest.compiler_version == "2.0.0"


class TestAutoFix:
    """Test auto-fix system"""
    
    def test_auto_fixer_creation(self):
        """Test creating auto fixer"""
        fixer = AutoFixer()
        assert fixer is not None
        assert fixer.fixes == []
    
    def test_fix_creation(self):
        """Test fix dataclass"""
        fix = Fix(
            description="Add reference",
            file_path="main.pyrite",
            line_number=10,
            old_text="process(data)",
            new_text="process(&data)",
            explanation="Borrow instead of move"
        )
        
        assert fix.description == "Add reference"
        assert fix.line_number == 10
    
    def test_extract_line_number(self):
        """Test extracting line number from error"""
        fixer = AutoFixer()
        
        error1 = "Error at line 10: cannot use moved value"
        line1 = fixer._extract_line_number(error1)
        assert line1 == 10
        
        error2 = "main.pyrite:15: type mismatch"
        line2 = fixer._extract_line_number(error2)
        assert line2 == 15
    
    def test_extract_variable_name(self):
        """Test extracting variable name from error"""
        fixer = AutoFixer()
        
        error1 = "cannot use moved value 'data'"
        var1 = fixer._extract_variable_name(error1)
        assert var1 == "data"
        
        error2 = 'undefined variable "count"'
        var2 = fixer._extract_variable_name(error2)
        assert var2 == "count"


class TestDogfoodBuild:
    """Test dogfood build command"""
    
    def test_dogfood_flag_recognized(self):
        """Test that --dogfood flag is recognized"""
        import sys
        from pathlib import Path
        
        # Add forge and repo root to path
        repo_root = Path(__file__).parent.parent.parent
        compiler_dir = repo_root / "forge"
        sys.path.insert(0, str(compiler_dir))
        sys.path.insert(0, str(repo_root))  # For quarry imports
        
        from quarry.main import cmd_build
        
        # Test that dogfood parameter is accepted
        # This will actually try to build workspaces, so it may take time
        # But we can at least verify the function accepts the parameter
        assert callable(cmd_build)
        
        # Verify function signature accepts dogfood parameter
        import inspect
        sig = inspect.signature(cmd_build)
        assert 'dogfood' in sig.parameters


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

