"""
CalcScript Parser - Phase 2: Syntax Analysis
=============================================
Recursive-descent parser consuming the token stream from the Lexer
and producing an AST.

Grammar (EBNF):
─────────────────────────────────────────────────────────────────
<program>       ::= { <statement> }

<statement>     ::= <func_def>
                  | <if_stmt>
                  | <repeat_stmt>
                  | <print_stmt>
                  | <return_stmt>
                  | <assign_stmt>
                  | <expr_stmt>

<func_def>      ::= "func" IDENTIFIER "(" <param_list> ")" "=>" <expr>
                  | "func" IDENTIFIER "(" <param_list> ")" NEWLINE <block> "end"

<param_list>    ::= [ IDENTIFIER { "," IDENTIFIER } ]

<if_stmt>       ::= "if" <expr> "then" <block> [ "else" <block> ] "end"

<repeat_stmt>   ::= "repeat" <expr> "times" <block> "end"

<print_stmt>    ::= "print" <expr>

<return_stmt>   ::= "return" <expr>

<assign_stmt>   ::= IDENTIFIER "=" <expr>

<block>         ::= { <statement> }

<expr>          ::= <comparison>

<comparison>    ::= <addition> { ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) <addition> }

<addition>      ::= <multiplication> { ( "+" | "-" ) <multiplication> }

<multiplication>::= <power> { ( "*" | "/" ) <power> }

<power>         ::= <unary> { "^" <power> }        (* right-associative *)

<unary>         ::= "-" <unary> | <primary>

<primary>       ::= NUMBER
                  | IDENTIFIER "(" <arg_list> ")"  (* function call *)
                  | BUILTIN    "(" <arg_list> ")"  (* built-in call  *)
                  | IDENTIFIER                      (* variable ref   *)
                  | "(" <expr> ")"

<arg_list>      ::= [ <expr> { "," <expr> } ]
─────────────────────────────────────────────────────────────────
"""

from typing import List, Optional
from lexer import Lexer, Token, TokenType
from ast_nodes import (
    ASTNode, Program, Block,
    AssignStmt, PrintStmt, ReturnStmt, FuncDefStmt, IfStmt, RepeatStmt,
    BinaryExpr, UnaryExpr, NumberLiteral, IdentifierExpr, FuncCallExpr,
)


# ─────────────────────────────────────────────
#  Parser Error
# ─────────────────────────────────────────────

class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        loc = f"line {token.line}, col {token.column}"
        super().__init__(f"[ParseError] {loc}: {message} (got {token.type.name} {token.value!r})")
        self.token = token


# ─────────────────────────────────────────────
#  Comparison operator set
# ─────────────────────────────────────────────

COMPARISON_OPS = {
    TokenType.EQ, TokenType.NEQ,
    TokenType.LT, TokenType.GT,
    TokenType.LTE, TokenType.GTE,
}

BUILTIN_TYPES = {
    TokenType.SQRT, TokenType.ABS,
    TokenType.SIN,  TokenType.COS,
    TokenType.LOG,  TokenType.TAN,
}


# ─────────────────────────────────────────────
#  Parser
# ─────────────────────────────────────────────

