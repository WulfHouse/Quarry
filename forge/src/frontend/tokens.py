"""Token definitions for Pyrite lexer"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional


class TokenType(Enum):
    """Token types for Pyrite language"""
    
    # Keywords
    FN = auto()
    LET = auto()
    VAR = auto()
    CONST = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    MATCH = auto()
    CASE = auto()
    MOVE = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    STRUCT = auto()
    ENUM = auto()
    IMPL = auto()
    TRAIT = auto()
    IMPORT = auto()
    AS = auto()
    FROM = auto()
    TRUE = auto()
    FALSE = auto()
    NONE = auto()
    UNSAFE = auto()
    DEFER = auto()
    WITH = auto()
    TRY = auto()
    EXTERN = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    TYPE = auto()
    PASS = auto()
    
    # Identifiers and Literals
    IDENTIFIER = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()
    CHAR = auto()
    
    # Operators
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    PERCENT = auto()        # %
    EQ = auto()             # ==
    NE = auto()             # !=
    LT = auto()             # <
    LE = auto()             # <=
    GT = auto()             # >
    GE = auto()             # >=
    ASSIGN = auto()         # =
    PLUS_EQ = auto()        # +=
    MINUS_EQ = auto()       # -=
    STAR_EQ = auto()        # *=
    SLASH_EQ = auto()       # /=
    AMPERSAND = auto()      # &
    PIPE = auto()           # |
    CARET = auto()          # ^
    TILDE = auto()          # ~
    SHL = auto()            # <<
    SHR = auto()            # >>
    AND_AND = auto()        # &&
    PIPE_PIPE = auto()      # ||
    BANG = auto()           # !
    AT_SIGN = auto()        # @
    DOT = auto()            # .
    COMMA = auto()          # ,
    COLON = auto()          # :
    SEMICOLON = auto()      # ;
    HASH = auto()           # #
    ARROW = auto()          # ->
    DOUBLE_COLON = auto()   # ::
    DOUBLE_DOT = auto()     # ..
    TRIPLE_DOT = auto()     # ...
    QUESTION_MARK = auto()  # ?
    
    # Delimiters
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    
    # Indentation
    INDENT = auto()
    DEDENT = auto()
    NEWLINE = auto()
    
    # Special
    EOF = auto()
    ERROR = auto()


# Keywords mapping
KEYWORDS = {
    'fn': TokenType.FN,
    'let': TokenType.LET,
    'var': TokenType.VAR,
    'const': TokenType.CONST,
    'if': TokenType.IF,
    'elif': TokenType.ELIF,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'match': TokenType.MATCH,
    'case': TokenType.CASE,
    'move': TokenType.MOVE,
    'return': TokenType.RETURN,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'struct': TokenType.STRUCT,
    'enum': TokenType.ENUM,
    'impl': TokenType.IMPL,
    'trait': TokenType.TRAIT,
    'import': TokenType.IMPORT,
    'as': TokenType.AS,
    'from': TokenType.FROM,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
    'None': TokenType.NONE,
    'unsafe': TokenType.UNSAFE,
    'defer': TokenType.DEFER,
    'with': TokenType.WITH,
    'try': TokenType.TRY,
    'extern': TokenType.EXTERN,
    'and': TokenType.AND,
    'or': TokenType.OR,
    'not': TokenType.NOT,
    'type': TokenType.TYPE,
    'pass': TokenType.PASS,
}


@dataclass
class Span:
    """Source location information"""
    filename: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    
    def __str__(self):
        return f"{self.filename}:{self.start_line}:{self.start_column}"


@dataclass
class Token:
    """A single token"""
    type: TokenType
    value: Any
    span: Span
    
    def __str__(self):
        if self.value is not None:
            return f"Token({self.type.name}, {repr(self.value)}, {self.span})"
        return f"Token({self.type.name}, {self.span})"

