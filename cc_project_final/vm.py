"""
CalcScript Virtual Machine - Phase 6: Code Generation & Execution
=================================================================
A register-based interpreter that executes the optimized TAC
instruction list produced by Phases 4 and 5.

VM Design:
─────────────────────────────────────────────────────────────────
  Memory model:
    - Global frame   : dict { name -> float }  (variables + temps)
    - Call stack     : list of Frame objects   (one per function call)
    - Each Frame     : { locals: dict, return_addr: int, return_dest: str }

  Execution:
    - Program counter (PC) walks the instruction list sequentially.
    - Labels are pre-indexed into a label_map { name -> index } before run.
    - FuncBegin/FuncEnd are markers — VM skips over function bodies
      during top-level execution and jumps into them on CallInstr.

  Built-in functions:
    Resolved before user lookup: sqrt, abs, sin, cos, log, tan.

  Output:
    PrintInstr writes to stdout in classic calculator display style:
      >> 4.0
─────────────────────────────────────────────────────────────────
"""

import math
from typing import List, Dict, Optional, Any
from ir_gen import (
    TACInstr, BinaryOp, UnaryOp, Copy, CallInstr,
    PrintInstr, ReturnInstr, LabelInstr, GotoInstr,
    IfFalseGoto, FuncBegin, FuncEnd,
)


# ─────────────────────────────────────────────
#  Runtime Error
# ─────────────────────────────────────────────

class RuntimeError_(Exception):
    def __init__(self, msg: str):
        super().__init__(f"[RuntimeError] {msg}")


# ─────────────────────────────────────────────
#  Call Frame
# ─────────────────────────────────────────────

class Frame:
    def __init__(self, func_name: str, return_addr: int, return_dest: Optional[str]):
        self.name = func_name
        self.return_addr = return_addr    # PC to resume after return
        self.return_dest = return_dest    # variable to store return value
        self.locals: Dict[str, float] = {}

    def __repr__(self):
        return f"Frame({self.name!r}, ret_addr={self.return_addr})"


# ─────────────────────────────────────────────
#  Built-in function table
# ─────────────────────────────────────────────

BUILTINS: Dict[str, Any] = {
    "sqrt": lambda args: math.sqrt(args[0]),
    "abs":  lambda args: abs(args[0]),
    "sin":  lambda args: math.sin(args[0]),
    "cos":  lambda args: math.cos(args[0]),
    "log":  lambda args: math.log(args[0]),
    "tan":  lambda args: math.tan(args[0]),
}


# ─────────────────────────────────────────────
#  Virtual Machine
# ─────────────────────────────────────────────

