"""
CalcScript Semantic Analyzer - Phase 3: Semantic Analysis
==========================================================
Walks the AST and performs:
  1. Symbol resolution  — every identifier must be declared before use
  2. Type checking      — CalcScript is numeric-only; all values are 'number'
  3. Arity checking     — function calls must match parameter count
  4. Scope management   — function bodies get their own local scope
  5. Duplicate detection— no re-defining a function in the same scope

Semantic Rules:
─────────────────────────────────────────────────────────
  SR1  A variable used before assignment is an error.
  SR2  A function called before definition is an error.
  SR3  A function call with wrong argument count is an error.
  SR4  Re-defining a function in the same scope is a warning
       (we allow variable re-assignment freely, like a calculator).
  SR5  All expressions evaluate to type 'number' (only type in CalcScript).
  SR6  repeat count must be a numeric expression (always true in CalcScript).
  SR7  return is only valid inside a function body.
─────────────────────────────────────────────────────────
"""

from typing import List, Optional
from ast_nodes import (
    ASTNode, Program, Block,
    AssignStmt, PrintStmt, ReturnStmt, FuncDefStmt, IfStmt, RepeatStmt,
    BinaryExpr, UnaryExpr, NumberLiteral, IdentifierExpr, FuncCallExpr,
)
from symbol_table import SymbolTable, VarSymbol, FuncSymbol


# ─────────────────────────────────────────────
#  Semantic Error
# ─────────────────────────────────────────────

class SemanticError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        loc = f"line {line}, col {col}" if line else "unknown location"
        super().__init__(f"[SemanticError] {loc}: {message}")
        self.line = line
        self.col  = col


# ─────────────────────────────────────────────
#  Semantic Analyzer
# ─────────────────────────────────────────────

