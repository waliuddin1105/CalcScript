"""
CalcScript Optimizer - Phase 5: Basic Optimization
===================================================
Implements two optimizations on the TAC instruction list:

1. CONSTANT FOLDING
   Evaluates expressions with all-constant operands at compile time.
   Before:  t0 = 3 + 4       After:  t0 = 7
   Before:  t1 = 2 ^ 10      After:  t1 = 1024
   Before:  t2 = -5.0        After:  t2 = -5.0
   Also folds Copy chains:
   Before:  t0 = 7 / result = t0    After: result = 7

2. DEAD CODE ELIMINATION
   Removes instructions whose result is computed but never used.
   Before:                    After:
     t0 = 3 + 4   (unused)    (removed)
     t1 = x + 1               t1 = x + 1
     print t1                 print t1

   Also removes:
   - goto immediately followed by its own label (goto L / L:)
   - if_false on a known-true/false constant condition
"""

import math
from typing import List, Set, Dict, Optional
from ir_gen import (
    TACInstr, BinaryOp, UnaryOp, Copy, CallInstr,
    PrintInstr, ReturnInstr, LabelInstr, GotoInstr,
    IfFalseGoto, FuncBegin, FuncEnd,
)


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def _to_num(s: str) -> float:
    return float(s)


def _fmt(v: float) -> str:
    """Format a number cleanly — no trailing .0 for integers."""
    if v == int(v) and not math.isinf(v):
        return str(int(v))
    return str(v)


def _apply_op(op: str, left: float, right: float) -> Optional[float]:
    """Evaluate a binary op on two constants. Returns None if undefined."""
    try:
        if op == "+":  return left + right
        if op == "-":  return left - right
        if op == "*":  return left * right
        if op == "/":
            if right == 0: return None       # avoid div-by-zero at compile time
            return left / right
        if op == "^":  return left ** right
        if op == "==": return float(left == right)
        if op == "!=": return float(left != right)
        if op == "<":  return float(left < right)
        if op == ">":  return float(left > right)
        if op == "<=": return float(left <= right)
        if op == ">=": return float(left >= right)
    except Exception:
        return None
    return None


# ─────────────────────────────────────────────
#  Optimizer
# ─────────────────────────────────────────────

