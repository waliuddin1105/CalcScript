"""
CalcScript IR Generator Test Suite - Phase 4
=============================================
Run: python test_ir.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from ir_gen import (
    IRGenerator,
    BinaryOp, UnaryOp, Copy, CallInstr, PrintInstr,
    ReturnInstr, LabelInstr, GotoInstr, IfFalseGoto,
    FuncBegin, FuncEnd,
)

passed = failed = 0


def pipeline(source: str):
    tokens = Lexer(source).tokenize()
    tree   = Parser(tokens).parse()
    SemanticAnalyzer().analyze(tree)
    gen    = IRGenerator()
    instrs = gen.generate(tree)
    return instrs, gen


def run_test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1


def has_type(instrs, typ):
    return any(isinstance(i, typ) for i in instrs)

def count_type(instrs, typ):
    return sum(1 for i in instrs if isinstance(i, typ))

def find(instrs, typ):
    return [i for i in instrs if isinstance(i, typ)]


# ─────────────────────────────────────────────
print("\n── 1. Number & variable expressions ─────────")
# ─────────────────────────────────────────────

def t_number_assign():
    instrs, _ = pipeline("x = 5")
    copies = find(instrs, Copy)
    assert any(c.result == "x" and c.src == "5" for c in copies)
run_test("number literal assigned via Copy", t_number_assign)

def t_var_assign():
    instrs, _ = pipeline("x = 5\ny = x")
    copies = find(instrs, Copy)
    assert any(c.result == "y" and c.src == "x" for c in copies)
run_test("variable copy", t_var_assign)


# ─────────────────────────────────────────────
print("\n── 2. Binary expressions ────────────────────")
# ─────────────────────────────────────────────

def t_addition():
    instrs, _ = pipeline("x = 1\ny = 2\nz = x + y")
    bins = find(instrs, BinaryOp)
    assert any(b.op == "+" and b.left == "x" and b.right == "y" for b in bins)
run_test("addition produces BinaryOp", t_addition)

def t_precedence():
    instrs, _ = pipeline("z = 1 + 2 * 3")
    bins = find(instrs, BinaryOp)
    # * must appear before +
    mul_idx = next(i for i,b in enumerate(bins) if b.op == "*")
    add_idx = next(i for i,b in enumerate(bins) if b.op == "+")
    assert mul_idx < add_idx
run_test("* evaluated before + (precedence preserved)", t_precedence)

def t_power():
    instrs, _ = pipeline("z = 2 ^ 3")
    bins = find(instrs, BinaryOp)
    assert any(b.op == "^" for b in bins)
run_test("power operator generates BinaryOp ^", t_power)

def t_comparison():
    instrs, _ = pipeline("x = 5\ny = x > 3")
    bins = find(instrs, BinaryOp)
    assert any(b.op == ">" for b in bins)
run_test("comparison generates BinaryOp >", t_comparison)


# ─────────────────────────────────────────────
print("\n── 3. Unary expressions ─────────────────────")
# ─────────────────────────────────────────────

def t_unary_minus():
    instrs, _ = pipeline("x = 5\ny = -x")
    assert has_type(instrs, UnaryOp)
    uop = find(instrs, UnaryOp)[0]
    assert uop.op == "-" and uop.operand == "x"
run_test("unary minus generates UnaryOp", t_unary_minus)


# ─────────────────────────────────────────────
print("\n── 4. Function calls ────────────────────────")
# ─────────────────────────────────────────────

def t_builtin_call():
    instrs, _ = pipeline("x = 4\nresult = sqrt(x)")
    calls = find(instrs, CallInstr)
    assert any(c.func_name == "sqrt" and c.args == ["x"] for c in calls)
run_test("built-in call generates CallInstr", t_builtin_call)

def t_user_func_call():
    instrs, _ = pipeline("func sq(n) => n * n\ny = sq(4)")
    calls = find(instrs, CallInstr)
    assert any(c.func_name == "sq" for c in calls)
run_test("user function call generates CallInstr", t_user_func_call)

def t_nested_call():
    instrs, _ = pipeline("x = 4\nresult = sqrt(abs(x))")
    calls = find(instrs, CallInstr)
    assert count_type(instrs, CallInstr) == 2
run_test("nested calls generate two CallInstrs", t_nested_call)


# ─────────────────────────────────────────────
print("\n── 5. Print statement ───────────────────────")
# ─────────────────────────────────────────────

def t_print():
    instrs, _ = pipeline("x = 5\nprint x")
    prints = find(instrs, PrintInstr)
    assert len(prints) == 1 and prints[0].value == "x"
run_test("print generates PrintInstr", t_print)

def t_print_expr():
    instrs, _ = pipeline("x = 5\nprint x + 1")
    assert has_type(instrs, PrintInstr)
    assert has_type(instrs, BinaryOp)
run_test("print expression generates BinaryOp + PrintInstr", t_print_expr)


# ─────────────────────────────────────────────
print("\n── 6. Function definitions ──────────────────")
# ─────────────────────────────────────────────

def t_func_def_markers():
    instrs, _ = pipeline("func square(n) => n * n")
    assert has_type(instrs, FuncBegin)
    assert has_type(instrs, FuncEnd)
    fb = find(instrs, FuncBegin)[0]
    assert fb.name == "square" and fb.params == ["n"]
run_test("func def has FuncBegin and FuncEnd", t_func_def_markers)

def t_func_def_return():
    instrs, _ = pipeline("func square(n) => n * n")
    assert has_type(instrs, ReturnInstr)
run_test("single-line func body ends with ReturnInstr", t_func_def_return)

def t_func_multiline():
    src = "func double(n)\nx = n * 2\nreturn x\nend"
    instrs, _ = pipeline(src)
    assert has_type(instrs, FuncBegin)
    assert has_type(instrs, ReturnInstr)
    assert has_type(instrs, FuncEnd)
run_test("multi-line func generates correct structure", t_func_multiline)


# ─────────────────────────────────────────────
print("\n── 7. If statement ──────────────────────────")
# ─────────────────────────────────────────────

def t_if_simple():
    src = "x = 5\nif x > 0 then\nprint x\nend"
    instrs, _ = pipeline(src)
    assert has_type(instrs, IfFalseGoto)
    assert has_type(instrs, LabelInstr)
    assert has_type(instrs, PrintInstr)
run_test("if generates IfFalseGoto + Label", t_if_simple)

def t_if_else():
    src = "x = 5\nif x > 0 then\nprint x\nelse\nprint 0\nend"
    instrs, _ = pipeline(src)
    assert count_type(instrs, LabelInstr) == 2
    assert has_type(instrs, GotoInstr)
run_test("if-else generates 2 labels + GotoInstr", t_if_else)


# ─────────────────────────────────────────────
print("\n── 8. Repeat loop ───────────────────────────")
# ─────────────────────────────────────────────

def t_repeat():
    src = "x = 1\nrepeat 3 times\nx = x + 1\nend"
    instrs, _ = pipeline(src)
    assert has_type(instrs, LabelInstr)
    assert has_type(instrs, GotoInstr)
    assert has_type(instrs, IfFalseGoto)
    # loop label + end label = 2 labels
    assert count_type(instrs, LabelInstr) == 2
run_test("repeat generates loop structure with labels", t_repeat)


# ─────────────────────────────────────────────
print("\n── 9. Temp variable naming ──────────────────")
# ─────────────────────────────────────────────

def t_temps_sequential():
    instrs, gen = pipeline("z = 1 + 2 + 3")
    bins = find(instrs, BinaryOp)
    # Each result should be t0, t1, ...
    results = [b.result for b in bins]
    assert all(r.startswith("t") for r in results)
run_test("temp variables named t0, t1, t2...", t_temps_sequential)


# ─────────────────────────────────────────────
print("\n── 10. Full program TAC output ──────────────")
# ─────────────────────────────────────────────

print("\n  --- TAC: sample program 1 (assign + sqrt + print) ---")
instrs, gen = pipeline("""x = 16
result = sqrt(x)
print result""")
gen.pretty_print()

print("  --- TAC: sample program 2 (func + if) ---")
instrs, gen = pipeline("""func square(n) => n * n
y = 3
if y > 2 then
print square(y)
end""")
gen.pretty_print()

print("  --- TAC: sample program 3 (repeat loop) ---")
instrs, gen = pipeline("""x = 1
repeat 5 times
x = x + 1
end
print x""")
gen.pretty_print()


# ─────────────────────────────────────────────
total = passed + failed
print(f"\n{'='*45}")
print(f"  Results: {passed}/{total} passed", end="")
if failed == 0:
    print("  All tests passed!")
else:
    print(f"  {failed} failed")
print(f"{'='*45}\n")