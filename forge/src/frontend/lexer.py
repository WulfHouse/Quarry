"""Lexer for Pyrite programming language.

This module provides lexical analysis (tokenization) for Pyrite source code.
It converts source code text into a stream of tokens that can be consumed by the parser.

Main Components:
    Lexer: Main lexer class that tokenizes source code
    lex(): Convenience function to tokenize source code
    LexerError: Exception raised on lexing errors

See Also:
    parser: Parses tokens into an Abstract Syntax Tree
    tokens: Token definitions and utilities
"""

from typing import List, Optional
from .tokens import Token, TokenType, Span, KEYWORDS


class LexerError(Exception):
    """Lexer error exception"""
    def __init__(self, message: str, span: Span):
        self.message = message
        self.span = span
        super().__init__(f"{span}: {message}")


class Lexer:
    """Tokenizer for Pyrite source code"""
    
    def __init__(self, source: str, filename: str = "<input>"):
        self.source = source
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1
        self.indent_stack = [0]  # Track indentation levels
        self.pending_tokens = []  # Queue for DEDENT tokens
        self.at_line_start = True  # Track if we're at the start of a line
        
    def peek(self, offset: int = 0) -> str:
        """Peek at character without consuming"""
        pos = self.pos + offset
        if pos >= len(self.source):
            return '\0'
        return self.source[pos]
    
    def advance(self) -> str:
        """Consume and return current character"""
        if self.pos >= len(self.source):
            return '\0'
        
        char = self.source[self.pos]
        self.pos += 1
        
        if char == '\n':
            self.line += 1
            self.column = 1
            self.at_line_start = True
        else:
            self.column += 1
        
        return char
    
    def make_span(self, start_line: int, start_column: int) -> Span:
        """Create a span from start position to current position"""
        return Span(
            self.filename,
            start_line,
            start_column,
            self.line,
            self.column
        )
    
    def skip_whitespace(self):
        """Skip spaces and tabs (but not newlines)"""
        while self.peek() in ' \t':
            self.advance()
    
    def skip_comment(self):
        """Skip single-line comment"""
        if self.peek() == '#':
            while self.peek() != '\n' and self.peek() != '\0':
                self.advance()
    
    def handle_indentation(self) -> List[Token]:
        """Handle indentation at the start of a line"""
        if not self.at_line_start:
            return []
        
        # Count leading spaces
        indent_level = 0
        while self.peek() in ' \t':
            if self.peek() == ' ':
                indent_level += 1
            else:  # tab
                indent_level += 4  # Tab counts as 4 spaces
            self.advance()
        
        # Skip blank lines and comments
        if self.peek() == '\n' or self.peek() == '#':
            return []
        
        self.at_line_start = False
        current_level = self.indent_stack[-1]
        tokens = []
        
        if indent_level > current_level:
            # Increased indentation
            self.indent_stack.append(indent_level)
            start_line = self.line
            start_col = self.column - indent_level
            tokens.append(Token(
                TokenType.INDENT,
                None,
                self.make_span(start_line, start_col)
            ))
        elif indent_level < current_level:
            # Decreased indentation - may need multiple DEDENT tokens
            while self.indent_stack[-1] > indent_level:
                self.indent_stack.pop()
                tokens.append(Token(
                    TokenType.DEDENT,
                    None,
                    self.make_span(self.line, self.column)
                ))
            
            # Check for indentation error
            if self.indent_stack[-1] != indent_level:
                raise LexerError(
                    f"Indentation doesn't match any outer level",
                    self.make_span(self.line, 1)
                )
        
        return tokens
    
    def lex_identifier(self) -> Token:
        """Lex an identifier or keyword"""
        start_line = self.line
        start_col = self.column
        
        result = ""
        while self.peek().isalnum() or self.peek() == '_':
            result += self.advance()
        
        # Check if it's a keyword
        token_type = KEYWORDS.get(result, TokenType.IDENTIFIER)
        
        # For keywords, value is None; for identifiers, value is the name
        value = None if token_type != TokenType.IDENTIFIER else result
        
        return Token(token_type, value, self.make_span(start_line, start_col))
    
    def lex_number(self) -> Token:
        """Lex a number (integer or float)"""
        start_line = self.line
        start_col = self.column
        
        # Handle different bases
        if self.peek() == '0':
            next_char = self.peek(1)
            if next_char == 'x':
                return self.lex_hex_number(start_line, start_col)
            elif next_char == 'b':
                return self.lex_binary_number(start_line, start_col)
            elif next_char == 'o':
                return self.lex_octal_number(start_line, start_col)
        
        # Decimal number
        result = ""
        has_dot = False
        has_exp = False
        
        while True:
            char = self.peek()
            
            if char.isdigit() or char == '_':
                if char != '_':
                    result += char
                self.advance()
            elif char == '.' and not has_dot and not has_exp and self.peek(1).isdigit():
                has_dot = True
                result += char
                self.advance()
            elif char in 'eE' and not has_exp:
                has_exp = True
                has_dot = True  # Exponential notation makes it a float
                result += char
                self.advance()
                # Handle optional +/- after exponent
                if self.peek() in '+-':
                    result += self.advance()
            else:
                break
        
        span = self.make_span(start_line, start_col)
        
        if has_dot or has_exp:
            try:
                return Token(TokenType.FLOAT, float(result), span)
            except ValueError:
                raise LexerError(f"Invalid float literal: {result}", span)
        else:
            try:
                return Token(TokenType.INTEGER, int(result), span)
            except ValueError:
                raise LexerError(f"Invalid integer literal: {result}", span)
    
    def lex_hex_number(self, start_line: int, start_col: int) -> Token:
        """Lex hexadecimal number"""
        self.advance()  # Skip '0'
        self.advance()  # Skip 'x'
        
        result = ""
        while self.peek().isdigit() or self.peek() in 'abcdefABCDEF_':
            if self.peek() != '_':
                result += self.peek()
            self.advance()
        
        span = self.make_span(start_line, start_col)
        
        if not result:
            raise LexerError("Invalid hexadecimal literal", span)
        
        try:
            return Token(TokenType.INTEGER, int(result, 16), span)
        except ValueError:
            raise LexerError(f"Invalid hexadecimal literal: 0x{result}", span)
    
    def lex_binary_number(self, start_line: int, start_col: int) -> Token:
        """Lex binary number"""
        self.advance()  # Skip '0'
        self.advance()  # Skip 'b'
        
        result = ""
        while self.peek() in '01_':
            if self.peek() != '_':
                result += self.peek()
            self.advance()
        
        span = self.make_span(start_line, start_col)
        
        if not result:
            raise LexerError("Invalid binary literal", span)
        
        try:
            return Token(TokenType.INTEGER, int(result, 2), span)
        except ValueError:
            raise LexerError(f"Invalid binary literal: 0b{result}", span)
    
    def lex_octal_number(self, start_line: int, start_col: int) -> Token:
        """Lex octal number"""
        self.advance()  # Skip '0'
        self.advance()  # Skip 'o'
        
        result = ""
        while self.peek() in '01234567_':
            if self.peek() != '_':
                result += self.peek()
            self.advance()
        
        span = self.make_span(start_line, start_col)
        
        if not result:
            raise LexerError("Invalid octal literal", span)
        
        try:
            return Token(TokenType.INTEGER, int(result, 8), span)
        except ValueError:
            raise LexerError(f"Invalid octal literal: 0o{result}", span)
    
    def lex_string(self) -> Token:
        """Lex a string literal"""
        start_line = self.line
        start_col = self.column
        
        quote = self.advance()  # Consume opening quote
        result = ""
        
        # Check for multiline string
        if self.peek() == quote and self.peek(1) == quote:
            # Multiline string: """..."""
            self.advance()
            self.advance()
            
            while True:
                if self.peek() == '\0':
                    raise LexerError(
                        "Unterminated string literal",
                        self.make_span(start_line, start_col)
                    )
                
                if (self.peek() == quote and 
                    self.peek(1) == quote and 
                    self.peek(2) == quote):
                    self.advance()
                    self.advance()
                    self.advance()
                    break
                
                result += self.advance()
        else:
            # Single-line string
            while self.peek() != quote:
                if self.peek() == '\0' or self.peek() == '\n':
                    raise LexerError(
                        "Unterminated string literal",
                        self.make_span(start_line, start_col)
                    )
                
                if self.peek() == '\\':
                    self.advance()
                    result += self.escape_sequence()
                else:
                    result += self.advance()
            
            self.advance()  # Consume closing quote
        
        return Token(TokenType.STRING, result, self.make_span(start_line, start_col))
    
    def escape_sequence(self) -> str:
        """Handle escape sequences in strings"""
        char = self.advance()
        
        if char == 'u' and self.peek() == '{':
            # Unicode escape: \u{...}
            self.advance()  # Consume {
            code_str = ""
            while self.peek() != '}' and self.peek() != '\0':
                code_str += self.advance()
            
            if self.peek() == '}':
                self.advance()  # Consume }
            else:
                raise LexerError("Unterminated Unicode escape sequence", self.make_span(self.line, self.column))
            
            try:
                # Convert hex to integer and then to character
                return chr(int(code_str, 16))
            except ValueError:
                raise LexerError(f"Invalid Unicode escape sequence: {code_str}", self.make_span(self.line, self.column))
        
        escape_chars = {
            'n': '\n',
            't': '\t',
            'r': '\r',
            '\\': '\\',
            '"': '"',
            "'": "'",
            '0': '\0',
        }
        
        if char in escape_chars:
            return escape_chars[char]
        else:
            # Unknown escape sequence - just return the character
            return char
    
    def lex_char(self) -> Token:
        """Lex a character literal"""
        start_line = self.line
        start_col = self.column
        
        self.advance()  # Consume opening '
        
        if self.peek() == '\\':
            self.advance()
            char = self.escape_sequence()
        else:
            char = self.advance()
        
        if self.peek() != "'":
            raise LexerError(
                "Character literal must contain exactly one character",
                self.make_span(start_line, start_col)
            )
        
        self.advance()  # Consume closing '
        
        return Token(TokenType.CHAR, char, self.make_span(start_line, start_col))
    
    def next_token(self) -> Token:
        """Get the next token"""
        # Return pending tokens first (DEDENT tokens)
        if self.pending_tokens:
            return self.pending_tokens.pop(0)
        
        # Handle indentation at line start
        if self.at_line_start:
            indent_tokens = self.handle_indentation()
            if indent_tokens:
                self.pending_tokens.extend(indent_tokens)
                return self.pending_tokens.pop(0)
        
        # Skip whitespace (but not newlines)
        self.skip_whitespace()
        
        # Skip comments
        while self.peek() == '#':
            self.skip_comment()
            if self.peek() == '\n':
                break
            self.skip_whitespace()
        
        # End of file
        if self.peek() == '\0':
            return Token(TokenType.EOF, None, self.make_span(self.line, self.column))
        
        start_line = self.line
        start_col = self.column
        char = self.peek()
        
        # Newline
        if char == '\n':
            self.advance()
            return Token(TokenType.NEWLINE, None, self.make_span(start_line, start_col))
        
        # Identifier or keyword
        if char.isalpha() or char == '_':
            return self.lex_identifier()
        
        # Number
        if char.isdigit():
            return self.lex_number()
        
        # String
        if char == '"':
            return self.lex_string()
        
        # Character
        if char == "'":
            return self.lex_char()
        
        # Operators and delimiters
        self.advance()
        
        # Two-character operators (maximal munch)
        next_char = self.peek()
        two_char = char + next_char
        
        if two_char == '==':
            self.advance()
            return Token(TokenType.EQ, None, self.make_span(start_line, start_col))
        elif two_char == '!=':
            self.advance()
            return Token(TokenType.NE, None, self.make_span(start_line, start_col))
        elif two_char == '<=':
            self.advance()
            return Token(TokenType.LE, None, self.make_span(start_line, start_col))
        elif two_char == '>=':
            self.advance()
            return Token(TokenType.GE, None, self.make_span(start_line, start_col))
        elif two_char == '->':
            self.advance()
            return Token(TokenType.ARROW, None, self.make_span(start_line, start_col))
        elif two_char == '::':
            self.advance()
            return Token(TokenType.DOUBLE_COLON, None, self.make_span(start_line, start_col))
        elif two_char == '..':
            self.advance()
            if self.peek() == '.':
                self.advance()
                return Token(TokenType.TRIPLE_DOT, None, self.make_span(start_line, start_col))
            return Token(TokenType.DOUBLE_DOT, None, self.make_span(start_line, start_col))
        elif two_char == '+=':
            self.advance()
            return Token(TokenType.PLUS_EQ, None, self.make_span(start_line, start_col))
        elif two_char == '-=':
            self.advance()
            return Token(TokenType.MINUS_EQ, None, self.make_span(start_line, start_col))
        elif two_char == '*=':
            self.advance()
            return Token(TokenType.STAR_EQ, None, self.make_span(start_line, start_col))
        elif two_char == '/=':
            self.advance()
            return Token(TokenType.SLASH_EQ, None, self.make_span(start_line, start_col))
        elif two_char == '<<':
            self.advance()
            return Token(TokenType.SHL, None, self.make_span(start_line, start_col))
        elif two_char == '>>':
            self.advance()
            return Token(TokenType.SHR, None, self.make_span(start_line, start_col))
        elif two_char == '&&':
            self.advance()
            return Token(TokenType.AND_AND, None, self.make_span(start_line, start_col))
        elif two_char == '||':
            self.advance()
            return Token(TokenType.PIPE_PIPE, None, self.make_span(start_line, start_col))
        
        # Single-character operators
        token_map = {
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '<': TokenType.LT,
            '>': TokenType.GT,
            '=': TokenType.ASSIGN,
            '&': TokenType.AMPERSAND,
            '|': TokenType.PIPE,
            '^': TokenType.CARET,
            '~': TokenType.TILDE,
            '!': TokenType.BANG,
            '@': TokenType.AT_SIGN,
            '.': TokenType.DOT,
            ',': TokenType.COMMA,
            ':': TokenType.COLON,
            ';': TokenType.SEMICOLON,
            '?': TokenType.QUESTION_MARK,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
        }
        
        if char in token_map:
            return Token(token_map[char], None, self.make_span(start_line, start_col))
        
        # Unknown character
        raise LexerError(
            f"Unexpected character: {repr(char)}",
            self.make_span(start_line, start_col)
        )
    
    def tokenize(self) -> List[Token]:
        """Tokenize entire source file"""
        tokens = []
        
        while True:
            token = self.next_token()
            tokens.append(token)
            
            if token.type == TokenType.EOF:
                break
        
        # Add final DEDENT tokens to close all blocks
        while len(self.indent_stack) > 1:
            self.indent_stack.pop()
            tokens.insert(-1, Token(  # Insert before EOF
                TokenType.DEDENT,
                None,
                self.make_span(self.line, self.column)
            ))
        
        return tokens


def lex(source: str, filename: str = "<input>") -> List[Token]:
    """Convenience function to tokenize source code"""
    lexer = Lexer(source, filename)
    return lexer.tokenize()