class Optimizer:
    """
    Two-pass optimizer over a TAC instruction list.

    Pass 1 — Constant Folding:
      Maintains a constant map {name -> value_str}.
      For each instruction, if all operands are known constants,
      replace the instruction with a Copy of the folded value.

    Pass 2 — Dead Code Elimination:
      Collects all names that are ever READ (used).
      Removes BinaryOp/UnaryOp/Copy instructions whose result
      is never read anywhere downstream.
      Also removes redundant goto-label pairs.

    Usage:
        opt    = Optimizer()
        result = opt.optimize(instrs)
        opt.pretty_print_diff(original, result)
    """

    def optimize(self, instrs: List[TACInstr]) -> List[TACInstr]:
        after_fold = self._constant_fold(instrs)
        after_dce  = self._dead_code_elim(after_fold)
        return after_dce

    # ── Pass 1: Constant Folding ─────────────────

    def _constant_fold(self, instrs: List[TACInstr]) -> List[TACInstr]:
        """
        Walk instructions top-to-bottom.
        Maintain const_map: variable/temp -> constant string.
        When an instruction's operands are all in const_map, fold it.
        """
        const_map: Dict[str, str] = {}
        result: List[TACInstr] = []

        for instr in instrs:

            # ── BinaryOp ──
            if isinstance(instr, BinaryOp):
                left  = const_map.get(instr.left,  instr.left)
                right = const_map.get(instr.right, instr.right)

                if _is_number(left) and _is_number(right):
                    folded = _apply_op(instr.op, _to_num(left), _to_num(right))
                    if folded is not None:
                        val = _fmt(folded)
                        const_map[instr.result] = val
                        result.append(Copy(instr.result, val))
                        continue

                # Partial fold: substitute known operands
                new_instr = BinaryOp(instr.result, left, instr.op, right)
                # If result was previously constant, invalidate it
                const_map.pop(instr.result, None)
                result.append(new_instr)

            # ── UnaryOp ──
            elif isinstance(instr, UnaryOp):
                operand = const_map.get(instr.operand, instr.operand)
                if instr.op == "-" and _is_number(operand):
                    val = _fmt(-_to_num(operand))
                    const_map[instr.result] = val
                    result.append(Copy(instr.result, val))
                    continue
                const_map.pop(instr.result, None)
                result.append(UnaryOp(instr.result, instr.op, operand))

            # ── Copy ──
            elif isinstance(instr, Copy):
                src = const_map.get(instr.src, instr.src)
                if _is_number(src):
                    const_map[instr.result] = src
                else:
                    # Propagate const through copy chain
                    if instr.src in const_map:
                        const_map[instr.result] = const_map[instr.src]
                    else:
                        const_map.pop(instr.result, None)
                result.append(Copy(instr.result, src))

            # ── IfFalseGoto on known constant ──
            elif isinstance(instr, IfFalseGoto):
                cond = const_map.get(instr.condition, instr.condition)
                if _is_number(cond):
                    if _to_num(cond) != 0:
                        # Condition always true → if_false never jumps → drop it
                        continue
                    else:
                        # Condition always false → always jumps → replace with goto
                        result.append(GotoInstr(instr.label))
                        continue
                result.append(IfFalseGoto(cond, instr.label))

            # ── LabelInstr: clear const_map to avoid folding across jumps ──
            elif isinstance(instr, LabelInstr):
                # A label means control flow can jump here from multiple paths.
                # We must not assume constants from before the jump are still valid.
                const_map.clear()
                result.append(instr)

            # ── Everything else passes through unchanged ──
            else:
                # Any assignment to a var from a non-const call invalidates it
                if isinstance(instr, CallInstr):
                    const_map.pop(instr.result, None)
                result.append(instr)

        return result

    # ── Pass 2: Dead Code Elimination ────────────

    def _dead_code_elim(self, instrs: List[TACInstr]) -> List[TACInstr]:
        """
        Collect all READ operands. Remove instructions that WRITE
        a temp (t0, t1, ...) that is never read.
        Also remove goto L immediately followed by L:.
        """
        used = self._collect_used(instrs)
        result: List[TACInstr] = []

        for i, instr in enumerate(instrs):
            # Remove dead BinaryOp / UnaryOp whose result is a temp never used
            if isinstance(instr, (BinaryOp, UnaryOp)):
                if instr.result.startswith("t") and instr.result not in used:
                    continue   # dead — drop it

            # Remove dead Copy whose result is a temp never used
            elif isinstance(instr, Copy):
                if instr.result.startswith("t") and instr.result not in used:
                    continue

            # Remove goto L where next instruction is L:
            elif isinstance(instr, GotoInstr):
                next_instr = instrs[i + 1] if i + 1 < len(instrs) else None
                if isinstance(next_instr, LabelInstr) and next_instr.name == instr.label:
                    continue   # goto immediately followed by its own label — redundant

            result.append(instr)

        return result

    def _collect_used(self, instrs: List[TACInstr]) -> Set[str]:
        """Return the set of all variable/temp names that are READ."""
        used: Set[str] = set()

        for instr in instrs:
            if isinstance(instr, BinaryOp):
                used.add(instr.left)
                used.add(instr.right)
            elif isinstance(instr, UnaryOp):
                used.add(instr.operand)
            elif isinstance(instr, Copy):
                used.add(instr.src)
            elif isinstance(instr, CallInstr):
                used.update(instr.args)
            elif isinstance(instr, PrintInstr):
                used.add(instr.value)
            elif isinstance(instr, ReturnInstr):
                used.add(instr.value)
            elif isinstance(instr, IfFalseGoto):
                used.add(instr.condition)

        return used

    # ── Pretty print diff ────────────────────────

    def pretty_print_diff(self,
                          before: List[TACInstr],
                          after:  List[TACInstr]) -> None:
        print("\n── Optimization: Before vs After ────────────")
        print(f"  Instructions before : {len(before)}")
        print(f"  Instructions after  : {len(after)}")
        print(f"  Removed             : {len(before) - len(after)}")

        before_strs = [str(i).strip() for i in before]
        after_strs  = [str(i).strip() for i in after]

        print("\n  BEFORE                              AFTER")
        print("  " + "─" * 70)

        max_rows = max(len(before_strs), len(after_strs))
        for i in range(max_rows):
            b = before_strs[i] if i < len(before_strs) else ""
            a = after_strs[i]  if i < len(after_strs)  else ""
            changed = b != a
            marker  = " <--folded" if changed and i < len(after_strs) else ""
            removed = "  [REMOVED]" if i >= len(after_strs) else ""
            print(f"  {b:<36}  {a}{marker}{removed}")
        print()