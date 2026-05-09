"""
CalcScript Semantic Analyzer Test Suite - Phase 3
==================================================
Run: python test_semantic.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from semantic import SemanticAnalyzer, SemanticError
from symbol_table import VarSymbol, FuncSymbol

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
passed = failed = 0


def analyze(source: str):
    tokens = Lexer(source).tokenize()
    tree   = Parser(tokens).parse()
    sa     = SemanticAnalyzer()
    sa.analyze(tree)
    return sa


def run_test(name: str, fn):
    global passed, failed
    try:
        fn()
        print(f"  {PASS} {name}")
        passed += 1
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        failed += 1


def run_error_test(name: str, source: str, fragment: str):
    global passed, failed
    try:
        analyze(source)
        print(f"  {FAIL} {name}: expected SemanticError, got none")
        failed += 1
    except SemanticError as e:
        if fragment.lower() in str(e).lower():
            print(f"  {PASS} {name}")
            passed += 1
        else:
            print(f"  {FAIL} {name}: wrong error — {e}")
            failed += 1
    except Exception as e:
        print(f"  {FAIL} {name}: unexpected error — {e}")
        failed += 1


# ─────────────────────────────────────────────
print("\n── 1. Variable assignment & lookup ──────────")
# ─────────────────────────────────────────────

def t_simple_assign():
    sa = analyze("x = 5")
    sym = sa.symbol_table.lookup("x")
    assert isinstance(sym, VarSymbol)
    assert sym.name == "x"
run_test("variable defined after assignment", t_simple_assign)

def t_multi_assign():
    sa = analyze("x = 1\ny = 2\nz = x + y")
    assert sa.symbol_table.lookup("x") is not None
    assert sa.symbol_table.lookup("y") is not None
    assert sa.symbol_table.lookup("z") is not None
run_test("multiple variables defined", t_multi_assign)

def t_reassign():
    sa = analyze("x = 1\nx = 2")
    sym = sa.symbol_table.lookup("x")
    assert isinstance(sym, VarSymbol)
run_test("variable re-assignment allowed", t_reassign)

def t_use_after_define():
    sa = analyze("x = 5\ny = x + 1")
    assert sa.symbol_table.lookup("y") is not None
run_test("variable used after definition", t_use_after_define)


# ─────────────────────────────────────────────
print("\n── 2. Undefined variable errors ─────────────")
# ─────────────────────────────────────────────

run_error_test("use before assign",           "print x",          "Undefined variable")
run_error_test("undefined in expression",     "y = x + 1",        "Undefined variable")
run_error_test("undefined in function call",  "sqrt(z)",          "Undefined variable")
run_error_test("undefined in if condition",   "if z > 0 then\nprint z\nend", "Undefined variable")


# ─────────────────────────────────────────────
print("\n── 3. Function definitions ──────────────────")
# ─────────────────────────────────────────────

def t_func_defined():
    sa = analyze("func square(n) => n * n")
    sym = sa.symbol_table.lookup("square")
    assert isinstance(sym, FuncSymbol)
    assert sym.params == ["n"]
run_test("function registered in symbol table", t_func_defined)

def t_func_two_params():
    sa = analyze("func add(a, b) => a + b")
    sym = sa.symbol_table.lookup("add")
    assert sym.params == ["a", "b"]
run_test("function with two params", t_func_two_params)

def t_func_no_params():
    sa = analyze("func pi() => 3.14159")
    sym = sa.symbol_table.lookup("pi")
    assert sym.params == []
run_test("function with no params", t_func_no_params)

def t_func_param_local():
    # param 'n' must NOT appear in global scope after func def
    sa = analyze("func square(n) => n * n")
    global_sym = sa.symbol_table.lookup("n")
    assert global_sym is None
run_test("function param not leaked to global scope", t_func_local_scope := t_func_param_local)

def t_recursive_func():
    src = "func f(n)\nreturn f(n)\nend"
    sa = analyze(src)
    assert sa.symbol_table.lookup("f") is not None
run_test("recursive function allowed", t_recursive_func)


# ─────────────────────────────────────────────
print("\n── 4. Function call arity checking ──────────")
# ─────────────────────────────────────────────

run_error_test("too few args",  "func sq(n) => n*n\nsq()",      "expects 1")
run_error_test("too many args", "func sq(n) => n*n\nsq(1,2)",   "expects 1")
run_error_test("sqrt too many", "x = 5\nsqrt(x, x)",            "expects 1")
run_error_test("zero-param call with arg",
               "func pi() => 3.14\npi(1)",                       "expects 0")

def t_correct_arity():
    sa = analyze("func add(a,b) => a + b\nadd(1, 2)")
    assert sa.symbol_table.lookup("add") is not None
run_test("correct arity accepted", t_correct_arity)


# ─────────────────────────────────────────────
print("\n── 5. Built-in functions ────────────────────")
# ─────────────────────────────────────────────

def t_builtins_pre_loaded():
    sa = analyze("x = 1")   # no user code needed
    for name in ["sqrt", "abs", "sin", "cos", "log", "tan"]:
        sym = sa.symbol_table.lookup(name)
        assert isinstance(sym, FuncSymbol) and sym.is_builtin, f"{name} not builtin"
run_test("all built-ins pre-loaded in global scope", t_builtins_pre_loaded)

def t_builtin_call():
    sa = analyze("x = 4\nresult = sqrt(x)")
    assert sa.symbol_table.lookup("result") is not None
run_test("built-in call accepted", t_builtin_call)

def t_nested_builtin():
    sa = analyze("x = -4\nresult = sqrt(abs(x))")
    assert sa.symbol_table.lookup("result") is not None
run_test("nested built-in calls accepted", t_nested_builtin)


# ─────────────────────────────────────────────
print("\n── 6. Scope management ──────────────────────")
# ─────────────────────────────────────────────

def t_global_depth():
    sa = analyze("x = 1")
    sym = sa.symbol_table.lookup("x")
    assert sym.scope == 0
run_test("global variable at scope depth 0", t_global_depth)

def t_func_call_undefined():
    pass  # calling undefined func
run_error_test("call undefined function", "mystery(1)", "Undefined function")

run_error_test("return outside function",
               "x = 1\nreturn x", "outside of a function")

def t_func_body_sees_global():
    src = "x = 10\nfunc f(n) => n + x\nresult = f(5)"
    sa  = analyze(src)
    assert sa.symbol_table.lookup("result") is not None
run_test("function body can read global variable", t_func_body_sees_global)


# ─────────────────────────────────────────────
print("\n── 7. If / repeat ───────────────────────────")
# ─────────────────────────────────────────────

def t_if_valid():
    src = "x = 5\nif x > 0 then\nprint x\nend"
    sa  = analyze(src)
    assert sa.symbol_table.lookup("x") is not None
run_test("valid if statement", t_if_valid)

def t_if_else_valid():
    src = "x = 5\nif x > 0 then\nprint x\nelse\nprint 0\nend"
    sa  = analyze(src)
run_test("valid if-else statement", t_if_else_valid)

def t_repeat_valid():
    src = "x = 1\nrepeat 5 times\nx = x + 1\nend"
    sa  = analyze(src)
run_test("valid repeat loop", t_repeat_valid)

run_error_test("undefined var in repeat body",
               "repeat 3 times\nx = z + 1\nend", "Undefined variable")


# ─────────────────────────────────────────────
print("\n── 8. Full programs ─────────────────────────")
# ─────────────────────────────────────────────

def t_full_program_1():
    src = """x = 16
