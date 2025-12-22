"""Tests for binary size analysis"""

import pytest

pytestmark = pytest.mark.integration  # All tests in this file are integration tests
from pathlib import Path
from quarry.binary_size import BinarySizeAnalyzer, SizeReport, Symbol, EMBEDDED_TARGETS


def test_binary_size_analyzer_creation():
    """Test that BinarySizeAnalyzer can be created"""
    analyzer = BinarySizeAnalyzer()
    assert analyzer is not None
    assert analyzer.symbols == []


def test_size_report_formatting():
    """Test size formatting in SizeReport"""
    report = SizeReport(
        total_size=1024,
        text_size=512,
        rodata_size=256,
        data_size=128,
        bss_size=128,
        symbols=[]
    )
    
    assert report.format_size(512) == "512 B"
    assert report.format_size(1024 * 1024) == "1.0 MB"
    assert report.format_size(100) == "100 B"
    assert report.format_size(2048) == "2.0 KB"


def test_embedded_targets_defined():
    """Test that embedded targets are defined"""
    assert 'stm32f4' in EMBEDDED_TARGETS
    assert EMBEDDED_TARGETS['stm32f4'] == 256 * 1024
    assert 'arduino-uno' in EMBEDDED_TARGETS
    assert EMBEDDED_TARGETS['arduino-uno'] == 32 * 1024


def test_symbol_creation():
    """Test Symbol dataclass"""
    symbol = Symbol(
        name="main",
        size=1024,
        section=".text",
        type="F"
    )
    assert symbol.name == "main"
    assert symbol.size == 1024
    assert symbol.section == ".text"
    assert symbol.type == "F"


def test_analyze_nonexistent_binary():
    """Test analyzing a binary that doesn't exist"""
    analyzer = BinarySizeAnalyzer()
    result = analyzer.analyze_binary(Path("nonexistent_binary.exe"))
    assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

