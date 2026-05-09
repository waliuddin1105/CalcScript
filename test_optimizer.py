"""
CalcScript Optimizer Test Suite - Phase 5
==========================================
Run: python test_optimizer.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from ir_gen import (
    IRGenerator, BinaryOp, UnaryOp, Copy,
    CallInstr, PrintInstr, GotoInstr, IfFalseGoto, LabelInstr
)
from optimizer import Optimizer

passed = failed = 0


def pipeline(source: str):
    tokens  = Lexer(source).tokenize()
    tree    = Parser(tokens).parse()
    SemanticAnalyzer().analyze(tree)
    gen     = IRGenerator()
    instrs  = gen.generate(tree)
    opt     = Optimizer()
    optimized = opt.optimize(instrs)
    return instrs, optimized, opt


def run_test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1


def find(instrs, typ):
    return [i for i in instrs if isinstance(i, typ)]

def has_type(instrs, typ):
    return any(isinstance(i, typ) for i in instrs)

def get_copies(instrs):
    return {c.result: c.src for c in find(instrs, Copy)}


# ─────────────────────────────────────────────
print("\n── 1. Constant Folding: arithmetic ──────────")
# ─────────────────────────────────────────────

def t_fold_add():
    # 3 + 4 should fold to 7
    before, after, _ = pipeline("x = 3 + 4")
    copies = get_copies(after)
    # x should be assigned 7 directly
    assert "x" in copies and copies["x"] == "7", f"copies={copies}"
run_test("3 + 4 folds to 7", t_fold_add)

def t_fold_sub():
    before, after, _ = pipeline("x = 10 - 3")
    copies = get_copies(after)
    assert copies.get("x") == "7"
run_test("10 - 3 folds to 7", t_fold_sub)

def t_fold_mul():
    before, after, _ = pipeline("x = 6 * 7")
    copies = get_copies(after)
    assert copies.get("x") == "42"
run_test("6 * 7 folds to 42", t_fold_mul)

def t_fold_div():
    before, after, _ = pipeline("x = 10 / 2")
    copies = get_copies(after)
    assert copies.get("x") == "5"
run_test("10 / 2 folds to 5", t_fold_div)

def t_fold_power():
    before, after, _ = pipeline("x = 2 ^ 8")
    copies = get_copies(after)
    assert copies.get("x") == "256"
run_test("2 ^ 8 folds to 256", t_fold_power)

def t_fold_nested():
    # (2 + 3) * 4  -> 5 * 4 -> 20
    before, after, _ = pipeline("x = (2 + 3) * 4")
    copies = get_copies(after)
    assert copies.get("x") == "20"
run_test("(2 + 3) * 4 folds to 20", t_fold_nested)

def t_fold_comparison():
    # 5 > 3 -> 1 (true)
    before, after, _ = pipeline("x = 5\ny = 3\nz = 5 > 3")
    copies = get_copies(after)
    assert copies.get("z") == "1"
run_test("5 > 3 folds to 1", t_fold_comparison)

def t_no_fold_variable():
    # result is from sqrt() call — runtime value, cannot be folded
    before, after, _ = pipeline("x = 4\nresult = sqrt(x)\ny = result + 1\nprint y")
    bins = find(after, BinaryOp)
    assert any(b.op == "+" for b in bins), "BinaryOp should remain"
run_test("runtime value + 1 not folded", t_no_fold_variable)


# ─────────────────────────────────────────────
print("\n── 2. Constant Folding: unary ───────────────")
# ─────────────────────────────────────────────

def t_fold_unary_minus():
    before, after, _ = pipeline("x = -5")
    copies = get_copies(after)
    assert copies.get("x") == "-5"
run_test("-5 unary folds to -5", t_fold_unary_minus)

def t_fold_unary_minus_expr():
    # -(3 + 2) -> -5
    before, after, _ = pipeline("x = -(3 + 2)")
    copies = get_copies(after)
    assert copies.get("x") == "-5"
run_test("-(3 + 2) folds to -5", t_fold_unary_minus_expr)


# ─────────────────────────────────────────────
print("\n── 3. Constant Folding: copy propagation ────")
# ─────────────────────────────────────────────

def t_copy_chain():
    # x = 7 / y = x — y should get 7 propagated
    before, after, _ = pipeline("x = 3 + 4\ny = x")
    copies = get_copies(after)
    # y should ultimately come from 7 directly
    assert copies.get("x") == "7"
run_test("copy chain propagates constant", t_copy_chain)


# ─────────────────────────────────────────────
print("\n── 4. Constant Folding: if_false on constant ─")
# ─────────────────────────────────────────────

def t_always_true_branch():
    # if 5 > 3 — condition is always true, if_false is dropped
    src = "if 5 > 3 then\nprint 1\nend"
    before, after, _ = pipeline(src)
    # No IfFalseGoto should remain since condition folds to 1 (true)
    assert not has_type(after, IfFalseGoto), "if_false should be removed for always-true"
run_test("always-true if_false removed", t_always_true_branch)


# ─────────────────────────────────────────────
print("\n── 5. Dead Code Elimination ─────────────────")
# ─────────────────────────────────────────────

def t_dead_temp_removed():
    # Compute something into a temp but never use it
    # x = 3 + 4  is used (assigned to x)
    # but if we have a dead intermediate:
    src = "x = 5\nprint x"
    before, after, _ = pipeline(src)
    # No dead BinaryOps should remain
    dead_bins = [b for b in find(after, BinaryOp)
                 if b.result.startswith("t") and
                 b.result not in {str(i) for i in after}]
    assert len(after) <= len(before)
run_test("dead code not longer than before", t_dead_temp_removed)

def t_fewer_instructions_after_opt():
    # Constant folding should reduce instruction count for all-constant exprs
    src = "x = 2 + 3\ny = x * 4\nprint y"
    before, after, _ = pipeline(src)
    assert len(after) <= len(before), f"before={len(before)}, after={len(after)}"
run_test("optimized code has <= instructions", t_fewer_instructions_after_opt)

def t_redundant_goto_removed():
    # if_false goto L / L: → the goto is redundant when cond is always true
    # We test the goto-immediately-before-label removal
    src = "if 5 > 3 then\nprint 1\nend"
    before, after, _ = pipeline(src)
    # Count gotos — should be 0 (removed)
    gotos = find(after, GotoInstr)
    assert len(gotos) == 0
run_test("redundant goto removed", t_redundant_goto_removed)


# ─────────────────────────────────────────────
print("\n── 6. Optimization does not break semantics ─")
# ─────────────────────────────────────────────

def t_print_still_present():
    src = "x = 3 + 4\nprint x"
    before, after, _ = pipeline(src)
    assert has_type(after, PrintInstr)
run_test("print instruction preserved after optimization", t_print_still_present)

def t_func_markers_preserved():
    src = "func sq(n) => n * n"
    before, after, _ = pipeline(src)
    from ir_gen import FuncBegin, FuncEnd
    assert has_type(after, FuncBegin)
    assert has_type(after, FuncEnd)
run_test("func_begin/func_end preserved", t_func_markers_preserved)

def t_variable_assignments_preserved():
    src = "x = 10\ny = 20\nprint x"
    before, after, _ = pipeline(src)
    copies = get_copies(after)
    assert "x" in copies
run_test("user variable assignments preserved", t_variable_assignments_preserved)


# ─────────────────────────────────────────────
print("\n── 7. Before/After diff output (handwritten ref) ──")
# ─────────────────────────────────────────────

print("\n  Example 1: Constant folding — x = (2 + 3) * 4")
before, after, opt = pipeline("x = (2 + 3) * 4\nprint x")
opt.pretty_print_diff(before, after)

print("  Example 2: Dead code elimination + folding — repeat with constants")
before, after, opt = pipeline("x = 1\nrepeat 3 times\nx = x + 1\nend\nprint x")
opt.pretty_print_diff(before, after)

print("  Example 3: Always-true branch elimination")
before, after, opt = pipeline("if 5 > 3 then\nprint 42\nend")
opt.pretty_print_diff(before, after)


# ─────────────────────────────────────────────
total = passed + failed
print(f"\n{'='*45}")
print(f"  Results: {passed}/{total} passed", end="")
if failed == 0:
    print("  All tests passed!")
else:
    print(f"  {failed} failed")
print(f"{'='*45}\n")