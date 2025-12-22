"""Tests for performance lockfile system"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from quarry.perf_lock import (
    PerformanceProfiler,
    PerformanceLockfile,
    FunctionProfile,
    cmd_perf_baseline,
    cmd_perf_check,
    cmd_perf_explain
)


def test_function_profile_serialization():
    """Test FunctionProfile serialization/deserialization"""
    func = FunctionProfile(
        name="test_func",
        time_ms=123.45,
        time_percent=12.5,
        call_count=100,
        alloc_sites=2,
        simd_width=4,
        inlined_calls=5,
        stack_bytes=256
    )
    
    # Test to_dict
    data = func.__dict__
    assert data['name'] == "test_func"
    assert data['time_ms'] == 123.45
    assert data['simd_width'] == 4
    
    # Test from_dict (via PerformanceLockfile)
    lockfile_dict = {
        'version': '1.0',
        'generated': '2024-01-01T00:00:00Z',
        'build_config': 'release',
        'platform': 'linux',
        'hot_functions': [data],
        'total_time_ms': 1000.0
    }
    
    lockfile = PerformanceLockfile.from_dict(lockfile_dict)
    assert len(lockfile.hot_functions) == 1
    assert lockfile.hot_functions[0].name == "test_func"
    assert lockfile.hot_functions[0].simd_width == 4


def test_performance_lockfile_serialization():
    """Test PerformanceLockfile serialization"""
    functions = [
        FunctionProfile(
            name="func1",
            time_ms=100.0,
            time_percent=50.0,
            call_count=10,
            alloc_sites=0
        ),
        FunctionProfile(
            name="func2",
            time_ms=50.0,
            time_percent=25.0,
            call_count=5,
            alloc_sites=1
        )
    ]
    
    lockfile = PerformanceLockfile(
        version="1.0",
        generated="2024-01-01T00:00:00Z",
        build_config="release",
        platform="linux",
        hot_functions=functions,
        total_time_ms=200.0
    )
    
    # Serialize
    data = lockfile.to_dict()
    assert data['version'] == "1.0"
    assert len(data['hot_functions']) == 2
    assert data['total_time_ms'] == 200.0
    
    # Deserialize
    lockfile2 = PerformanceLockfile.from_dict(data)
    assert lockfile2.version == "1.0"
    assert len(lockfile2.hot_functions) == 2
    assert lockfile2.hot_functions[0].name == "func1"
    assert lockfile2.hot_functions[1].name == "func2"


def test_profiler_initialization():
    """Test PerformanceProfiler initialization"""
    profiler = PerformanceProfiler()
    assert profiler.platform in ["linux", "darwin", "windows"]


@patch('quarry.perf_lock.subprocess.run')
@patch('quarry.perf_lock.Path.exists')
def test_profile_simple(mock_exists, mock_subprocess):
    """Test simple profiling fallback"""
    mock_exists.return_value = True
    
    # Mock subprocess.run for binary execution
    mock_result = Mock()
    mock_result.returncode = 0
    mock_subprocess.return_value = mock_result
    
    profiler = PerformanceProfiler()
    binary_path = Path("test_binary")
    
    # Mock time.time for consistent timing
    with patch('quarry.perf_lock.time.time', side_effect=[0.0, 0.1]):
        lockfile = profiler._profile_simple(binary_path)
    
    assert lockfile is not None
    assert lockfile.total_time_ms == 100.0  # 0.1 seconds = 100ms
    assert len(lockfile.hot_functions) == 1
    assert lockfile.hot_functions[0].name == "main"


def test_parse_perf_report():
    """Test parsing perf report output"""
    profiler = PerformanceProfiler()
    
    perf_output = """
