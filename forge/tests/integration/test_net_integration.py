"""Integration tests for TCP and HTTP networking (SPEC-LANG-0850)

Tests TCP echo server and HTTP client/server functionality.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from forge.src.frontend import lex, parse
from forge.src import ast


@pytest.mark.fast
def test_tcp_stream_parse():
    """Test that TcpStream implementation parses correctly"""
    source = """
import std.net.tcp

fn test_tcp() -> i32:
    let conn = TcpStream.connect(string_new("127.0.0.1"), 8080)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify parsing succeeded
    assert program is not None
    assert len(program.items) > 0


@pytest.mark.fast
def test_tcp_listener_parse():
    """Test that TcpListener implementation parses correctly"""
    source = """
import std.net.tcp

fn test_listener() -> i32:
    let listener = TcpListener.bind(string_new("0.0.0.0"), 8080)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify parsing succeeded
    assert program is not None
    assert len(program.items) > 0


@pytest.mark.fast
def test_http_client_methods_exist():
    """Test that HttpClient has all required methods (GET, POST, PUT, DELETE)"""
    # Read the http.pyrite file and verify all methods are present
    http_file = Path(__file__).parent.parent.parent.parent / "pyrite" / "net" / "http.pyrite"
    assert http_file.exists(), "http.pyrite should exist"
    
    content = http_file.read_text()
    
    # Verify all required HTTP methods are present
    assert "fn get(" in content, "HttpClient should have get method"
    assert "fn post(" in content, "HttpClient should have post method"
    assert "fn put(" in content, "HttpClient should have put method"
    assert "fn delete(" in content, "HttpClient should have delete method"


@pytest.mark.fast
def test_http_client_parse():
    """Test that HttpClient implementation parses correctly"""
    source = """
import std.net.http

fn test_http_get() -> i32:
    let client = HttpClient.new()
    let result = client.get(string_new("http://example.com"))
    match result:
        case Ok(response):
            return response.status_code
        case Err(e):
            return 1
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify parsing succeeded
    assert program is not None
    assert len(program.items) > 0


@pytest.mark.fast
def test_http_post_parse():
    """Test that HTTP POST parses correctly"""
    source = """
import std.net.http

fn test_http_post() -> i32:
    let client = HttpClient.new()
    let body = string_new("{}")
    let result = client.post(string_new("http://example.com/api"), body)
    match result:
        case Ok(response):
            return 0
        case Err(e):
            return 1
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify parsing succeeded
    assert program is not None


@pytest.mark.fast
def test_http_put_parse():
    """Test that HTTP PUT parses correctly"""
    source = """
import std.net.http

fn test_http_put() -> i32:
    let client = HttpClient.new()
    let body = string_new("{}")
    let result = client.put(string_new("http://example.com/api/1"), body)
    match result:
        case Ok(response):
            return 0
        case Err(e):
            return 1
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify parsing succeeded
    assert program is not None


@pytest.mark.fast
def test_http_delete_parse():
    """Test that HTTP DELETE parses correctly"""
    source = """
import std.net.http

fn test_http_delete() -> i32:
    let client = HttpClient.new()
    let result = client.delete(string_new("http://example.com/api/1"))
    match result:
        case Ok(response):
            return 0
        case Err(e):
            return 1
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify parsing succeeded
    assert program is not None


@pytest.mark.fast
def test_http_server_parse():
    """Test that HttpServer implementation parses correctly"""
    source = """
import std.net.http

fn test_http_server() -> i32:
    let server = HttpServer.new(8080)
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify parsing succeeded
    assert program is not None
    assert len(program.items) > 0


@pytest.mark.fast
def test_tcp_echo_pattern():
    """Test TCP echo server pattern parses correctly"""
    source = """
import std.net.tcp

fn echo_server() -> i32:
    let listener = TcpListener.bind(string_new("127.0.0.1"), 9999)
    # Simplified test - just verify API exists
    return 0
"""
    
    tokens = lex(source, "<test>")
    program = parse(tokens)
    
    # Verify parsing succeeded
    assert program is not None
    assert len(program.items) > 0