result = sqrt(x)
print result"""
    sa = analyze(src)
    assert sa.symbol_table.lookup("x")      is not None
    assert sa.symbol_table.lookup("result") is not None
run_test("full program 1: assign + sqrt + print", t_full_program_1)

def t_full_program_2():
    src = """func square(n) => n * n
y = 3
if y > 2 then
print square(y)
end"""
    sa = analyze(src)
    assert isinstance(sa.symbol_table.lookup("square"), FuncSymbol)
    assert isinstance(sa.symbol_table.lookup("y"),      VarSymbol)
run_test("full program 2: func + if", t_full_program_2)

def t_full_program_3():
    src = """x = 1
repeat 5 times
x = x + 1
end
print x"""
    sa = analyze(src)
    assert sa.symbol_table.lookup("x") is not None
run_test("full program 3: repeat loop", t_full_program_3)


# ─────────────────────────────────────────────
print("\n── 9. Symbol table pretty print (handwritten ref) ──")
# ─────────────────────────────────────────────

src = """func square(n) => n * n
func hyp(a, b) => sqrt(a ^ 2 + b ^ 2)
x = 3
y = 4
result = hyp(x, y)
print result"""

sa = analyze(src)
sa.symbol_table.pretty_print()

if sa.warnings:
    print("Warnings:")
    for w in sa.warnings:
        print(" ", w)


# ─────────────────────────────────────────────
total = passed + failed
print(f"\n{'═'*45}")
print(f"  Results: {passed}/{total} passed", end="")
if failed == 0:
    print("  \033[92m All tests passed! \033[0m")
else:
    print(f"  \033[91m {failed} failed \033[0m")
print(f"{'═'*45}\n")