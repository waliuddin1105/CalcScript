"""
CalcScript Lexer - Phase 1: Lexical Analysis
=============================================
Tokenizes .calc source files into a stream of tokens with line/column info.
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional


# ─────────────────────────────────────────────
#  Token Types
# ─────────────────────────────────────────────

class TokenType(Enum):
    # Literals
    NUMBER      = auto()   # integer or float: 42, 3.14, .5
    IDENTIFIER  = auto()   # variable/function names: x, myVar

    # Keywords
    FUNC        = auto()   # func
    IF          = auto()   # if
    THEN        = auto()   # then
    ELSE        = auto()   # else
    END         = auto()   # end
    REPEAT      = auto()   # repeat
    TIMES       = auto()   # times
    PRINT       = auto()   # print
    RETURN      = auto()   # return

    # Built-in math functions
    SQRT        = auto()   # sqrt
    ABS         = auto()   # abs
    SIN         = auto()   # sin
    COS         = auto()   # cos
    LOG         = auto()   # log
    TAN         = auto()   # tan

    # Arithmetic operators
    PLUS        = auto()   # +
    MINUS       = auto()   # -
    STAR        = auto()   # *
    SLASH       = auto()   # /
    CARET       = auto()   # ^  (power)

    # Comparison operators
    EQ          = auto()   # ==
    NEQ         = auto()   # !=
    LT          = auto()   # <
    GT          = auto()   # >
    LTE         = auto()   # <=
    GTE         = auto()   # >=

    # Assignment
    ASSIGN      = auto()   # =

    # Delimiters
    LPAREN      = auto()   # (
    RPAREN      = auto()   # )
    COMMA       = auto()   # ,
    ARROW       = auto()   # =>

    # Special
    NEWLINE     = auto()   # \n  (statement separator)
    EOF         = auto()   # end of file
    COMMENT     = auto()   # // ...  (skipped by default)


# ─────────────────────────────────────────────
#  Keyword & Built-in Maps
# ─────────────────────────────────────────────

KEYWORDS: dict[str, TokenType] = {
    "func":   TokenType.FUNC,
    "if":     TokenType.IF,
    "then":   TokenType.THEN,
    "else":   TokenType.ELSE,
    "end":    TokenType.END,
    "repeat": TokenType.REPEAT,
    "times":  TokenType.TIMES,
    "print":  TokenType.PRINT,
    "return": TokenType.RETURN,
}

BUILTINS: dict[str, TokenType] = {
    "sqrt": TokenType.SQRT,
    "abs":  TokenType.ABS,
    "sin":  TokenType.SIN,
    "cos":  TokenType.COS,
    "log":  TokenType.LOG,
    "tan":  TokenType.TAN,
}


# ─────────────────────────────────────────────
#  Token Dataclass
# ─────────────────────────────────────────────

@dataclass
class Token:
    type:    TokenType
    value:   str
    line:    int
    column:  int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


# ─────────────────────────────────────────────
#  Lexical Error
# ─────────────────────────────────────────────

class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"[LexerError] Line {line}, Col {column}: {message}")
        self.line   = line
        self.column = column


# ─────────────────────────────────────────────
#  Token Patterns  (order matters — checked top-to-bottom)
# ─────────────────────────────────────────────

TOKEN_PATTERNS: List[tuple[str, Optional[TokenType]]] = [
    # Whitespace (spaces/tabs only — newlines handled separately)
    (r'[ \t]+',                  None),              # skip horizontal whitespace

    # Comments
    (r'//[^\n]*',                TokenType.COMMENT), # // to end of line

    # Newline (statement separator)
    (r'\n',                      TokenType.NEWLINE),

    # Number literals  (float before int to match 3.14 correctly)
    (r'\d+\.\d*|\.\d+',          TokenType.NUMBER),  # 3.14 | .5
    (r'\d+',                     TokenType.NUMBER),  # 42

    # Arrow operator (must come before comparisons to match =>)
    (r'=>',                      TokenType.ARROW),

    # Two-character comparison operators
    (r'==',                      TokenType.EQ),
    (r'!=',                      TokenType.NEQ),
    (r'<=',                      TokenType.LTE),
    (r'>=',                      TokenType.GTE),

    # Single-character operators and delimiters
    (r'\+',                      TokenType.PLUS),
    (r'-',                       TokenType.MINUS),
    (r'\*',                      TokenType.STAR),
    (r'/',                       TokenType.SLASH),
    (r'\^',                      TokenType.CARET),
    (r'<',                       TokenType.LT),
    (r'>',                       TokenType.GT),
    (r'=',                       TokenType.ASSIGN),
    (r'\(',                      TokenType.LPAREN),
    (r'\)',                      TokenType.RPAREN),
    (r',',                       TokenType.COMMA),

    # Identifiers and keywords (letters/underscores, then alphanumeric)
    (r'[A-Za-z_][A-Za-z0-9_]*',  TokenType.IDENTIFIER),
]

# Compile all patterns into one master regex with named groups
_MASTER_REGEX = re.compile(
    '|'.join(f'(?P<PAT{i}>{pat})' for i, (pat, _) in enumerate(TOKEN_PATTERNS))
)


# ─────────────────────────────────────────────
#  Lexer Class
# ─────────────────────────────────────────────

class Lexer:
    """
    Converts CalcScript source text into a list of Tokens.

    Usage:
        lexer  = Lexer(source_code)
        tokens = lexer.tokenize()          # returns List[Token]
    """

    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source   = source
        self.filename = filename
        self._tokens: List[Token] = []

    # ── Public API ──────────────────────────────

    def tokenize(self, skip_comments: bool = True) -> List[Token]:
        """
        Scan the full source and return a token list ending with EOF.
        Comments are stripped unless skip_comments=False.
        Consecutive NEWLINEs are collapsed to one.
        """
        self._tokens = []
        line    = 1
        line_start = 0  # character index where the current line began

        pos = 0
        source = self.source
        length = len(source)

        last_was_newline = True  # suppress leading blank lines

        while pos < length:
            match = _MASTER_REGEX.match(source, pos)

            if not match:
                col = pos - line_start + 1
                raise LexerError(
                    f"Unexpected character {source[pos]!r}",
                    line, col
                )

            # Find which pattern matched
            group_index = next(
                i for i, g in enumerate(match.groups()) if g is not None
            )
            pat_str, tok_type = TOKEN_PATTERNS[group_index]
            value = match.group()
            col   = pos - line_start + 1

            pos = match.end()

            # ── Handle each token type ───────────────

            # Skip pure whitespace
            if tok_type is None:
                continue

            # Track newlines for line/column counting
            if tok_type == TokenType.NEWLINE:
                if not last_was_newline:
                    self._tokens.append(Token(TokenType.NEWLINE, "\\n", line, col))
                    last_was_newline = True
                line += 1
                line_start = pos
                continue

            # Comments
            if tok_type == TokenType.COMMENT:
                if not skip_comments:
                    self._tokens.append(Token(TokenType.COMMENT, value, line, col))
                continue

            # Reclassify IDENTIFIER → keyword or built-in if applicable
            if tok_type == TokenType.IDENTIFIER:
                if value in KEYWORDS:
                    tok_type = KEYWORDS[value]
                elif value in BUILTINS:
                    tok_type = BUILTINS[value]

            self._tokens.append(Token(tok_type, value, line, col))
            last_was_newline = False

        # Always end with EOF
        eof_line = line
        self._tokens.append(Token(TokenType.EOF, "", eof_line, 0))
        return self._tokens

    def token_stream(self) -> List[Token]:
        """Return already-computed tokens (call tokenize() first)."""
        return self._tokens

    # ── Debug helpers ────────────────────────────

    def pretty_print(self, tokens: Optional[List[Token]] = None) -> None:
        """Print token table to stdout."""
        toks = tokens or self._tokens
        if not toks:
            print("No tokens — run tokenize() first.")
            return
        col_w = [10, 24, 8, 8]
        header = f"{'TYPE':<{col_w[0]}}  {'VALUE':<{col_w[1]}}  {'LINE':>{col_w[2]}}  {'COL':>{col_w[3]}}"
        print(header)
        print("─" * len(header))
        for tok in toks:
            print(
                f"{tok.type.name:<{col_w[0]}}  "
                f"{tok.value!r:<{col_w[1]}}  "
                f"{tok.line:>{col_w[2]}}  "
                f"{tok.column:>{col_w[3]}}"
            )