class Parser:
    """
    Recursive-descent parser for CalcScript.

    Usage:
        tokens = Lexer(source).tokenize()
        tree   = Parser(tokens).parse()     # returns Program node
    """

    def __init__(self, tokens: List[Token]):
        # Strip leading/trailing newlines for cleanliness
        self._tokens = tokens
        self._pos    = 0

    # ── Token navigation ────────────────────────

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _peek_type(self) -> TokenType:
        return self._tokens[self._pos].type

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        if tok.type != TokenType.EOF:
            self._pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._peek_type() in types

    def _match(self, *types: TokenType) -> Optional[Token]:
        if self._check(*types):
            return self._advance()
        return None

    def _expect(self, typ: TokenType, msg: str = "") -> Token:
        if self._check(typ):
            return self._advance()
        raise ParseError(
            msg or f"expected {typ.name}",
            self._peek()
        )

    def _skip_newlines(self):
        while self._check(TokenType.NEWLINE):
            self._advance()

    def _at_end(self) -> bool:
        return self._peek_type() == TokenType.EOF

    # ── Public entry point ───────────────────────

    def parse(self) -> Program:
        self._skip_newlines()
        prog = Program(line=1, col=1)
        while not self._at_end():
            stmt = self._parse_statement()
            if stmt is not None:
                prog.statements.append(stmt)
            self._skip_newlines()
        return prog

    # ── Statements ───────────────────────────────

    def _parse_statement(self) -> Optional[ASTNode]:
        self._skip_newlines()
        tok = self._peek()

        if tok.type == TokenType.FUNC:
            return self._parse_func_def()
        if tok.type == TokenType.IF:
            return self._parse_if()
        if tok.type == TokenType.REPEAT:
            return self._parse_repeat()
        if tok.type == TokenType.PRINT:
            return self._parse_print()
        if tok.type == TokenType.RETURN:
            return self._parse_return()
        if tok.type == TokenType.IDENTIFIER:
            # Look ahead: if next non-whitespace token is ASSIGN → assignment
            # otherwise treat as expression statement (function call, etc.)
            return self._parse_assign_or_expr()
        if tok.type in (TokenType.NEWLINE, TokenType.EOF):
            return None

        # expression statement (e.g. standalone call)
        return self._parse_expr_stmt()

    def _parse_assign_or_expr(self) -> ASTNode:
        """IDENTIFIER = expr   OR   expr-starting-with-identifier."""
        tok = self._peek()
        # Save position; peek ahead past the identifier
        saved_pos = self._pos
        name_tok  = self._advance()          # consume IDENTIFIER

        if self._check(TokenType.ASSIGN):
            self._advance()                  # consume =
            value = self._parse_expr()
            self._expect_newline_or_eof()
            return AssignStmt(name=name_tok.value, value=value,
                              line=name_tok.line, col=name_tok.column)
        else:
            # Not an assignment — backtrack and parse as expression
            self._pos = saved_pos
            node = self._parse_expr()
            self._expect_newline_or_eof()
            return node

    def _parse_expr_stmt(self) -> ASTNode:
        node = self._parse_expr()
        self._expect_newline_or_eof()
        return node

    def _expect_newline_or_eof(self):
        if self._check(TokenType.NEWLINE, TokenType.EOF):
            self._match(TokenType.NEWLINE)
        # else: allow implicit end (e.g. before 'end', 'else')

    def _parse_func_def(self) -> FuncDefStmt:
        tok = self._expect(TokenType.FUNC)
        name_tok = self._expect(TokenType.IDENTIFIER, "expected function name after 'func'")
        self._expect(TokenType.LPAREN, "expected '(' after function name")
        params = self._parse_param_list()
        self._expect(TokenType.RPAREN, "expected ')' after parameters")

        if self._match(TokenType.ARROW):
            # Single-line: func f(x) => expr
            body = self._parse_expr()
            self._expect_newline_or_eof()
            return FuncDefStmt(name=name_tok.value, params=params, body=body,
                               line=tok.line, col=tok.column)
        else:
            # Multi-line: func f(x) \n body end
            self._expect_newline_or_eof()
            body = self._parse_block()
            self._expect(TokenType.END, "expected 'end' to close function body")
            self._expect_newline_or_eof()
            return FuncDefStmt(name=name_tok.value, params=params, body=body,
                               line=tok.line, col=tok.column)

    def _parse_param_list(self) -> List[str]:
        params = []
        if self._check(TokenType.IDENTIFIER):
            params.append(self._advance().value)
            while self._match(TokenType.COMMA):
                params.append(
                    self._expect(TokenType.IDENTIFIER, "expected parameter name").value
                )
        return params

    def _parse_if(self) -> IfStmt:
        tok = self._expect(TokenType.IF)
        condition = self._parse_expr()
        self._expect(TokenType.THEN, "expected 'then' after if condition")
        self._skip_newlines()
        then_body = self._parse_block()

        else_body = None
        if self._match(TokenType.ELSE):
            self._skip_newlines()
            else_body = self._parse_block()

        self._expect(TokenType.END, "expected 'end' to close if statement")
        self._expect_newline_or_eof()
        return IfStmt(condition=condition, then_body=then_body, else_body=else_body,
                      line=tok.line, col=tok.column)

    def _parse_repeat(self) -> RepeatStmt:
        tok = self._expect(TokenType.REPEAT)
        count = self._parse_expr()
        self._expect(TokenType.TIMES, "expected 'times' after repeat count")
        self._skip_newlines()
        body = self._parse_block()
        self._expect(TokenType.END, "expected 'end' to close repeat")
        self._expect_newline_or_eof()
        return RepeatStmt(count=count, body=body, line=tok.line, col=tok.column)

    def _parse_print(self) -> PrintStmt:
        tok = self._expect(TokenType.PRINT)
        value = self._parse_expr()
        self._expect_newline_or_eof()
        return PrintStmt(value=value, line=tok.line, col=tok.column)

    def _parse_return(self) -> ReturnStmt:
        tok = self._expect(TokenType.RETURN)
        value = self._parse_expr()
        self._expect_newline_or_eof()
        return ReturnStmt(value=value, line=tok.line, col=tok.column)

    def _parse_block(self) -> Block:
        """Parse statements until end/else/EOF."""
        block = Block(line=self._peek().line, col=self._peek().column)
        self._skip_newlines()
        while not self._check(TokenType.END, TokenType.ELSE, TokenType.EOF):
            stmt = self._parse_statement()
            if stmt is not None:
                block.statements.append(stmt)
            self._skip_newlines()
        return block

    # ── Expressions (precedence climbing) ───────

    def _parse_expr(self) -> ASTNode:
        return self._parse_comparison()

    def _parse_comparison(self) -> ASTNode:
        left = self._parse_addition()
        while self._check(*COMPARISON_OPS):
            op_tok = self._advance()
            right  = self._parse_addition()
            left   = BinaryExpr(op=op_tok.value, left=left, right=right,
                                 line=op_tok.line, col=op_tok.column)
        return left

    def _parse_addition(self) -> ASTNode:
        left = self._parse_multiplication()
        while self._check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            right  = self._parse_multiplication()
            left   = BinaryExpr(op=op_tok.value, left=left, right=right,
                                 line=op_tok.line, col=op_tok.column)
        return left

    def _parse_multiplication(self) -> ASTNode:
        left = self._parse_power()
        while self._check(TokenType.STAR, TokenType.SLASH):
            op_tok = self._advance()
            right  = self._parse_power()
            left   = BinaryExpr(op=op_tok.value, left=left, right=right,
                                 line=op_tok.line, col=op_tok.column)
        return left

    def _parse_power(self) -> ASTNode:
        """Right-associative: 2^3^2 = 2^(3^2)."""
        base = self._parse_unary()
        if self._check(TokenType.CARET):
            op_tok = self._advance()
            exp    = self._parse_power()   # recursive for right-assoc
            return BinaryExpr(op=op_tok.value, left=base, right=exp,
                               line=op_tok.line, col=op_tok.column)
        return base

    def _parse_unary(self) -> ASTNode:
        if self._check(TokenType.MINUS):
            op_tok = self._advance()
            right  = self._parse_unary()
            return UnaryExpr(op='-', right=right,
                              line=op_tok.line, col=op_tok.column)
        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        tok = self._peek()

        # Number literal
        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLiteral(value=float(tok.value),
                                  line=tok.line, col=tok.column)

        # Built-in function call: sqrt(x)
        if tok.type in BUILTIN_TYPES:
            self._advance()
            self._expect(TokenType.LPAREN, f"expected '(' after built-in '{tok.value}'")
            args = self._parse_arg_list()
            self._expect(TokenType.RPAREN, "expected ')' after arguments")
            return FuncCallExpr(name=tok.value, args=args,
                                 line=tok.line, col=tok.column)

        # Identifier: variable OR user function call
        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            if self._check(TokenType.LPAREN):
                self._advance()            # consume (
                args = self._parse_arg_list()
                self._expect(TokenType.RPAREN, "expected ')' after arguments")
                return FuncCallExpr(name=tok.value, args=args,
                                     line=tok.line, col=tok.column)
            return IdentifierExpr(name=tok.value, line=tok.line, col=tok.column)

        # Parenthesised expression
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')' to close expression")
            return expr

        raise ParseError("expected an expression", tok)

    def _parse_arg_list(self) -> List[ASTNode]:
        args = []
        if not self._check(TokenType.RPAREN):
            args.append(self._parse_expr())
            while self._match(TokenType.COMMA):
                args.append(self._parse_expr())
        return args