# Overhead  Command  Shared Object  Symbol
# ........  .......  .............  ......
    34.23%  main     program        [.] process_data
    12.45%  main     program        [.] helper_func
     5.67%  main     libc.so        [.] malloc
    """
    
    functions = profiler._parse_perf_report(perf_output)
    
    assert len(functions) >= 2
    # Should be sorted by time_ms descending
    assert functions[0].time_percent >= functions[1].time_percent if len(functions) > 1 else True


def test_regression_detection():
    """Test regression detection logic"""
    profiler = PerformanceProfiler()
    
    baseline = PerformanceLockfile(
        version="1.0",
        generated="2024-01-01T00:00:00Z",
        build_config="release",
        platform="linux",
        hot_functions=[
            FunctionProfile(
                name="func1",
                time_ms=100.0,
                time_percent=50.0,
                call_count=10,
                alloc_sites=0
            )
        ],
        total_time_ms=200.0
    )
    
    # Current is 10% slower (regression)
    current = PerformanceLockfile(
        version="1.0",
        generated="2024-01-02T00:00:00Z",
        build_config="release",
        platform="linux",
        hot_functions=[
            FunctionProfile(
                name="func1",
                time_ms=110.0,
                time_percent=50.0,
                call_count=10,
                alloc_sites=0
            )
        ],
        total_time_ms=220.0
    )
    
    # Should detect regression (threshold is 5%)
    no_regression = profiler.check_regression(current, baseline, threshold=5.0)
    assert no_regression == False  # Regression detected
    
    # Current is 3% slower (within threshold)
    current2 = PerformanceLockfile(
        version="1.0",
        generated="2024-01-02T00:00:00Z",
        build_config="release",
        platform="linux",
        hot_functions=[
            FunctionProfile(
                name="func1",
                time_ms=103.0,
                time_percent=50.0,
                call_count=10,
                alloc_sites=0
            )
        ],
        total_time_ms=206.0
    )
    
    no_regression2 = profiler.check_regression(current2, baseline, threshold=5.0)
    assert no_regression2 == True  # No regression


def test_explain_regression():
    """Test regression explanation"""
    profiler = PerformanceProfiler()
    
    baseline = PerformanceLockfile(
        version="1.0",
        generated="2024-01-01T00:00:00Z",
        build_config="release",
        platform="linux",
        hot_functions=[
            FunctionProfile(
                name="func1",
                time_ms=100.0,
                time_percent=50.0,
                call_count=10,
                alloc_sites=0,
                simd_width=8,
                inlined_calls=5
            )
        ],
        total_time_ms=200.0
    )
    
    # Current with SIMD width change
    current = PerformanceLockfile(
        version="1.0",
        generated="2024-01-02T00:00:00Z",
        build_config="release",
        platform="linux",
        hot_functions=[
            FunctionProfile(
                name="func1",
                time_ms=120.0,  # 20% slower
                time_percent=50.0,
                call_count=10,
                alloc_sites=0,
                simd_width=4,  # Changed from 8 to 4
                inlined_calls=3  # Decreased from 5 to 3
            )
        ],
        total_time_ms=240.0
    )
    
    explanations = profiler.explain_regression(current, baseline)
    
    # Should detect SIMD width change and inlining decrease
    assert len(explanations) >= 1
    assert any("SIMD width" in exp for exp in explanations) or any("Inlining" in exp for exp in explanations)


@patch('quarry.perf_lock.Path.exists')
@patch('quarry.perf_lock.Path.read_text')
@patch('quarry.perf_lock.Path.write_text')
@patch('quarry.perf_lock.PerformanceProfiler')
def test_cmd_perf_baseline(mock_profiler_class, mock_write, mock_read, mock_exists):
    """Test baseline generation command"""
    mock_exists.return_value = True
    
    # Mock profiler
    mock_profiler = Mock()
    mock_lockfile = PerformanceLockfile(
        version="1.0",
        generated="2024-01-01T00:00:00Z",
        build_config="release",
        platform="linux",
        hot_functions=[],
        total_time_ms=100.0
    )
    mock_profiler.profile_binary.return_value = mock_lockfile
    mock_profiler_class.return_value = mock_profiler
    
    # Mock Path for binary
    with patch('quarry.perf_lock.Path') as mock_path:
        mock_binary = Mock()
        mock_binary.exists.return_value = True
        mock_path.side_effect = lambda p: mock_binary if "target" in str(p) else Path(p)
        
        result = cmd_perf_baseline()
        # Should succeed (return 0)
        assert result == 0


@patch('quarry.perf_lock.Path')
@patch('quarry.perf_lock.PerformanceProfiler')
def test_cmd_perf_check(mock_profiler_class, mock_path_class):
    """Test check command"""
    # Mock Path class
    def path_side_effect(path_str):
        mock_path = Mock()
        if "Perf.lock" in str(path_str):
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = json.dumps({
                'version': '1.0',
                'generated': '2024-01-01T00:00:00Z',
                'build_config': 'release',
                'platform': 'linux',
                'hot_functions': [],
                'total_time_ms': 100.0
            })
        elif "target" in str(path_str):
            mock_path.exists.return_value = True
        else:
            mock_path.exists.return_value = False
        return mock_path
    
    mock_path_class.side_effect = path_side_effect
    
    # Mock profiler
    baseline_data = {
        'version': '1.0',
        'generated': '2024-01-01T00:00:00Z',
        'build_config': 'release',
        'platform': 'linux',
        'hot_functions': [],
        'total_time_ms': 100.0
    }
    mock_profiler = Mock()
    current_lockfile = PerformanceLockfile.from_dict(baseline_data)
    mock_profiler.profile_binary.return_value = current_lockfile
    mock_profiler.check_regression.return_value = True  # No regression
    mock_profiler_class.return_value = mock_profiler
    
    result = cmd_perf_check(threshold=5.0)
    # Should succeed (no regression)
    assert result == 0


def test_ci_integration_exit_code_on_regression():
    """Test that CI integration returns exit code 1 on regression"""
    from quarry.perf_lock import cmd_perf_check, PerformanceLockfile, FunctionProfile
    import tempfile
    import json
    from pathlib import Path
    from unittest.mock import patch, Mock
    
    # Create a temporary Perf.lock file
    with tempfile.TemporaryDirectory() as tmpdir:
        lockfile_path = Path(tmpdir) / "Perf.lock"
        
        # Create baseline lockfile
        baseline = PerformanceLockfile(
            version="1.0",
            generated="2025-01-01T00:00:00Z",
            build_config="release",
            platform="test",
            hot_functions=[
                FunctionProfile(
                    name="test_func",
                    time_ms=100.0,
                    time_percent=50.0,
                    call_count=100,
                    alloc_sites=0
                )
            ],
            total_time_ms=200.0
        )
        
        # Save baseline
        lockfile_path.write_text(json.dumps(baseline.to_dict(), indent=2))
        
        # Mock profiler to return slower performance (regression)
        slower_lockfile = PerformanceLockfile(
            version="1.0",
            generated="2025-01-02T00:00:00Z",
            build_config="release",
            platform="test",
            hot_functions=[
                FunctionProfile(
                    name="test_func",
                    time_ms=110.0,  # 10% slower (above 5% threshold)
                    time_percent=50.0,
                    call_count=100,
                    alloc_sites=0
                )
            ],
            total_time_ms=220.0
        )
        
        with patch('quarry.perf_lock.Path') as mock_path_class:
            def path_side_effect(path_str):
                mock_path = Mock()
                if "Perf.lock" in str(path_str):
                    mock_path.exists.return_value = True
                    mock_path.read_text.return_value = lockfile_path.read_text()
                elif "target" in str(path_str):
                    mock_path.exists.return_value = True
                else:
                    mock_path.exists.return_value = False
                return mock_path
            
            mock_path_class.side_effect = path_side_effect
            
            with patch('quarry.perf_lock.PerformanceProfiler') as mock_profiler_class:
                mock_profiler = Mock()
                mock_profiler.profile_binary.return_value = slower_lockfile
                mock_profiler.check_regression.return_value = False  # Regression detected
                mock_profiler_class.return_value = mock_profiler
                
                # Should return 1 (error) for regression
                result = cmd_perf_check(threshold=5.0)
                assert result == 1  # CI should fail on regression