"""Pyrite LSP Server - Main implementation"""

import sys
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('pyrite-lsp.log'), logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger('pyrite-lsp')


class Position:
    """LSP Position (line, character)"""
    def __init__(self, line: int, character: int):
        self.line = line
        self.character = character
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Position':
        return cls(data['line'], data['character'])
    
    def to_dict(self) -> Dict:
        return {'line': self.line, 'character': self.character}


class Range:
    """LSP Range (start, end)"""
    def __init__(self, start: Position, end: Position):
        self.start = start
        self.end = end
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Range':
        return cls(
            Position.from_dict(data['start']),
            Position.from_dict(data['end'])
        )
    
    def to_dict(self) -> Dict:
        return {
            'start': self.start.to_dict(),
            'end': self.end.to_dict()
        }


class Diagnostic:
    """LSP Diagnostic (error/warning)"""
    SEVERITY_ERROR = 1
    SEVERITY_WARNING = 2
    SEVERITY_INFO = 3
    SEVERITY_HINT = 4
    
    def __init__(self, range: Range, message: str, severity: int = SEVERITY_ERROR, code: Optional[str] = None):
        self.range = range
        self.message = message
        self.severity = severity
        self.code = code
    
    def to_dict(self) -> Dict:
        result = {
            'range': self.range.to_dict(),
            'message': self.message,
            'severity': self.severity
        }
        if self.code:
            result['code'] = self.code
        return result


