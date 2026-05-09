"""
CalcScript VM Test Suite - Phase 6
====================================
Run: python test_vm.py
"""

import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer
from ir_gen import IRGenerator
from optimizer import Optimizer
from vm import VM, RuntimeError_

passed = failed = 0


def run_calc(source: str) -> str:
    """Full pipeline: source -> printed output (captured as string)."""
    tokens    = Lexer(source).tokenize()
    tree      = Parser(tokens).parse()
    SemanticAnalyzer().analyze(tree)
    instrs    = IRGenerator().generate(tree)
    optimized = Optimizer().optimize(instrs)
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        VM().run(optimized)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue().strip()


def run_test(name, fn):
    global passed, failed
    try:
        fn()
        print(f"  [PASS] {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        failed += 1


def run_error_test(name, source, fragment):
    global passed, failed
    try:
        run_calc(source)
        print(f"  [FAIL] {name}: expected RuntimeError, got none")
        failed += 1
    except RuntimeError_ as e:
        if fragment.lower() in str(e).lower():
            print(f"  [PASS] {name}")
            passed += 1
        else:
            print(f"  [FAIL] {name}: wrong error — {e}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] {name}: unexpected — {e}")
        failed += 1


# ─────────────────────────────────────────────
print("\n── 1. Basic arithmetic ──────────────────────")
# ─────────────────────────────────────────────

def t_add():
    out = run_calc("print 3 + 4")
    assert "7" in out, f"got: {out}"
run_test("3 + 4 = 7", t_add)

def t_sub():
    out = run_calc("print 10 - 3")
    assert "7" in out
run_test("10 - 3 = 7", t_sub)

def t_mul():
    out = run_calc("print 6 * 7")
    assert "42" in out
run_test("6 * 7 = 42", t_mul)

def t_div():
    out = run_calc("print 10 / 2")
    assert "5" in out
run_test("10 / 2 = 5", t_div)

def t_power():
    out = run_calc("print 2 ^ 10")
    assert "1024" in out
run_test("2 ^ 10 = 1024", t_power)

def t_precedence():
    out = run_calc("print 2 + 3 * 4")
    assert "14" in out
run_test("2 + 3 * 4 = 14 (precedence)", t_precedence)

def t_parens():
    out = run_calc("print (2 + 3) * 4")
    assert "20" in out
run_test("(2 + 3) * 4 = 20", t_parens)

def t_unary_minus():
    out = run_calc("x = 5\nprint -x")
    assert "-5" in out
run_test("unary minus: -5", t_unary_minus)


# ─────────────────────────────────────────────
print("\n── 2. Variables ─────────────────────────────")
# ─────────────────────────────────────────────

def t_var_assign_print():
    out = run_calc("x = 42\nprint x")
    assert "42" in out
run_test("assign and print variable", t_var_assign_print)

def t_multi_var():
    out = run_calc("x = 3\ny = 4\nz = x + y\nprint z")
    assert "7" in out
run_test("multiple variables, sum", t_multi_var)

def t_var_reassign():
    out = run_calc("x = 1\nx = 99\nprint x")
    assert "99" in out
run_test("variable re-assignment", t_var_reassign)


# ─────────────────────────────────────────────
print("\n── 3. Built-in functions ────────────────────")
# ─────────────────────────────────────────────

def t_sqrt():
    out = run_calc("print sqrt(16)")
    assert "4" in out
run_test("sqrt(16) = 4", t_sqrt)

def t_abs_neg():
    out = run_calc("x = -9\nprint abs(x)")
    assert "9" in out
run_test("abs(-9) = 9", t_abs_neg)

def t_sin_zero():
    out = run_calc("print sin(0)")
    assert "0" in out
run_test("sin(0) = 0", t_sin_zero)

def t_cos_zero():
    out = run_calc("print cos(0)")
    assert "1" in out
run_test("cos(0) = 1", t_cos_zero)

def t_log():
    out = run_calc("print log(1)")
    assert "0" in out
run_test("log(1) = 0", t_log)

def t_nested_builtins():
    out = run_calc("x = -16\nprint sqrt(abs(x))")
    assert "4" in out
run_test("sqrt(abs(-16)) = 4", t_nested_builtins)


# ─────────────────────────────────────────────
print("\n── 4. User-defined functions ────────────────")
# ─────────────────────────────────────────────

def t_func_single_line():
    out = run_calc("func square(n) => n * n\nprint square(5)")
    assert "25" in out
run_test("func square(5) = 25", t_func_single_line)

def t_func_two_params():
    out = run_calc("func add(a, b) => a + b\nprint add(3, 4)")
    assert "7" in out
run_test("func add(3, 4) = 7", t_func_two_params)

def t_func_multiline():
    src = "func double(n)\nx = n * 2\nreturn x\nend\nprint double(6)"
    out = run_calc(src)
    assert "12" in out
run_test("multi-line func double(6) = 12", t_func_multiline)

def t_func_uses_builtin():
    out = run_calc("func hyp(a, b) => sqrt(a ^ 2 + b ^ 2)\nprint hyp(3, 4)")
    assert "5" in out
run_test("hyp(3,4) = 5 (Pythagorean)", t_func_uses_builtin)

def t_func_nested_call():
    out = run_calc("func sq(n) => n * n\nfunc sum_sq(a,b) => sq(a) + sq(b)\nprint sum_sq(3,4)")
    assert "25" in out
run_test("nested user func calls: sum_sq(3,4) = 25", t_func_nested_call)

def t_func_no_params():
    out = run_calc("func answer() => 42\nprint answer()")
    assert "42" in out
run_test("no-param func: answer() = 42", t_func_no_params)


# ─────────────────────────────────────────────
print("\n── 5. If / else ─────────────────────────────")
# ─────────────────────────────────────────────

def t_if_true():
    out = run_calc("x = 5\nif x > 0 then\nprint x\nend")
    assert "5" in out
run_test("if true branch executes", t_if_true)

def t_if_false():
    out = run_calc("x = -1\nif x > 0 then\nprint 99\nend")
    assert "99" not in out
run_test("if false branch skipped", t_if_false)

def t_if_else_true():
    out = run_calc("x = 5\nif x > 0 then\nprint 1\nelse\nprint 0\nend")
    assert "1" in out and "0" not in out
run_test("if-else: true branch", t_if_else_true)

def t_if_else_false():
    out = run_calc("x = -1\nif x > 0 then\nprint 1\nelse\nprint 0\nend")
    assert "0" in out and "1" not in out
run_test("if-else: false branch", t_if_else_false)

def t_comparison_eq():
    out = run_calc("x = 5\nif x == 5 then\nprint 1\nend")
    assert "1" in out
run_test("== comparison", t_comparison_eq)

def t_comparison_lte():
    out = run_calc("x = 3\nif x <= 3 then\nprint 1\nend")
    assert "1" in out
run_test("<= comparison", t_comparison_lte)


# ─────────────────────────────────────────────
print("\n── 6. Repeat loop ───────────────────────────")
# ─────────────────────────────────────────────

def t_repeat_basic():
    out = run_calc("x = 0\nrepeat 3 times\nx = x + 1\nend\nprint x")
    assert "3" in out
run_test("repeat 3 times: x = 3", t_repeat_basic)

def t_repeat_multiply():
    out = run_calc("x = 1\nrepeat 5 times\nx = x * 2\nend\nprint x")
    assert "32" in out
run_test("repeat 5 times doubling: x = 32", t_repeat_multiply)

def t_repeat_zero():
    out = run_calc("x = 99\nrepeat 0 times\nx = 0\nend\nprint x")
    assert "99" in out
run_test("repeat 0 times: body skipped", t_repeat_zero)


# ─────────────────────────────────────────────
print("\n── 7. Runtime errors ────────────────────────")
# ─────────────────────────────────────────────

run_error_test("division by zero", "print 10 / 0", "Division by zero")
run_error_test("sqrt of negative", "print sqrt(-1)", "sqrt")


# ─────────────────────────────────────────────
print("\n── 8. Full sample programs ──────────────────")
# ─────────────────────────────────────────────

def t_sample1():
    src = open("sample1.calc").read()
    out = run_calc(src)
    lines = out.split("\n")
    # sqrt(16) = 4, 3.14159^2 = ~9.8696
    assert any("4" in l for l in lines)
run_test("sample1.calc runs without error", t_sample1)

def t_sample2():
    src = open("sample2.calc").read()
    out = run_calc(src)
    assert any("5" in l for l in out.split("\n"))
run_test("sample2.calc: hyp(3,4)=5", t_sample2)

def t_sample3():
    src = open("sample3.calc").read()
    out = run_calc(src)
    assert "32" in out
run_test("sample3.calc: repeat 5 times doubling = 32", t_sample3)


# ─────────────────────────────────────────────
print("\n── 9. Output demonstration ──────────────────")
# ─────────────────────────────────────────────

demos = [
    ("Arithmetic",      "print 2 ^ 10"),
    ("Pythagorean",     "func hyp(a,b) => sqrt(a^2 + b^2)\nprint hyp(3,4)"),
    ("Factorial-like",  "x = 1\nrepeat 6 times\nx = x * 2\nend\nprint x"),
    ("Conditional",     "x = 7\nif x > 5 then\nprint x\nelse\nprint 0\nend"),
    ("Built-ins",       "print sqrt(144)\nprint abs(-99)\nprint cos(0)"),
]

for title, src in demos:
    print(f"\n  {title}: {src.split(chr(10))[0]}")
    tokens    = Lexer(src).tokenize()
    tree      = Parser(tokens).parse()
    SemanticAnalyzer().analyze(tree)
    instrs    = IRGenerator().generate(tree)
    optimized = Optimizer().optimize(instrs)
    VM().run(optimized)


# ─────────────────────────────────────────────
total = passed + failed
print(f"\n{'='*45}")
print(f"  Results: {passed}/{total} passed", end="")
if failed == 0:
    print("  All tests passed!")
else:
    print(f"  {failed} failed")
print(f"{'='*45}\n")