import pytest
from src.utils.diagnostics import Diagnostic, DiagnosticManager, Span

def test_i18n_support():
    """Test internationalization support (SPEC-FORGE-0106)"""
    span = Span("test.pyrite", 1, 1, 1, 5)
    
    # English
    manager_en = DiagnosticManager(language="en")
    msg_en = manager_en.get_message("P0234", var_name="x")
    assert "cannot use moved value 'x'" in msg_en
    
    # Spanish
    manager_es = DiagnosticManager(language="es")
    msg_es = manager_es.get_message("P0234", var_name="x")
    assert "no se puede usar el valor movido 'x'" in msg_es

def test_error_suppression():
    """Test error suppression (SPEC-FORGE-0109)"""
    span = Span("test.pyrite", 1, 1, 1, 5)
    manager = DiagnosticManager()
    
    diag = Diagnostic(code="P1050", message="allocation in loop", span=span)
    
    # Not suppressed
    manager.report(diag)
    assert len(manager.diagnostics) == 1
    
    # Suppressed
    manager.diagnostics = []
    manager.allow("P1050")
    manager.report(diag)
    assert len(manager.diagnostics) == 0

def test_performance_diagnostics_codes():
    """Test that performance diagnostic codes exist (SPEC-FORGE-0110)"""
    from src.utils.diagnostics import ERROR_CODES
    assert "P1050" in ERROR_CODES
    assert "P1051" in ERROR_CODES
    assert "heap allocation" in ERROR_CODES["P1050"]
    assert "implicit copy" in ERROR_CODES["P1051"]