# ─────────────────────────────────────────────
#  AST Pretty-Printer (for --debug and handwritten parse tree reference)
# ─────────────────────────────────────────────

class ASTPrinter:
    """Prints the AST as an indented tree."""

    def print(self, node: ASTNode, indent: int = 0) -> None:
        pad  = "    " * indent
        pipe = "│   " * indent

        name = type(node).__name__

        if isinstance(node, Program):
            print(f"{pad}Program")
            for s in node.statements:
                self.print(s, indent + 1)

        elif isinstance(node, Block):
            print(f"{pad}Block")
            for s in node.statements:
                self.print(s, indent + 1)

        elif isinstance(node, FuncDefStmt):
            params = ", ".join(node.params)
            print(f"{pad}FuncDef  name={node.name!r}  params=({params})")
            self.print(node.body, indent + 1)

        elif isinstance(node, AssignStmt):
            print(f"{pad}Assign  name={node.name!r}")
            self.print(node.value, indent + 1)

        elif isinstance(node, PrintStmt):
            print(f"{pad}Print")
            self.print(node.value, indent + 1)

        elif isinstance(node, ReturnStmt):
            print(f"{pad}Return")
            self.print(node.value, indent + 1)

        elif isinstance(node, IfStmt):
            print(f"{pad}If")
            print(f"{pad}  condition:")
            self.print(node.condition, indent + 2)
            print(f"{pad}  then:")
            self.print(node.then_body, indent + 2)
            if node.else_body:
                print(f"{pad}  else:")
                self.print(node.else_body, indent + 2)

        elif isinstance(node, RepeatStmt):
            print(f"{pad}Repeat")
            print(f"{pad}  count:")
            self.print(node.count, indent + 2)
            print(f"{pad}  body:")
            self.print(node.body, indent + 2)

        elif isinstance(node, BinaryExpr):
            print(f"{pad}BinOp  op={node.op!r}")
            self.print(node.left,  indent + 1)
            self.print(node.right, indent + 1)

        elif isinstance(node, UnaryExpr):
            print(f"{pad}UnaryOp  op={node.op!r}")
            self.print(node.right, indent + 1)

        elif isinstance(node, FuncCallExpr):
            print(f"{pad}FuncCall  name={node.name!r}")
            for a in node.args:
                self.print(a, indent + 1)

        elif isinstance(node, NumberLiteral):
            print(f"{pad}Number  {node.value}")

        elif isinstance(node, IdentifierExpr):
            print(f"{pad}Identifier  {node.name!r}")

        else:
            print(f"{pad}{node!r}")