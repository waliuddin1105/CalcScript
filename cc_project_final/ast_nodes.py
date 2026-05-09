"""
CalcScript AST Nodes - Phase 2: Syntax Analysis
================================================
All AST node types produced by the parser.
Each node stores its source location (line, col) for error reporting.
"""

from typing import List, Optional


class ASTNode:
    def __init__(self, line: int = 0, col: int = 0):
        self.line = line
        self.col  = col

    def accept(self, visitor):
        method = f"visit_{type(self).__name__}"
        return getattr(visitor, method)(self)


class Program(ASTNode):
    def __init__(self, statements=None, line=0, col=0):
        super().__init__(line, col)
        self.statements: List[ASTNode] = statements or []
    def __repr__(self): return f"Program({len(self.statements)} stmts)"


class Block(ASTNode):
    def __init__(self, statements=None, line=0, col=0):
        super().__init__(line, col)
        self.statements: List[ASTNode] = statements or []
    def __repr__(self): return f"Block({len(self.statements)} stmts)"


class AssignStmt(ASTNode):
    def __init__(self, name: str, value: ASTNode, line=0, col=0):
        super().__init__(line, col)
        self.name  = name
        self.value = value
    def __repr__(self): return f"Assign({self.name!r}, {self.value})"


class PrintStmt(ASTNode):
    def __init__(self, value: ASTNode, line=0, col=0):
        super().__init__(line, col)
        self.value = value
    def __repr__(self): return f"Print({self.value})"


class ReturnStmt(ASTNode):
    def __init__(self, value: ASTNode, line=0, col=0):
        super().__init__(line, col)
        self.value = value
    def __repr__(self): return f"Return({self.value})"


class FuncDefStmt(ASTNode):
    def __init__(self, name: str, params: List[str], body: ASTNode, line=0, col=0):
        super().__init__(line, col)
        self.name   = name
        self.params = params
        self.body   = body
    def __repr__(self): return f"FuncDef({self.name!r}, params={self.params})"


class IfStmt(ASTNode):
    def __init__(self, condition: ASTNode, then_body: Block,
                 else_body: Optional[Block] = None, line=0, col=0):
        super().__init__(line, col)
        self.condition = condition
        self.then_body = then_body
        self.else_body = else_body
    def __repr__(self): return f"If({self.condition})"


class RepeatStmt(ASTNode):
    def __init__(self, count: ASTNode, body: Block, line=0, col=0):
        super().__init__(line, col)
        self.count = count
        self.body  = body
    def __repr__(self): return f"Repeat({self.count})"


class BinaryExpr(ASTNode):
    def __init__(self, op: str, left: ASTNode, right: ASTNode, line=0, col=0):
        super().__init__(line, col)
        self.op    = op
        self.left  = left
        self.right = right
    def __repr__(self): return f"BinOp({self.op!r}, {self.left}, {self.right})"


class UnaryExpr(ASTNode):
    def __init__(self, op: str, right: ASTNode, line=0, col=0):
        super().__init__(line, col)
        self.op    = op
        self.right = right
    def __repr__(self): return f"UnaryOp({self.op!r}, {self.right})"


class NumberLiteral(ASTNode):
    def __init__(self, value: float, line=0, col=0):
        super().__init__(line, col)
        self.value = value
    def __repr__(self): return f"Num({self.value})"


class IdentifierExpr(ASTNode):
    def __init__(self, name: str, line=0, col=0):
        super().__init__(line, col)
        self.name = name
    def __repr__(self): return f"Var({self.name!r})"


class FuncCallExpr(ASTNode):
    def __init__(self, name: str, args: List[ASTNode] = None, line=0, col=0):
        super().__init__(line, col)
        self.name = name
        self.args = args or []
    def __repr__(self): return f"Call({self.name!r}, {self.args})"