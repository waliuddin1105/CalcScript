"""
CalcScript IR Generator - Phase 4: Intermediate Code Generation
===============================================================
Generates Three-Address Code (TAC) from the AST.

TAC Instruction Forms:
──────────────────────────────────────────────────────────────
  t1 = a op b          BinaryOp
  t1 = op a            UnaryOp
  t1 = a               Copy
  t1 = call f, [args]  Call
  print t1             Print
  param a              Push argument before call
  return a             Return from function
  label L:             Label (jump target)
  if_false t goto L    Conditional jump
  goto L               Unconditional jump
  func_begin f         Function entry marker
  func_end f           Function exit marker
──────────────────────────────────────────────────────────────

Example — result = sqrt(x + 1):
  t0 = x + 1
  t1 = call sqrt, [t0]
  result = t1

Example — if y > 2 then print y end:
  t0 = y > 2
  if_false t0 goto L1
  print y
  L1:
──────────────────────────────────────────────────────────────
"""

from typing import List, Optional, Any
from ast_nodes import (
    ASTNode, Program, Block,
    AssignStmt, PrintStmt, ReturnStmt, FuncDefStmt, IfStmt, RepeatStmt,
    BinaryExpr, UnaryExpr, NumberLiteral, IdentifierExpr, FuncCallExpr,
)


# ─────────────────────────────────────────────
#  TAC Instruction Classes
# ─────────────────────────────────────────────

class TACInstr:
    """Base class for all TAC instructions."""
    pass


class BinaryOp(TACInstr):
    """result = left op right"""
    def __init__(self, result, left, op, right):
        self.result = result
        self.left   = left
        self.op     = op
        self.right  = right

    def __str__(self):
        return f"    {self.result} = {self.left} {self.op} {self.right}"


class UnaryOp(TACInstr):
    """result = op operand"""
    def __init__(self, result, op, operand):
        self.result  = result
        self.op      = op
        self.operand = operand

    def __str__(self):
        return f"    {self.result} = {self.op}{self.operand}"


class Copy(TACInstr):
    """result = src"""
    def __init__(self, result, src):
        self.result = result
        self.src    = src

    def __str__(self):
        return f"    {self.result} = {self.src}"


class CallInstr(TACInstr):
    """result = call func_name arg1, arg2, ..."""
    def __init__(self, result, func_name, args):
        self.result    = result
        self.func_name = func_name
        self.args      = args

    def __str__(self):
        args_str = ", ".join(str(a) for a in self.args)
        return f"    {self.result} = call {self.func_name} [{args_str}]"