class SemanticAnalyzer:
    """
    Visitor-style AST walker.
    Returns the symbol table after analysis (for --debug output).

    Usage:
        analyzer = SemanticAnalyzer()
        analyzer.analyze(tree)          # raises SemanticError on failure
        analyzer.symbol_table           # inspect populated table
    """

    def __init__(self):
        self.symbol_table    = SymbolTable()
        self._in_function    = False      # SR7: track if inside func body
        self._current_func   = None       # name of current function (for errors)
        self.warnings: List[str] = []

    # ── Public entry point ───────────────────────

    def analyze(self, program: Program) -> SymbolTable:
        self._visit_program(program)
        return self.symbol_table

    # ── Program / Block ──────────────────────────

    def _visit_program(self, node: Program) -> None:
        for stmt in node.statements:
            self._visit_stmt(stmt)

    def _visit_block(self, node: Block) -> None:
        for stmt in node.statements:
            self._visit_stmt(stmt)

    # ── Statements ───────────────────────────────

    def _visit_stmt(self, node: ASTNode) -> None:
        if isinstance(node, AssignStmt):    self._visit_assign(node)
        elif isinstance(node, PrintStmt):   self._visit_print(node)
        elif isinstance(node, ReturnStmt):  self._visit_return(node)
        elif isinstance(node, FuncDefStmt): self._visit_func_def(node)
        elif isinstance(node, IfStmt):      self._visit_if(node)
        elif isinstance(node, RepeatStmt):  self._visit_repeat(node)
        else:
            # Expression statement (e.g. standalone call)
            self._visit_expr(node)

    def _visit_assign(self, node: AssignStmt) -> str:
        # Evaluate RHS first (catches use-before-assign on the right side)
        self._visit_expr(node.value)
        # Define or update variable in current scope
        existing = self.symbol_table.lookup_current_scope(node.name)
        if existing is None:
            self.symbol_table.define(VarSymbol(node.name))
        return "number"

    def _visit_print(self, node: PrintStmt) -> None:
        self._visit_expr(node.value)

    def _visit_return(self, node: ReturnStmt) -> None:
        # SR7: return only inside a function
        if not self._in_function:
            raise SemanticError(
                "'return' used outside of a function",
                node.line, node.col
            )
        self._visit_expr(node.value)

    def _visit_func_def(self, node: FuncDefStmt) -> None:
        # SR4: warn on re-definition in same scope
        existing = self.symbol_table.lookup_current_scope(node.name)
        if isinstance(existing, FuncSymbol) and not existing.is_builtin:
            self.warnings.append(
                f"[Warning] line {node.line}: function '{node.name}' re-defined"
            )

        # Register function in current scope BEFORE entering body
        # (allows recursion)
        func_sym = FuncSymbol(node.name, node.params)
        self.symbol_table.define(func_sym)

        # Enter function scope
        self.symbol_table.enter_scope()
        prev_in_func   = self._in_function
        prev_func_name = self._current_func
        self._in_function  = True
        self._current_func = node.name

        # Define parameters as local variables
        for param in node.params:
            self.symbol_table.define(VarSymbol(param))

        # Analyze body (Block or single Expr for single-line funcs)
        if isinstance(node.body, Block):
            self._visit_block(node.body)
        else:
            self._visit_expr(node.body)

        # Exit function scope
        self.symbol_table.exit_scope()
        self._in_function  = prev_in_func
        self._current_func = prev_func_name

    def _visit_if(self, node: IfStmt) -> None:
        self._visit_expr(node.condition)
        self._visit_block(node.then_body)
        if node.else_body:
            self._visit_block(node.else_body)

    def _visit_repeat(self, node: RepeatStmt) -> None:
        self._visit_expr(node.count)     # SR6: count must be numeric (always is)
        self._visit_block(node.body)

    # ── Expressions ──────────────────────────────

    def _visit_expr(self, node: ASTNode) -> str:
        """Returns the type of the expression (always 'number' in CalcScript)."""
        if isinstance(node, NumberLiteral):
            return "number"

        elif isinstance(node, IdentifierExpr):
            return self._visit_identifier(node)

        elif isinstance(node, BinaryExpr):
            return self._visit_binary(node)

        elif isinstance(node, UnaryExpr):
            self._visit_expr(node.right)
            return "number"

        elif isinstance(node, FuncCallExpr):
            return self._visit_call(node)

        else:
            raise SemanticError(
                f"Unknown expression node: {type(node).__name__}",
                node.line, node.col
            )

    def _visit_identifier(self, node: IdentifierExpr) -> str:
        # SR1: variable must be defined
        sym = self.symbol_table.lookup(node.name)
        if sym is None:
            raise SemanticError(
                f"Undefined variable '{node.name}'",
                node.line, node.col
            )
        if isinstance(sym, FuncSymbol):
            raise SemanticError(
                f"'{node.name}' is a function, not a variable",
                node.line, node.col
            )
        return "number"

    def _visit_binary(self, node: BinaryExpr) -> str:
        left_type  = self._visit_expr(node.left)
        right_type = self._visit_expr(node.right)
        # SR5: both sides must be numeric
        if left_type != "number" or right_type != "number":
            raise SemanticError(
                f"Operator '{node.op}' requires numeric operands",
                node.line, node.col
            )
        return "number"

    def _visit_call(self, node: FuncCallExpr) -> str:
        # SR2: function must be defined
        sym = self.symbol_table.lookup(node.name)
        if sym is None:
            raise SemanticError(
                f"Undefined function '{node.name}'",
                node.line, node.col
            )
        if not isinstance(sym, FuncSymbol):
            raise SemanticError(
                f"'{node.name}' is a variable, not a function",
                node.line, node.col
            )
        # SR3: argument count must match parameter count
        if len(node.args) != len(sym.params):
            raise SemanticError(
                f"Function '{node.name}' expects {len(sym.params)} argument(s), "
                f"got {len(node.args)}",
                node.line, node.col
            )
        # Analyze each argument
        for arg in node.args:
            self._visit_expr(arg)
        return "number"