class VM:
    """
    Executes an optimized TAC instruction list.

    Usage:
        vm = VM()
        vm.run(instrs)
    """

    def __init__(self, debug: bool = False):
        self.debug        = debug
        self._globals: Dict[str, float] = {}
        self._call_stack: List[Frame]   = []
        # Maps function name -> index of its FuncBegin instruction
        self._func_map:   Dict[str, int] = {}
        # Maps label name -> instruction index
        self._label_map:  Dict[str, int] = {}

    # ── Public entry point ───────────────────────

    def run(self, instrs: List[TACInstr]) -> None:
        self._globals    = {}
        self._call_stack = []
        self._pre_index(instrs)

        pc = 0
        while pc < len(instrs):
            instr = instrs[pc]

            if self.debug:
                frame_name = self._call_stack[-1].name if self._call_stack else "global"
                print(f"  [VM] pc={pc:>3}  {frame_name:<12}  {str(instr).strip()}")

            # ── Skip function bodies during top-level pass ──
            if isinstance(instr, FuncBegin):
                # Jump past FuncEnd so we don't execute the body on first pass
                pc = self._skip_func(instrs, pc)
                continue

            if isinstance(instr, FuncEnd):
                # Should only reach here if a function had no return statement
                # (treat as implicit return None → 0)
                if self._call_stack:
                    pc = self._do_return(instrs, 0.0)
                    continue
                pc += 1
                continue

            # ── Copy ──
            elif isinstance(instr, Copy):
                val = self._resolve(instr.src)
                self._store(instr.result, val)
                pc += 1

            # ── BinaryOp ──
            elif isinstance(instr, BinaryOp):
                left  = self._resolve(instr.left)
                right = self._resolve(instr.right)
                val   = self._apply_op(instr.op, left, right)
                self._store(instr.result, val)
                pc += 1

            # ── UnaryOp ──
            elif isinstance(instr, UnaryOp):
                operand = self._resolve(instr.operand)
                if instr.op == "-":
                    val = -operand
                else:
                    raise RuntimeError_(f"Unknown unary op: {instr.op}")
                self._store(instr.result, val)
                pc += 1

            # ── CallInstr ──
            elif isinstance(instr, CallInstr):
                args = [self._resolve(a) for a in instr.args]

                # Built-in?
                if instr.func_name in BUILTINS:
                    try:
                        result = BUILTINS[instr.func_name](args)
                    except Exception as e:
                        raise RuntimeError_(f"Built-in '{instr.func_name}' error: {e}")
                    self._store(instr.result, result)
                    pc += 1

                # User-defined function
                elif instr.func_name in self._func_map:
                    func_start = self._func_map[instr.func_name]
                    func_begin = instrs[func_start]

                    # Push frame
                    frame = Frame(
                        func_name   = instr.func_name,
                        return_addr = pc + 1,
                        return_dest = instr.result,
                    )
                    # Bind arguments to parameter names
                    for param, val in zip(func_begin.params, args):
                        frame.locals[param] = val

                    self._call_stack.append(frame)
                    pc = func_start + 1   # jump into function body (skip FuncBegin)

                else:
                    raise RuntimeError_(f"Undefined function: '{instr.func_name}'")

            # ── PrintInstr ──
            elif isinstance(instr, PrintInstr):
                val = self._resolve(instr.value)
                self._print_value(val)
                pc += 1

            # ── ReturnInstr ──
            elif isinstance(instr, ReturnInstr):
                val = self._resolve(instr.value)
                pc  = self._do_return(instrs, val)

            # ── LabelInstr ──
            elif isinstance(instr, LabelInstr):
                pc += 1   # labels are no-ops at runtime

            # ── GotoInstr ──
            elif isinstance(instr, GotoInstr):
                pc = self._label_map[instr.label]

            # ── IfFalseGoto ──
            elif isinstance(instr, IfFalseGoto):
                cond = self._resolve(instr.condition)
                if cond == 0.0:
                    pc = self._label_map[instr.label]
                else:
                    pc += 1

            else:
                pc += 1   # unknown instruction — skip

    # ── Helpers ─────────────────────────────────

    def _pre_index(self, instrs: List[TACInstr]) -> None:
        """Build label_map and func_map before execution."""
        for i, instr in enumerate(instrs):
            if isinstance(instr, LabelInstr):
                self._label_map[instr.name] = i
            elif isinstance(instr, FuncBegin):
                self._func_map[instr.name] = i

    def _skip_func(self, instrs: List[TACInstr], start: int) -> int:
        """Return index just after the FuncEnd matching FuncBegin at start."""
        depth = 0
        for i in range(start, len(instrs)):
            if isinstance(instrs[i], FuncBegin):
                depth += 1
            elif isinstance(instrs[i], FuncEnd):
                depth -= 1
                if depth == 0:
                    return i + 1
        return len(instrs)

    def _do_return(self, instrs: List[TACInstr], val: float) -> int:
        """Pop the call stack and store the return value. Return new PC."""
        if not self._call_stack:
            raise RuntimeError_("return outside function")
        frame = self._call_stack.pop()
        if frame.return_dest is not None:
            self._store(frame.return_dest, val)
        return frame.return_addr

    def _resolve(self, name: str) -> float:
        """Resolve a name or literal to a float."""
        # Numeric literal
        try:
            return float(name)
        except (ValueError, TypeError):
            pass

        # Local scope first
        if self._call_stack:
            frame = self._call_stack[-1]
            if name in frame.locals:
                return frame.locals[name]

        # Global scope
        if name in self._globals:
            return self._globals[name]

        raise RuntimeError_(f"Undefined variable '{name}' at runtime")

    def _store(self, name: str, val: float) -> None:
        """Store a value — locals if inside a function, else globals."""
        if self._call_stack:
            self._call_stack[-1].locals[name] = val
        else:
            self._globals[name] = val

    def _apply_op(self, op: str, left: float, right: float) -> float:
        if op == "+":  return left + right
        if op == "-":  return left - right
        if op == "*":  return left * right
        if op == "/":
            if right == 0:
                raise RuntimeError_("Division by zero")
            return left / right
        if op == "^":  return left ** right
        if op == "==": return float(left == right)
        if op == "!=": return float(left != right)
        if op == "<":  return float(left < right)
        if op == ">":  return float(left > right)
        if op == "<=": return float(left <= right)
        if op == ">=": return float(left >= right)
        raise RuntimeError_(f"Unknown operator: '{op}'")

    def _print_value(self, val: float) -> None:
        """Display in classic calculator style."""
        if val == int(val) and not math.isinf(val):
            display = str(int(val))
        else:
            display = f"{val:.6g}"
        print(f"  >> {display}")