class PrintInstr(TACInstr):
    """print value"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"    print {self.value}"


class ReturnInstr(TACInstr):
    """return value"""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f"    return {self.value}"


class LabelInstr(TACInstr):
    """L:"""
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"{self.name}:"


class GotoInstr(TACInstr):
    """goto L"""
    def __init__(self, label):
        self.label = label

    def __str__(self):
        return f"    goto {self.label}"


class IfFalseGoto(TACInstr):
    """if_false condition goto L"""
    def __init__(self, condition, label):
        self.condition = condition
        self.label     = label

    def __str__(self):
        return f"    if_false {self.condition} goto {self.label}"


class FuncBegin(TACInstr):
    """func_begin name (params...)"""
    def __init__(self, name, params):
        self.name   = name
        self.params = params

    def __str__(self):
        return f"func_begin {self.name} ({', '.join(self.params)})"


class FuncEnd(TACInstr):
    """func_end name"""
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"func_end {self.name}"


# ─────────────────────────────────────────────
#  IR Generator
# ─────────────────────────────────────────────

class IRGenerator:
    """
    Walks the AST and emits a flat list of TACInstr objects.

    Usage:
        gen    = IRGenerator()
        instrs = gen.generate(tree)     # returns List[TACInstr]
        gen.pretty_print()              # prints formatted TAC
    """

    def __init__(self):
        self._instrs:   List[TACInstr] = []
        self._temp_cnt: int = 0
        self._label_cnt: int = 0

    # ── Helpers ─────────────────────────────────

    def _new_temp(self) -> str:
        t = f"t{self._temp_cnt}"
        self._temp_cnt += 1
        return t

    def _new_label(self) -> str:
        l = f"L{self._label_cnt}"
        self._label_cnt += 1
        return l

    def _emit(self, instr: TACInstr) -> None:
        self._instrs.append(instr)

    # ── Public entry point ───────────────────────

    def generate(self, program: Program) -> List[TACInstr]:
        self._instrs    = []
        self._temp_cnt  = 0
        self._label_cnt = 0
        self._gen_program(program)
        return self._instrs

    # ── Program / Block ──────────────────────────

    def _gen_program(self, node: Program) -> None:
        for stmt in node.statements:
            self._gen_stmt(stmt)

    def _gen_block(self, node: Block) -> None:
        for stmt in node.statements:
            self._gen_stmt(stmt)

    # ── Statements ───────────────────────────────

    def _gen_stmt(self, node: ASTNode) -> None:
        if isinstance(node, AssignStmt):    self._gen_assign(node)
        elif isinstance(node, PrintStmt):   self._gen_print(node)
        elif isinstance(node, ReturnStmt):  self._gen_return(node)
        elif isinstance(node, FuncDefStmt): self._gen_func_def(node)
        elif isinstance(node, IfStmt):      self._gen_if(node)
        elif isinstance(node, RepeatStmt):  self._gen_repeat(node)
        else:
            # Expression statement
            self._gen_expr(node)

    def _gen_assign(self, node: AssignStmt) -> None:
        src = self._gen_expr(node.value)
        self._emit(Copy(node.name, src))

    def _gen_print(self, node: PrintStmt) -> None:
        val = self._gen_expr(node.value)
        self._emit(PrintInstr(val))

    def _gen_return(self, node: ReturnStmt) -> None:
        val = self._gen_expr(node.value)
        self._emit(ReturnInstr(val))

    def _gen_func_def(self, node: FuncDefStmt) -> None:
        self._emit(FuncBegin(node.name, node.params))
        if isinstance(node.body, Block):
            self._gen_block(node.body)
        else:
            # Single-line: func f(x) => expr  →  return expr
            val = self._gen_expr(node.body)
            self._emit(ReturnInstr(val))
        self._emit(FuncEnd(node.name))

    def _gen_if(self, node: IfStmt) -> None:
        cond     = self._gen_expr(node.condition)
        else_lbl = self._new_label()
        end_lbl  = self._new_label()

        self._emit(IfFalseGoto(cond, else_lbl))
        self._gen_block(node.then_body)

        if node.else_body:
            self._emit(GotoInstr(end_lbl))
            self._emit(LabelInstr(else_lbl))
            self._gen_block(node.else_body)
            self._emit(LabelInstr(end_lbl))
        else:
            self._emit(LabelInstr(else_lbl))

    def _gen_repeat(self, node: RepeatStmt) -> None:
        # Implement repeat N times using a counter variable
        count_val  = self._gen_expr(node.count)
        counter    = self._new_temp()        # counter temp
        loop_lbl   = self._new_label()
        end_lbl    = self._new_label()

        # counter = count_val
        self._emit(Copy(counter, count_val))

        # loop_lbl:
        self._emit(LabelInstr(loop_lbl))

        # if_false (counter > 0) goto end_lbl
        zero_tmp = self._new_temp()
        cond_tmp = self._new_temp()
        self._emit(Copy(zero_tmp, "0"))
        self._emit(BinaryOp(cond_tmp, counter, ">", zero_tmp))
        self._emit(IfFalseGoto(cond_tmp, end_lbl))

        # body
        self._gen_block(node.body)

        # counter = counter - 1
        one_tmp    = self._new_temp()
        new_counter = self._new_temp()
        self._emit(Copy(one_tmp, "1"))
        self._emit(BinaryOp(new_counter, counter, "-", one_tmp))
        self._emit(Copy(counter, new_counter))

        # goto loop_lbl
        self._emit(GotoInstr(loop_lbl))
        self._emit(LabelInstr(end_lbl))

    # ── Expressions (return the name of the result temp/var) ────

    def _gen_expr(self, node: ASTNode) -> str:
        if isinstance(node, NumberLiteral):
            # Represent as string to keep TAC readable
            v = int(node.value) if node.value == int(node.value) else node.value
            return str(v)

        elif isinstance(node, IdentifierExpr):
            return node.name

        elif isinstance(node, UnaryExpr):
            operand = self._gen_expr(node.right)
            result  = self._new_temp()
            self._emit(UnaryOp(result, node.op, operand))
            return result

        elif isinstance(node, BinaryExpr):
            left   = self._gen_expr(node.left)
            right  = self._gen_expr(node.right)
            result = self._new_temp()
            self._emit(BinaryOp(result, left, node.op, right))
            return result

        elif isinstance(node, FuncCallExpr):
            arg_temps = [self._gen_expr(a) for a in node.args]
            result    = self._new_temp()
            self._emit(CallInstr(result, node.name, arg_temps))
            return result

        else:
            raise RuntimeError(f"IRGenerator: unknown expr node {type(node).__name__}")

    # ── Pretty print ─────────────────────────────

    def pretty_print(self, instrs: Optional[List[TACInstr]] = None) -> None:
        code = instrs or self._instrs
        print("\n── Three-Address Code (TAC) ─────────────────")
        for i, instr in enumerate(code):
            print(f"  {i:>3}  {instr}")
        print()