class PyriteLanguageServer:
    """Pyrite Language Server Protocol implementation"""
    
    def __init__(self):
        self.documents: Dict[str, str] = {}  # uri -> content
        self.initialized = False
        self.shutdown_requested = False
        
        # Import compiler components
        try:
            # Add parent to path but NOT src (to avoid conflicts with Python's types module)
            parent_dir = Path(__file__).parent.parent
            
            if str(parent_dir) not in sys.path:
                sys.path.insert(0, str(parent_dir))
            
            # Import using absolute imports from src package
            import src.frontend.lexer as lexer_module
            import src.frontend.parser as parser_module
            import src.middle.type_checker as type_checker_module
            import src.middle.symbol_table as symbol_table_module
            import src.middle.ownership as ownership_module
            
            self.Lexer = lexer_module.Lexer
            self.Parser = parser_module.Parser
            self.TypeChecker = type_checker_module.TypeChecker
            self.SymbolTable = symbol_table_module.SymbolTable
            self.OwnershipAnalyzer = ownership_module.OwnershipAnalyzer
            
            # Import type info utilities
            from lsp.type_info import (
                get_type_badges, calculate_memory_layout,
                estimate_copy_cost, get_ownership_state_info,
                generate_next_risks, is_heap_allocated
            )
            self.get_type_badges = get_type_badges
            self.calculate_memory_layout = calculate_memory_layout
            self.estimate_copy_cost = estimate_copy_cost
            self.get_ownership_state_info = get_ownership_state_info
            self.generate_next_risks = generate_next_risks
            self.is_heap_allocated = is_heap_allocated
            
            logger.info("Compiler components loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load compiler components: {e}")
            raise
    
    def _normalize_line_endings(self, text: str) -> str:
        """Normalize line endings to LF (convert CRLF to LF)"""
        return text.replace('\r\n', '\n').replace('\r', '\n')
    
    def start(self):
        """Start the LSP server (JSON-RPC over stdio)"""
        logger.info("Starting Pyrite LSP Server v2.0.0")
        
        try:
            while not self.shutdown_requested:
                # Read message from stdin
                message = self._read_message()
                if message is None:
                    break
                
                # Handle message
                response = self._handle_message(message)
                
                # Send response
                if response:
                    self._send_message(response)
        
        except KeyboardInterrupt:
            logger.info("Server interrupted")
        except Exception as e:
            logger.error(f"Server error: {e}", exc_info=True)
        finally:
            logger.info("Server shutting down")
    
    def _read_message(self) -> Optional[Dict]:
        """Read JSON-RPC message from stdin"""
        try:
            # Read headers
            headers = {}
            while True:
                line = sys.stdin.buffer.readline().decode('utf-8').strip()
                if not line:
                    break
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            # Read content
            content_length = int(headers.get('Content-Length', 0))
            if content_length == 0:
                return None
            
            content = sys.stdin.buffer.read(content_length).decode('utf-8')
            message = json.loads(content)
            
            logger.debug(f"Received: {message.get('method', 'response')}")
            return message
        
        except Exception as e:
            logger.error(f"Error reading message: {e}")
            return None
    
    def _send_message(self, message: Dict):
        """Send JSON-RPC message to stdout"""
        try:
            content = json.dumps(message)
            content_bytes = content.encode('utf-8')
            content_length = len(content_bytes)
            
            # Write headers
            sys.stdout.buffer.write(f"Content-Length: {content_length}\r\n".encode('utf-8'))
            sys.stdout.buffer.write(b"\r\n")
            
            # Write content
            sys.stdout.buffer.write(content_bytes)
            sys.stdout.buffer.flush()
            
            logger.debug(f"Sent: {message.get('method', 'response')}")
        
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    def _handle_message(self, message: Dict) -> Optional[Dict]:
        """Handle incoming JSON-RPC message"""
        method = message.get('method')
        msg_id = message.get('id')
        params = message.get('params', {})
        
        try:
            # Handle requests (need response)
            if msg_id is not None:
                if method == 'initialize':
                    result = self._handle_initialize(params)
                    return self._make_response(msg_id, result)
                
                elif method == 'shutdown':
                    self.shutdown_requested = True
                    return self._make_response(msg_id, None)
                
                elif method == 'textDocument/hover':
                    result = self._handle_hover(params)
                    return self._make_response(msg_id, result)
                
                elif method == 'textDocument/definition':
                    result = self._handle_definition(params)
                    return self._make_response(msg_id, result)
                
                elif method == 'textDocument/completion':
                    result = self._handle_completion(params)
                    return self._make_response(msg_id, result)
                
                elif method == 'textDocument/documentSymbol':
                    result = self._handle_document_symbol(params)
                    return self._make_response(msg_id, result)
                
                elif method == 'textDocument/references':
                    result = self._handle_references(params)
                    return self._make_response(msg_id, result)
                
                elif method == 'textDocument/rename':
                    result = self._handle_rename(params)
                    return self._make_response(msg_id, result)
                
                elif method == 'workspace/symbol':
                    result = self._handle_workspace_symbol(params)
                    return self._make_response(msg_id, result)
                
                else:
                    logger.warning(f"Unhandled request: {method}")
                    return self._make_error_response(msg_id, -32601, f"Method not found: {method}")
            
            # Handle notifications (no response)
            else:
                if method == 'initialized':
                    self._handle_initialized(params)
                
                elif method == 'exit':
                    sys.exit(0)
                
                elif method == 'textDocument/didOpen':
                    self._handle_did_open(params)
                
                elif method == 'textDocument/didChange':
                    self._handle_did_change(params)
                
                elif method == 'textDocument/didClose':
                    self._handle_did_close(params)
                
                else:
                    logger.debug(f"Unhandled notification: {method}")
                
                return None
        
        except Exception as e:
            logger.error(f"Error handling {method}: {e}", exc_info=True)
            if msg_id is not None:
                return self._make_error_response(msg_id, -32603, str(e))
            return None
    
    def _make_response(self, msg_id: Any, result: Any) -> Dict:
        """Create JSON-RPC response"""
        return {
            'jsonrpc': '2.0',
            'id': msg_id,
            'result': result
        }
    
    def _make_error_response(self, msg_id: Any, code: int, message: str) -> Dict:
        """Create JSON-RPC error response"""
        return {
            'jsonrpc': '2.0',
            'id': msg_id,
            'error': {
                'code': code,
                'message': message
            }
        }
    
    def _handle_initialize(self, params: Dict) -> Dict:
        """Handle initialize request"""
        logger.info(f"Initializing for workspace: {params.get('rootUri', 'unknown')}")
        
        self.initialized = True
        
        return {
            'capabilities': {
                'textDocumentSync': {
                    'openClose': True,
                    'change': 1,  # Full document sync
                    'save': {'includeText': False}
                },
                'hoverProvider': True,
                'definitionProvider': True,
                'referencesProvider': True,
                'completionProvider': {
                    'triggerCharacters': ['.', ':']
                },
                'renameProvider': True,
                'documentSymbolProvider': True,
                'workspaceSymbolProvider': True
            },
            'serverInfo': {
                'name': 'pyrite-lsp',
                'version': '2.0.0'
            }
        }
    
    def _handle_initialized(self, params: Dict):
        """Handle initialized notification"""
        logger.info("Client initialized")
    
    def _handle_did_open(self, params: Dict):
        """Handle textDocument/didOpen"""
        text_document = params['textDocument']
        uri = text_document['uri']
        text = text_document['text']
        
        # Normalize line endings
        text = self._normalize_line_endings(text)
        
        logger.info(f"Document opened: {uri}")
        
        # Store document content
        self.documents[uri] = text
        
        # Analyze and send diagnostics
        diagnostics = self._analyze_document(uri, text)
        self._publish_diagnostics(uri, diagnostics)
    
    def _handle_did_change(self, params: Dict):
        """Handle textDocument/didChange"""
        text_document = params['textDocument']
        uri = text_document['uri']
        changes = params['contentChanges']
        
        # Full document sync (change type 1)
        if changes:
            text = changes[0]['text']
            # Normalize line endings
            text = self._normalize_line_endings(text)
            self.documents[uri] = text
            
            logger.debug(f"Document changed: {uri}")
            
            # Re-analyze and send diagnostics
            diagnostics = self._analyze_document(uri, text)
            self._publish_diagnostics(uri, diagnostics)
    
    def _handle_did_close(self, params: Dict):
        """Handle textDocument/didClose"""
        uri = params['textDocument']['uri']
        
        logger.info(f"Document closed: {uri}")
        
        # Remove from cache
        if uri in self.documents:
            del self.documents[uri]
    
    def _handle_hover(self, params: Dict) -> Optional[Dict]:
        """Handle textDocument/hover"""
        uri = params['textDocument']['uri']
        position = Position.from_dict(params['position'])
        
        logger.debug(f"Hover request at {uri}:{position.line}:{position.character}")
        
        # Get document content
        text = self.documents.get(uri)
        if not text:
            return None
        
        # Normalize line endings
        text = self._normalize_line_endings(text)
        
        # Find symbol at position
        symbol_info = self._get_symbol_at_position(text, position)
        if not symbol_info:
            return None
        
        # Format hover content
        content = self._format_hover_content(symbol_info)
        
        return {
            'contents': {
                'kind': 'markdown',
                'value': content
            }
        }
    
    def _handle_definition(self, params: Dict) -> Optional[Dict]:
        """Handle textDocument/definition"""
        uri = params['textDocument']['uri']
        position = Position.from_dict(params['position'])
        
        logger.debug(f"Definition request at {uri}:{position.line}:{position.character}")
        
        # Get document content
        text = self.documents.get(uri)
        if not text:
            return None
        
        # Normalize line endings
        text = self._normalize_line_endings(text)
        
        # Find symbol at position
        symbol_info = self._get_symbol_at_position(text, position)
        if not symbol_info:
            return None
        
        symbol_name = symbol_info['name']
        
        # Try to find definition in the same file
        try:
            lines = text.split('\n')
            
            # Look for function definition
            for i, line in enumerate(lines):
                if f"fn {symbol_name}(" in line or f"fn {symbol_name}[" in line:
                    return {
                        'uri': uri,
                        'range': Range(
                            Position(i, 0),
                            Position(i, len(line))
                        ).to_dict()
                    }
                
                # Look for variable definition
                if f"let {symbol_name}" in line or f"var {symbol_name}" in line:
                    return {
                        'uri': uri,
                        'range': Range(
                            Position(i, 0),
                            Position(i, len(line))
                        ).to_dict()
                    }
                
                # Look for struct/enum definition
                if f"struct {symbol_name}" in line or f"enum {symbol_name}" in line:
                    return {
                        'uri': uri,
                        'range': Range(
                            Position(i, 0),
                            Position(i, len(line))
                        ).to_dict()
                    }
        
        except Exception as e:
            logger.error(f"Error finding definition: {e}")
        
        return None
    
    def _handle_completion(self, params: Dict) -> Dict:
        """Handle textDocument/completion"""
        uri = params['textDocument']['uri']
        position = Position.from_dict(params['position'])
        
        logger.debug(f"Completion request at {uri}:{position.line}:{position.character}")
        
        # Get document content
        text = self.documents.get(uri)
        if not text:
            return {'items': []}
        
        # Normalize line endings
        text = self._normalize_line_endings(text)
        
        # Get completions
        items = self._get_completions(text, position)
        
        return {'items': items}
    
    def _analyze_document(self, uri: str, text: str) -> List[Diagnostic]:
        """Analyze document and return diagnostics"""
        diagnostics = []
        
        # Normalize line endings
        text = self._normalize_line_endings(text)
        
        try:
            # Lex
            lexer = self.Lexer(text)
            tokens = lexer.tokenize()
            
            # Parse
            parser = self.Parser(tokens)
            ast = parser.parse_program()
            
            # Type check
            type_checker = self.TypeChecker()
            type_checker.check_program(ast)
            
            # Check for type checking errors
            if type_checker.has_errors():
                for error in type_checker.errors:
                    # Extract line number from error span
                    line_num = error.span.start_line - 1 if hasattr(error, 'span') and error.span else 0
                    col_start = error.span.start_column - 1 if hasattr(error, 'span') and error.span else 0
                    col_end = error.span.end_column if hasattr(error, 'span') and error.span else col_start + 100
                    
                    diagnostic = Diagnostic(
                        range=Range(
                            Position(line_num, col_start),
                            Position(line_num, col_end)
                        ),
                        message=str(error),
                        severity=Diagnostic.SEVERITY_ERROR
                    )
                    diagnostics.append(diagnostic)
                
                # Also check resolver errors
                for error_msg in type_checker.resolver.errors:
                    diagnostic = Diagnostic(
                        range=Range(
                            Position(0, 0),
                            Position(0, 100)
                        ),
                        message=error_msg,
                        severity=Diagnostic.SEVERITY_ERROR
                    )
                    diagnostics.append(diagnostic)
            
            logger.debug(f"Analysis successful for {uri}")
        
        except Exception as e:
            # Convert compiler error to diagnostic
            error_msg = str(e)
            
            # Try to extract line number from error
            line_num = 0
            if 'line' in error_msg.lower():
                try:
                    # Simple extraction (improve later)
                    parts = error_msg.split('line')
                    if len(parts) > 1:
                        num_str = ''.join(c for c in parts[1].split()[0] if c.isdigit())
                        if num_str:
                            line_num = int(num_str) - 1  # LSP is 0-indexed
                except:
                    pass
            
            # Create diagnostic
            diagnostic = Diagnostic(
                range=Range(
                    Position(line_num, 0),
                    Position(line_num, 100)
                ),
                message=error_msg,
                severity=Diagnostic.SEVERITY_ERROR
            )
            diagnostics.append(diagnostic)
            
            logger.debug(f"Analysis error for {uri}: {error_msg}")
        
        return diagnostics
    
    def _publish_diagnostics(self, uri: str, diagnostics: List[Diagnostic]):
        """Publish diagnostics to client"""
        message = {
            'jsonrpc': '2.0',
            'method': 'textDocument/publishDiagnostics',
            'params': {
                'uri': uri,
                'diagnostics': [d.to_dict() for d in diagnostics]
            }
        }
        self._send_message(message)
    
    def _get_symbol_at_position(self, text: str, position: Position) -> Optional[Dict]:
        """Get symbol information at position"""
        try:
            # Split into lines
            lines = text.split('\n')
            if position.line >= len(lines):
                return None
            
            line = lines[position.line]
            if position.character >= len(line):
                return None
            
            # First, try to detect literals by tokenizing the line
            # This handles string literals (with quotes) and number literals
            try:
                from src.frontend.tokens import TokenType
                
                # Tokenize just this line to find what's at the position
                line_text = line
                lexer = self.Lexer(line_text)
                tokens = lexer.tokenize()
                
                # Find token that contains the hover position
                for token in tokens:
                    if token.span:
                        token_start_col = token.span.start_column - 1  # Convert to 0-indexed
                        token_end_col = token.span.end_column  # Already 1-indexed, but we'll use it as-is
                        
                        # Check if position is within this token
                        if token_start_col <= position.character < token_end_col:
                            # Check if it's a literal
                            if token.type == TokenType.INTEGER:
                                value = token.value
                                return {
                                    'name': str(value),
                                    'type': 'int',
                                    'type_obj': None,
                                    'kind': 'literal',
                                    'ownership_state': None,
                                    'literal_value': value,
                                    'literal_type': 'integer'
                                }
                            elif token.type == TokenType.FLOAT:
                                value = token.value
                                return {
                                    'name': str(value),
                                    'type': 'f64',
                                    'type_obj': None,
                                    'kind': 'literal',
                                    'ownership_state': None,
                                    'literal_value': value,
                                    'literal_type': 'float'
                                }
                            elif token.type == TokenType.STRING:
                                value = token.value
                                return {
                                    'name': f'"{value}"',
                                    'type': 'String',
                                    'type_obj': None,
                                    'kind': 'literal',
                                    'ownership_state': None,
                                    'literal_value': value,
                                    'literal_type': 'string'
                                }
                            elif token.type == TokenType.CHAR:
                                value = token.value
                                return {
                                    'name': f"'{value}'",
                                    'type': 'char',
                                    'type_obj': None,
                                    'kind': 'literal',
                                    'ownership_state': None,
                                    'literal_value': value,
                                    'literal_type': 'char'
                                }
                            elif token.type == TokenType.TRUE:
                                return {
                                    'name': 'true',
                                    'type': 'bool',
                                    'type_obj': None,
                                    'kind': 'literal',
                                    'ownership_state': None,
                                    'literal_value': True,
                                    'literal_type': 'boolean'
                                }
                            elif token.type == TokenType.FALSE:
                                return {
                                    'name': 'false',
                                    'type': 'bool',
                                    'type_obj': None,
                                    'kind': 'literal',
                                    'ownership_state': None,
                                    'literal_value': False,
                                    'literal_type': 'boolean'
                                }
                            elif token.type == TokenType.NONE:
                                return {
                                    'name': 'None',
                                    'type': 'None',
                                    'type_obj': None,
                                    'kind': 'literal',
                                    'ownership_state': None,
                                    'literal_value': None,
                                    'literal_type': 'none'
                                }
            except Exception as e:
                logger.debug(f"Error detecting literal: {e}")
            
            # Find word at position (for non-literal symbols)
            start = position.character
            end = position.character
            
            # Expand left
            while start > 0 and (line[start - 1].isalnum() or line[start - 1] == '_'):
                start -= 1
            
            # Expand right
            while end < len(line) and (line[end].isalnum() or line[end] == '_'):
                end += 1
            
            if start == end:
                return None
            
            symbol_name = line[start:end]
            
            # Check if it's a built-in type - provide type information
            try:
                from src.types import primitive_type_from_name
                builtin_type = primitive_type_from_name(symbol_name)
                if builtin_type:
                    # Get type information
                    type_docs = {
                        'int': '**int** - 32-bit signed integer\n\n**Size**: 4 bytes\n**Range**: -2,147,483,648 to 2,147,483,647\n**Copy**: Yes (Copy type)\n\nDefault integer type in Pyrite.',
                        'i8': '**i8** - 8-bit signed integer\n\n**Size**: 1 byte\n**Range**: -128 to 127\n**Copy**: Yes',
                        'i16': '**i16** - 16-bit signed integer\n\n**Size**: 2 bytes\n**Range**: -32,768 to 32,767\n**Copy**: Yes',
                        'i32': '**i32** - 32-bit signed integer\n\n**Size**: 4 bytes\n**Range**: -2,147,483,648 to 2,147,483,647\n**Copy**: Yes',
                        'i64': '**i64** - 64-bit signed integer\n\n**Size**: 8 bytes\n**Range**: -9,223,372,036,854,775,808 to 9,223,372,036,854,775,807\n**Copy**: Yes',
                        'u8': '**u8** - 8-bit unsigned integer\n\n**Size**: 1 byte\n**Range**: 0 to 255\n**Copy**: Yes',
                        'u16': '**u16** - 16-bit unsigned integer\n\n**Size**: 2 bytes\n**Range**: 0 to 65,535\n**Copy**: Yes',
                        'u32': '**u32** - 32-bit unsigned integer\n\n**Size**: 4 bytes\n**Range**: 0 to 4,294,967,295\n**Copy**: Yes',
                        'u64': '**u64** - 64-bit unsigned integer\n\n**Size**: 8 bytes\n**Range**: 0 to 18,446,744,073,709,551,615\n**Copy**: Yes',
                        'f32': '**f32** - 32-bit floating point\n\n**Size**: 4 bytes\n**Precision**: ~7 decimal digits\n**Copy**: Yes',
                        'f64': '**f64** - 64-bit floating point\n\n**Size**: 8 bytes\n**Precision**: ~15 decimal digits\n**Copy**: Yes',
                        'bool': '**bool** - Boolean type\n\n**Size**: 1 byte\n**Values**: `true`, `false`\n**Copy**: Yes',
                        'char': '**char** - Unicode character\n\n**Size**: 4 bytes (UTF-32)\n**Copy**: Yes',
                        'String': '**String** - UTF-8 string\n\n**Size**: 16 bytes (pointer + length)\n**Heap**: Yes (variable size)\n**Copy**: No (Move type)\n\nOwned string type. Heap-allocated buffer.',
                        'void': '**void** - No return value\n\nUsed as function return type when function returns nothing.',
                        'Self': '**Self** - Self type\n\nRefers to the current type in impl blocks and traits.',
                    }
                    
                    type_doc = type_docs.get(symbol_name, f'**{symbol_name}** - Built-in type')
                    
                    return {
                        'name': symbol_name,
                        'type': str(builtin_type),
                        'type_obj': builtin_type,
                        'kind': 'type',
                        'ownership_state': None,
                        'type_doc': type_doc
                    }
            except Exception as e:
                logger.debug(f"Error checking built-in type: {e}")
            
            # Check if it's a keyword - provide helpful documentation
            keyword_docs = {
                'let': '**let** - Declares an immutable variable\n\n`let name = value`\n\nCreates an immutable binding. The value cannot be reassigned.',
                'var': '**var** - Declares a mutable variable\n\n`var name = value`\n\nThe value can be reassigned later.',
                'const': '**const** - Declares a compile-time constant\n\n`const NAME = value`\n\nMust be known at compile time. Cannot be reassigned.',
                'fn': '**fn** - Function declaration\n\n`fn name(params) -> return_type:`\n\nDefines a function with parameters and optional return type.',
                'struct': '**struct** - Structure definition\n\n`struct Name:\n    field: Type`\n\nDefines a custom data type with named fields.',
                'enum': '**enum** - Enumeration definition\n\n`enum Name:\n    Variant1\n    Variant2(value)`\n\nDefines a sum type with variants.',
                'impl': '**impl** - Implementation block\n\n`impl Type:\n    fn method(self):`\n\nAdds methods to a type.',
                'trait': '**trait** - Trait definition\n\n`trait Name:\n    fn method(self):`\n\nDefines an interface that types can implement.',
                'if': '**if** - Conditional statement\n\n`if condition:\n    ...`\n\nExecutes code if condition is true.',
                'elif': '**elif** - Else-if clause\n\n`elif condition:\n    ...`\n\nAlternative condition after if.',
                'else': '**else** - Else clause\n\n`else:\n    ...`\n\nExecutes when all conditions are false.',
                'while': '**while** - While loop\n\n`while condition:\n    ...`\n\nRepeats while condition is true.',
                'for': '**for** - For loop\n\n`for item in iterable:\n    ...`\n\nIterates over a collection.',
                'in': '**in** - Membership operator\n\n`for item in collection:`\n\nUsed in for loops and pattern matching.',
                'match': '**match** - Pattern matching\n\n`match value:\n    pattern => result`\n\nPattern matching expression.',
                'return': '**return** - Return statement\n\n`return value`\n\nReturns a value from a function.',
                'break': '**break** - Break statement\n\n`break`\n\nExits the innermost loop.',
                'continue': '**continue** - Continue statement\n\n`continue`\n\nSkips to next iteration of loop.',
                'import': '**import** - Import statement\n\n`import module`\n\nImports a module or type.',
                'from': '**from** - Import from\n\n`from module import item`\n\nImports specific items from a module.',
                'as': '**as** - Alias\n\n`import module as alias`\n\nCreates an alias for an import.',
                'unsafe': '**unsafe** - Unsafe block\n\n`unsafe:\n    ...`\n\nAllows unsafe operations (raw pointers, FFI).',
                'defer': '**defer** - Defer statement\n\n`defer cleanup()`\n\nExecutes cleanup when scope exits.',
                'with': '**with** - With statement\n\n`with resource:\n    ...`\n\nAutomatic resource management.',
                'try': '**try** - Try block\n\n`try:\n    ...`\n\nError handling block.',
                'extern': '**extern** - External function\n\n`extern fn name() -> Type`\n\nDeclares external C function.',
                'and': '**and** - Logical AND\n\n`condition1 and condition2`\n\nReturns true if both are true.',
                'or': '**or** - Logical OR\n\n`condition1 or condition2`\n\nReturns true if either is true.',
                'not': '**not** - Logical NOT\n\n`not condition`\n\nNegates a boolean value.',
                'True': '**True** - Boolean true\n\nLiteral boolean value representing true.',
                'False': '**False** - Boolean false\n\nLiteral boolean value representing false.',
                'None': '**None** - None value\n\nRepresents absence of a value (like null).',
            }
            
            if symbol_name in keyword_docs:
                return {
                    'name': symbol_name,
                    'type': 'keyword',
                    'type_obj': None,
                    'kind': 'keyword',
                    'ownership_state': None,
                    'keyword_doc': keyword_docs[symbol_name]
                }
            
            # Try to get type information from compiler
            ownership_state = None
            try:
                # Import AST module (if not already imported at module level)
                from src import ast as ast_module
                from src.frontend.tokens import Span
                from src.types import UNKNOWN
                
                lexer = self.Lexer(text)
                tokens = lexer.tokenize()
                parser = self.Parser(tokens)
                ast = parser.parse_program()
                
                type_checker = self.TypeChecker()
                type_checker.check_program(ast)
                
                # Find the function containing this position
                containing_func = None
                for item in ast.items:
                    if isinstance(item, ast_module.FunctionDef):
                        # Check if position is within this function's span
                        if hasattr(item, 'span') and item.span:
                            func_start_line = item.span.start_line - 1  # Convert to 0-indexed
                            func_end_line = item.span.end_line - 1 if item.span.end_line else func_start_line + 100
                            if func_start_line <= position.line <= func_end_line:
                                containing_func = item
                                break
                
                # Try to get type using type checker's check_identifier method
                # Create a temporary identifier AST node
                # Create a span for the identifier (at the hover position)
                ident_span = Span(
                    filename="<hover>",
                    start_line=position.line + 1,  # Convert back to 1-indexed
                    start_column=start + 1,
                    end_line=position.line + 1,
                    end_column=end + 1
                )
                ident_node = ast_module.Identifier(name=symbol_name, span=ident_span)
                
                # If we're in a function, we need to check the identifier in that context
                typ = None
                symbol = None
                
                if containing_func:
                    # Re-enter function scope and check identifier
                    type_checker.resolver.enter_scope()
                    try:
                        # Define function parameters
                        for param in containing_func.params:
                            if param.type_annotation:
                                param_type = type_checker.resolve_type(param.type_annotation)
                                type_checker.resolver.define_variable(param.name, param_type, False, param.span)
                        
                        # Check function body to populate variable scope
                        type_checker.check_block(containing_func.body)
                        
                        # Now check the identifier
                        typ = type_checker.check_identifier(ident_node)
                        logger.debug(f"check_identifier returned: {typ} for {symbol_name}")
                        if typ and typ != UNKNOWN:
                            # Get the symbol for additional info
                            symbol = type_checker.resolver.current_scope.lookup(symbol_name)
                            logger.debug(f"Found symbol: {symbol}")
                    finally:
                        type_checker.resolver.exit_scope()
                
                # If not found in function, try global scope
                if not typ or typ == UNKNOWN:
                    # Check as function first
                    symbol = type_checker.resolver.global_scope.lookup_function(symbol_name)
                    if symbol:
                        typ = symbol.type
                    else:
                        # Try as variable in global scope
                        symbol = type_checker.resolver.global_scope.lookup(symbol_name)
                        if symbol:
                            typ = symbol.type
                        else:
                            # Last resort: use check_identifier on global scope
                            typ = type_checker.check_identifier(ident_node)
                
                # Run ownership analysis
                ownership_state = None
                try:
                    ownership_analyzer = self.OwnershipAnalyzer()
                    ownership_analyzer.type_checker = type_checker
                    if containing_func:
                        ownership_analyzer.collect_variable_types(containing_func)
                        ownership_analyzer.analyze_function(containing_func)
                        ownership_state = ownership_analyzer.state
                except Exception as e:
                    logger.debug(f"Ownership analysis failed: {e}")
                
                if symbol or (typ and typ != UNKNOWN):
                    if not typ:
                        typ = symbol.type if symbol and hasattr(symbol, 'type') else None
                    return {
                        'name': symbol_name,
                        'type': str(typ) if typ else 'unknown',
                        'type_obj': typ,  # Store actual type object
                        'kind': symbol.kind if symbol and hasattr(symbol, 'kind') else 'variable',
                        'ownership_state': ownership_state
                    }
                else:
                    logger.debug(f"Symbol {symbol_name} not found. typ={typ}, symbol={symbol}")
            except Exception as e:
                logger.error(f"Type checking failed: {e}", exc_info=True)
            
            # Return basic info
            return {
                'name': symbol_name,
                'type': 'unknown',
                'type_obj': None,
                'kind': 'variable',
                'ownership_state': None
            }
        
        except Exception as e:
            logger.error(f"Error getting symbol: {e}")
            return None
    
    def _format_hover_content(self, symbol_info: Dict) -> str:
        """Format hover content as Markdown with comprehensive information"""
        name = symbol_info['name']
        type_str = symbol_info['type']
        kind = symbol_info.get('kind', 'variable')
        typ = symbol_info.get('type_obj')
        ownership_state = symbol_info.get('ownership_state')
        
        # Handle keywords specially
        if kind == 'keyword' and 'keyword_doc' in symbol_info:
            return symbol_info['keyword_doc']
        
        # Handle built-in types specially
        if kind == 'type' and 'type_doc' in symbol_info:
            return symbol_info['type_doc']
        
        # Handle literals specially
        if kind == 'literal':
            literal_type = symbol_info.get('literal_type')
            literal_value = symbol_info.get('literal_value')
            type_str = symbol_info['type']
            
            if literal_type == 'integer':
                return f"**Integer Literal**\n\n```pyrite\n{literal_value}: int\n```\n\n**Type**: `int` (32-bit signed integer)\n**Size**: 4 bytes\n**Copy**: Yes\n**Value**: `{literal_value}`"
            elif literal_type == 'float':
                return f"**Float Literal**\n\n```pyrite\n{literal_value}: f64\n```\n\n**Type**: `f64` (64-bit floating point)\n**Size**: 8 bytes\n**Precision**: ~15 decimal digits\n**Copy**: Yes\n**Value**: `{literal_value}`"
            elif literal_type == 'string':
                return f"**String Literal**\n\n```pyrite\n\"{literal_value}\": String\n```\n\n**Type**: `String` (UTF-8 string)\n**Size**: 16 bytes (pointer + length) + {len(literal_value.encode('utf-8'))} bytes heap\n**Heap**: Yes\n**Copy**: No (Move type)\n**Length**: {len(literal_value)} characters\n**Value**: `\"{literal_value}\"`"
            elif literal_type == 'char':
                return f"**Character Literal**\n\n```pyrite\n'{literal_value}': char\n```\n\n**Type**: `char` (Unicode character)\n**Size**: 4 bytes (UTF-32)\n**Copy**: Yes\n**Value**: `'{literal_value}'`"
            elif literal_type == 'boolean':
                return f"**Boolean Literal**\n\n```pyrite\n{literal_value}: bool\n```\n\n**Type**: `bool`\n**Size**: 1 byte\n**Copy**: Yes\n**Value**: `{literal_value}`"
            elif literal_type == 'none':
                return f"**None Literal**\n\n```pyrite\nNone: None\n```\n\n**Type**: `None`\n**Represents**: Absence of a value\n**Value**: `None`"
            else:
                return f"**Literal**\n\n```pyrite\n{name}: {type_str}\n```\n\n**Value**: `{literal_value}`"
        
        # Start with type signature
        content = f"```pyrite\n{name}: {type_str}\n```\n\n"
        
        # Collect all information first, then format nicely
        sections = []
        
        # Type badges (if available)
        if typ:
            try:
                badges = self.get_type_badges(typ)
                if badges:
                    # Format badges more readably
                    badge_text = " ".join(badges)
                    sections.append(("Badges", badge_text))
            except Exception as e:
                logger.debug(f"Error getting badges: {e}")
        
        # Ownership state
        ownership_info = None
        if ownership_state:
            try:
                ownership_info = self.get_ownership_state_info(name, ownership_state)
                state = ownership_info['state']
                if state == 'owned':
                    sections.append(("Ownership", "Owned"))
                elif state == 'moved':
                    moved_to = ownership_info.get('moved_to')
                    if moved_to:
                        sections.append(("Ownership", f"Moved to `{moved_to}`"))
                    else:
                        sections.append(("Ownership", "Moved"))
                elif state == 'borrowed':
                    sections.append(("Ownership", "Borrowed"))
            except Exception as e:
                logger.debug(f"Error getting ownership info: {e}")
        
        # Memory layout
        memory_info = []
        if typ:
            try:
                stack_bytes, heap_bytes = self.calculate_memory_layout(typ)
                if stack_bytes > 0:
                    memory_info.append(f"Stack: {stack_bytes} bytes")
                if heap_bytes > 0:
                    memory_info.append(f"Heap: {heap_bytes} bytes")
                elif self.is_heap_allocated(typ):
                    memory_info.append("Heap: variable size")
                
                if memory_info:
                    sections.append(("Memory", ", ".join(memory_info)))
            except Exception as e:
                logger.debug(f"Error calculating memory layout: {e}")
        
        # Copy cost
        if typ:
            try:
                copy_cost = self.estimate_copy_cost(typ)
                sections.append(("Copy Cost", copy_cost))
            except Exception as e:
                logger.debug(f"Error estimating copy cost: {e}")
        
        # Format sections nicely - ensure each property is on its own line
        # Use single newline for line breaks (markdown will render these as separate lines)
        if sections:
            for i, (label, value) in enumerate(sections):
                content += f"**{label}**: {value}"
                if i < len(sections) - 1:  # Add newline between items, but not after last
                    content += "\n"
            content += "\n"  # Final newline after all sections
        
        # Add next risks (if any)
        if typ and ownership_state and ownership_info:
            try:
                risks = self.generate_next_risks(typ, ownership_info, name)
                if risks:
                    content += "**Next Risks:**\n"
                    for risk in risks:
                        content += f"  {risk}\n"
            except Exception as e:
                logger.debug(f"Error generating risks: {e}")
        
        return content.rstrip()  # Remove trailing whitespace
    
    def _get_completions(self, text: str, position: Position) -> List[Dict]:
        """Get completion items"""
        items = []
        
        # Keywords
        keywords = [
            'fn', 'let', 'var', 'const', 'if', 'elif', 'else',
            'while', 'for', 'in', 'match', 'return', 'break', 'continue',
            'struct', 'enum', 'trait', 'impl', 'defer', 'with', 'try',
            'true', 'false', 'None', 'unsafe', 'extern'
        ]
        
        for kw in keywords:
            items.append({
                'label': kw,
                'kind': 14,  # Keyword
                'detail': 'keyword',
                'insertText': kw
            })
        
        # Types
        types = ['int', 'i32', 'i64', 'u32', 'u64', 'f32', 'f64', 'bool', 'str', 'String', 'List', 'Map', 'Set']
        
        for ty in types:
            items.append({
                'label': ty,
                'kind': 7,  # Class (type)
                'detail': 'type',
                'insertText': ty
            })
        
        return items
    
    def _handle_document_symbol(self, params: Dict) -> List[Dict]:
        """Handle textDocument/documentSymbol - returns outline/symbol list"""
        uri = params['textDocument']['uri']
        
        # Get document content
        text = self.documents.get(uri)
        if not text:
            return []
        
        # Normalize line endings
        text = self._normalize_line_endings(text)
        
        symbols = []
        
        try:
            # Import AST module
            from src import ast as ast_module
            
            # Parse the document
            lexer = self.Lexer(text)
            tokens = lexer.tokenize()
            parser = self.Parser(tokens)
            ast = parser.parse_program()
            
            # Extract symbols from AST
            for item in ast.items:
                if isinstance(item, ast_module.FunctionDef):
                    # Function symbol
                    start_line = item.span.start_line - 1 if item.span else 0
                    start_col = item.span.start_column - 1 if item.span else 0
                    end_line = item.span.end_line - 1 if item.span and item.span.end_line else start_line
                    end_col = item.span.end_column if item.span else start_col + len(item.name)
                    
                    symbol = {
                        'name': item.name,
                        'kind': 12,  # Function
                        'location': {
                            'uri': uri,
                            'range': Range(
                                Position(start_line, start_col),
                                Position(end_line, end_col)
                            ).to_dict()
                        },
                        'detail': self._format_function_signature(item),
                        'children': []  # Variables inside function (can be added later)
                    }
                    symbols.append(symbol)
                
                elif isinstance(item, ast_module.StructDef):
                    # Struct symbol
                    start_line = item.span.start_line - 1 if item.span else 0
                    start_col = item.span.start_column - 1 if item.span else 0
                    end_line = item.span.end_line - 1 if item.span and item.span.end_line else start_line
                    end_col = item.span.end_column if item.span else start_col + len(item.name)
                    
                    # Collect field symbols as children
                    children = []
                    for field in item.fields:
                        field_start = field.span.start_line - 1 if field.span else start_line
                        field_start_col = field.span.start_column - 1 if field.span else 0
                        field_end = field.span.end_line - 1 if field.span and field.span.end_line else field_start
                        field_end_col = field.span.end_column if field.span else field_start_col + len(field.name)
                        
                        children.append({
                            'name': field.name,
                            'kind': 7,  # Property/Field
                            'location': {
                                'uri': uri,
                                'range': Range(
                                    Position(field_start, field_start_col),
                                    Position(field_end, field_end_col)
                                ).to_dict()
                            }
                        })
                    
                    symbol = {
                        'name': item.name,
                        'kind': 23,  # Struct
                        'location': {
                            'uri': uri,
                            'range': Range(
                                Position(start_line, start_col),
                                Position(end_line, end_col)
                            ).to_dict()
                        },
                        'children': children
                    }
                    symbols.append(symbol)
                
                elif isinstance(item, ast_module.EnumDef):
                    # Enum symbol
                    start_line = item.span.start_line - 1 if item.span else 0
                    start_col = item.span.start_column - 1 if item.span else 0
                    end_line = item.span.end_line - 1 if item.span and item.span.end_line else start_line
                    end_col = item.span.end_column if item.span else start_col + len(item.name)
                    
                    # Collect variant symbols as children
                    children = []
                    for variant in item.variants:
                        variant_start = variant.span.start_line - 1 if variant.span else start_line
                        variant_start_col = variant.span.start_column - 1 if variant.span else 0
                        variant_end = variant.span.end_line - 1 if variant.span and variant.span.end_line else variant_start
                        variant_end_col = variant.span.end_column if variant.span else variant_start_col + len(variant.name)
                        
                        children.append({
                            'name': variant.name,
                            'kind': 20,  # EnumMember
                            'location': {
                                'uri': uri,
                                'range': Range(
                                    Position(variant_start, variant_start_col),
                                    Position(variant_end, variant_end_col)
                                ).to_dict()
                            }
                        })
                    
                    symbol = {
                        'name': item.name,
                        'kind': 11,  # Enum
                        'location': {
                            'uri': uri,
                            'range': Range(
                                Position(start_line, start_col),
                                Position(end_line, end_col)
                            ).to_dict()
                        },
                        'children': children
                    }
                    symbols.append(symbol)
            
        except Exception as e:
            logger.debug(f"Error extracting document symbols: {e}")
        
        return symbols
    
    def _format_function_signature(self, func) -> str:
        """Format function signature for symbol detail"""
        from src import ast as ast_module
        params_str = ', '.join([f"{p.name}: {self._format_type(p.type_annotation)}" for p in func.params])
        return_type_str = f" -> {self._format_type(func.return_type)}" if func.return_type else ""
        return f"fn {func.name}({params_str}){return_type_str}"
    
    def _format_type(self, type_ann) -> str:
        """Format type annotation to string"""
        if type_ann is None:
            return ""
        # Simple string representation - can be enhanced
        if hasattr(type_ann, 'name'):
            return type_ann.name
        return str(type_ann)
    
    def _handle_references(self, params: Dict) -> List[Dict]:
        """Handle textDocument/references - find all references to a symbol"""
        uri = params['textDocument']['uri']
        position = Position.from_dict(params['position'])
        include_declaration = params.get('context', {}).get('includeDeclaration', True)
        
        # Get document content
        text = self.documents.get(uri)
        if not text:
            return []
        
        # Normalize line endings
        text = self._normalize_line_endings(text)
        
        # Find symbol name at position
        lines = text.split('\n')
        if position.line >= len(lines):
            return []
        
        line = lines[position.line]
        if position.character >= len(line):
            return []
        
        # Extract symbol name
        start = position.character
        end = position.character
        
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == '_'):
            start -= 1
        while end < len(line) and (line[end].isalnum() or line[end] == '_'):
            end += 1
        
        if start == end:
            return []
        
        symbol_name = line[start:end]
        references = []
        
        try:
            # Search for all occurrences of this symbol in the document
            for line_num, line_text in enumerate(lines):
                # Simple text search (can be enhanced with AST analysis)
                search_start = 0
                while True:
                    idx = line_text.find(symbol_name, search_start)
                    if idx == -1:
                        break
                    
                    # Check if it's a whole word (not part of another identifier)
                    if (idx == 0 or not (line_text[idx - 1].isalnum() or line_text[idx - 1] == '_')) and \
                       (idx + len(symbol_name) >= len(line_text) or not (line_text[idx + len(symbol_name)].isalnum() or line_text[idx + len(symbol_name)] == '_')):
                        
                        # Check if this is the definition (if include_declaration is False, skip it)
                        is_definition = ('fn ' + symbol_name in line_text or 
                                        'let ' + symbol_name in line_text or 
                                        'var ' + symbol_name in line_text or
                                        'struct ' + symbol_name in line_text or
                                        'enum ' + symbol_name in line_text)
                        
                        if include_declaration or not is_definition:
                            references.append({
                                'uri': uri,
                                'range': Range(
                                    Position(line_num, idx),
                                    Position(line_num, idx + len(symbol_name))
                                ).to_dict()
                            })
                    
                    search_start = idx + 1
        
        except Exception as e:
            logger.debug(f"Error finding references: {e}")
        
        return references
    
    def _handle_rename(self, params: Dict) -> Dict:
        """Handle textDocument/rename - rename symbol"""
        uri = params['textDocument']['uri']
        position = Position.from_dict(params['position'])
        new_name = params['newName']
        
        # Get document content
        text = self.documents.get(uri)
        if not text:
            return {'changes': {}}
        
        # Normalize line endings
        text = self._normalize_line_endings(text)
        
        # Find symbol name at position (same logic as references)
        lines = text.split('\n')
        if position.line >= len(lines):
            return {'changes': {}}
        
        line = lines[position.line]
        if position.character >= len(line):
            return {'changes': {}}
        
        # Extract symbol name
        start = position.character
        end = position.character
        
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == '_'):
            start -= 1
        while end < len(line) and (line[end].isalnum() or line[end] == '_'):
            end += 1
        
        if start == end:
            return {'changes': {}}
        
        old_name = line[start:end]
        
        # Find all references (reuse references logic)
        references_params = {
            'textDocument': {'uri': uri},
            'position': position.to_dict(),
            'context': {'includeDeclaration': True}
        }
        references = self._handle_references(references_params)
        
        # Build edit changes
        text_edits = []
        for ref in references:
            text_edits.append({
                'range': ref['range'],
                'newText': new_name
            })
        
        return {
            'changes': {
                uri: text_edits
            }
        }
    
    def _handle_workspace_symbol(self, params: Dict) -> List[Dict]:
        """Handle workspace/symbol - search symbols across workspace"""
        query = params.get('query', '')
        
        # For MVP, search in all open documents
        # In a full implementation, this would index all files in the workspace
        symbols = []
        
        for uri, text in self.documents.items():
            # Normalize line endings
            text = self._normalize_line_endings(text)
            
            try:
                # Import AST module
                from src import ast as ast_module
                
                # Parse document
                lexer = self.Lexer(text)
                tokens = lexer.tokenize()
                parser = self.Parser(tokens)
                ast = parser.parse_program()
                
                # Search for symbols matching query
                for item in ast.items:
                    if isinstance(item, ast_module.FunctionDef):
                        if query.lower() in item.name.lower():
                            start_line = item.span.start_line - 1 if item.span else 0
                            start_col = item.span.start_column - 1 if item.span else 0
                            
                            symbols.append({
                                'name': item.name,
                                'kind': 12,  # Function
                                'location': {
                                    'uri': uri,
                                    'range': Range(
                                        Position(start_line, start_col),
                                        Position(start_line, start_col + len(item.name))
                                    ).to_dict()
                                }
                            })
                    
                    elif isinstance(item, ast_module.StructDef):
                        if query.lower() in item.name.lower():
                            start_line = item.span.start_line - 1 if item.span else 0
                            start_col = item.span.start_column - 1 if item.span else 0
                            
                            symbols.append({
                                'name': item.name,
                                'kind': 23,  # Struct
                                'location': {
                                    'uri': uri,
                                    'range': Range(
                                        Position(start_line, start_col),
                                        Position(start_line, start_col + len(item.name))
                                    ).to_dict()
                                }
                            })
            
            except Exception as e:
                logger.debug(f"Error searching workspace symbols in {uri}: {e}")
        
        return symbols


def main():
    """Main entry point for LSP server"""
    server = PyriteLanguageServer()
    server.start()


if __name__ == '__main__':
    main()

