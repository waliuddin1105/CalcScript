"""
CalcScript Parser Test Suite - Phase 2
=======================================
Tests AST structure for all grammar constructs.
Run: python test_parser.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser, ParseError
from ast_nodes import *

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
passed = failed = 0


def parse(source: str) -> Program:
    tokens = Lexer(source).tokenize()
    return Parser(tokens).parse()


def run_test(name: str, fn):
    global passed, failed
    try:
        fn()
        print(f"  {PASS} {name}")
        passed += 1
    except Exception as e:
        print(f"  {FAIL} {name}: {e}")
        failed += 1


def run_error_test(name: str, source: str):
    global passed, failed
    try:
        parse(source)
        print(f"  {FAIL} {name}: expected ParseError but got none")
        failed += 1
    except ParseError as e:
        print(f"  {PASS} {name}")
        passed += 1
    except Exception as e:
        print(f"  {FAIL} {name}: wrong error type: {e}")
        failed += 1


# ─────────────────────────────────────────────
print("\n── 1. Number & Identifier expressions ──────")
# ─────────────────────────────────────────────

def t_number_literal():
    prog = parse("42")
    assert isinstance(prog.statements[0], NumberLiteral)
    assert prog.statements[0].value == 42.0
run_test("integer literal", t_number_literal)

def t_float_literal():
    prog = parse("3.14")
    assert isinstance(prog.statements[0], NumberLiteral)
    assert prog.statements[0].value == 3.14
run_test("float literal", t_float_literal)

def t_identifier():
    prog = parse("x")
    assert isinstance(prog.statements[0], IdentifierExpr)
    assert prog.statements[0].name == "x"
run_test("identifier expr", t_identifier)


# ─────────────────────────────────────────────
print("\n── 2. Assignment statements ─────────────────")
# ─────────────────────────────────────────────

def t_assign_number():
    prog = parse("x = 5")
    s = prog.statements[0]
    assert isinstance(s, AssignStmt)
    assert s.name == "x"
    assert isinstance(s.value, NumberLiteral)
    assert s.value.value == 5.0
run_test("assign number", t_assign_number)

def t_assign_expr():
    prog = parse("y = x + 1")
    s = prog.statements[0]
    assert isinstance(s, AssignStmt)
    assert isinstance(s.value, BinaryExpr)
    assert s.value.op == "+"
run_test("assign expression", t_assign_expr)

def t_assign_multiple():
    prog = parse("x = 1\ny = 2")
    assert len(prog.statements) == 2
    assert prog.statements[0].name == "x"
    assert prog.statements[1].name == "y"
run_test("multiple assignments", t_assign_multiple)


# ─────────────────────────────────────────────
print("\n── 3. Arithmetic expressions ────────────────")
# ─────────────────────────────────────────────

def t_addition():
    prog = parse("1 + 2")
    e = prog.statements[0]
    assert isinstance(e, BinaryExpr) and e.op == "+"
    assert e.left.value == 1.0 and e.right.value == 2.0
run_test("addition", t_addition)

def t_precedence_mul_over_add():
    prog = parse("1 + 2 * 3")
    e = prog.statements[0]
    # Should be: +(1, *(2, 3))
    assert isinstance(e, BinaryExpr) and e.op == "+"
    assert isinstance(e.right, BinaryExpr) and e.right.op == "*"
run_test("* before + precedence", t_precedence_mul_over_add)

def t_power_right_assoc():
    prog = parse("2 ^ 3 ^ 2")
    e = prog.statements[0]
    # Should be: ^(2, ^(3, 2))
    assert isinstance(e, BinaryExpr) and e.op == "^"
    assert isinstance(e.right, BinaryExpr) and e.right.op == "^"
run_test("^ right-associative", t_power_right_assoc)

def t_unary_minus():
    prog = parse("-x")
    e = prog.statements[0]
    assert isinstance(e, UnaryExpr) and e.op == "-"
    assert isinstance(e.right, IdentifierExpr)
run_test("unary minus", t_unary_minus)

def t_grouped_expr():
    prog = parse("(1 + 2) * 3")
    e = prog.statements[0]
    assert isinstance(e, BinaryExpr) and e.op == "*"
    assert isinstance(e.left, BinaryExpr) and e.left.op == "+"
run_test("parenthesised grouping", t_grouped_expr)


# ─────────────────────────────────────────────
print("\n── 4. Comparison expressions ────────────────")
# ─────────────────────────────────────────────

for op in ["==", "!=", "<", ">", "<=", ">="]:
    def _make(o):
        def t():
            prog = parse(f"x {o} 1")
            e = prog.statements[0]
            assert isinstance(e, BinaryExpr) and e.op == o
        return t
    run_test(f"comparison {op}", _make(op))


# ─────────────────────────────────────────────
print("\n── 5. Print statement ───────────────────────")
# ─────────────────────────────────────────────

def t_print():
    prog = parse("print x")
    s = prog.statements[0]
    assert isinstance(s, PrintStmt)
    assert isinstance(s.value, IdentifierExpr)
run_test("print identifier", t_print)

def t_print_expr():
    prog = parse("print x + 1")
    s = prog.statements[0]
    assert isinstance(s, PrintStmt)
    assert isinstance(s.value, BinaryExpr)
run_test("print expression", t_print_expr)


# ─────────────────────────────────────────────
print("\n── 6. Function definitions ──────────────────")
# ─────────────────────────────────────────────

def t_func_single_line():
    prog = parse("func square(n) => n * n")
    s = prog.statements[0]
    assert isinstance(s, FuncDefStmt)
    assert s.name == "square"
    assert s.params == ["n"]
    assert isinstance(s.body, BinaryExpr)
run_test("single-line func def", t_func_single_line)

def t_func_two_params():
    prog = parse("func add(a, b) => a + b")
    s = prog.statements[0]
    assert s.params == ["a", "b"]
run_test("func with two params", t_func_two_params)

def t_func_no_params():
    prog = parse("func pi() => 3.14159")
    s = prog.statements[0]
    assert s.params == []
    assert isinstance(s.body, NumberLiteral)
run_test("func with no params", t_func_no_params)

def t_func_multiline():
    src = "func double(n)\nx = n * 2\nreturn x\nend"
    prog = parse(src)
    s = prog.statements[0]
    assert isinstance(s, FuncDefStmt)
    assert isinstance(s.body, Block)
    assert len(s.body.statements) == 2
run_test("multi-line func def", t_func_multiline)


# ─────────────────────────────────────────────
print("\n── 7. Function calls ────────────────────────")
# ─────────────────────────────────────────────

def t_user_call():
    prog = parse("square(4)")
    e = prog.statements[0]
    assert isinstance(e, FuncCallExpr)
    assert e.name == "square"
    assert len(e.args) == 1
run_test("user-defined function call", t_user_call)

def t_builtin_sqrt():
    prog = parse("sqrt(16)")
    e = prog.statements[0]
    assert isinstance(e, FuncCallExpr) and e.name == "sqrt"
run_test("built-in sqrt call", t_builtin_sqrt)

def t_builtin_in_expr():
    prog = parse("x = sqrt(y) + 1")
    s = prog.statements[0]
    assert isinstance(s.value, BinaryExpr)
    assert isinstance(s.value.left, FuncCallExpr)
run_test("built-in in expression", t_builtin_in_expr)

def t_nested_call():
    prog = parse("sqrt(abs(-4))")
    e = prog.statements[0]
    assert isinstance(e, FuncCallExpr) and e.name == "sqrt"
    assert isinstance(e.args[0], FuncCallExpr) and e.args[0].name == "abs"
run_test("nested function calls", t_nested_call)


# ─────────────────────────────────────────────
print("\n── 8. If statement ──────────────────────────")
# ─────────────────────────────────────────────

def t_if_simple():
    src = "if x > 0 then\nprint x\nend"
    prog = parse(src)
    s = prog.statements[0]
    assert isinstance(s, IfStmt)
    assert isinstance(s.condition, BinaryExpr) and s.condition.op == ">"
    assert isinstance(s.then_body, Block)
    assert s.else_body is None
run_test("simple if", t_if_simple)

def t_if_else():
    src = "if x > 0 then\nprint x\nelse\nprint 0\nend"
    prog = parse(src)
    s = prog.statements[0]
    assert isinstance(s, IfStmt)
    assert s.else_body is not None
    assert len(s.else_body.statements) == 1
run_test("if-else", t_if_else)


# ─────────────────────────────────────────────
print("\n── 9. Repeat statement ──────────────────────")
# ─────────────────────────────────────────────

def t_repeat():
    src = "repeat 3 times\nx = x + 1\nend"
    prog = parse(src)
    s = prog.statements[0]
    assert isinstance(s, RepeatStmt)
    assert isinstance(s.count, NumberLiteral) and s.count.value == 3.0
    assert isinstance(s.body, Block)
    assert len(s.body.statements) == 1
run_test("repeat loop", t_repeat)

def t_repeat_expr_count():
    src = "repeat n times\nx = x * 2\nend"
    prog = parse(src)
    s = prog.statements[0]
    assert isinstance(s.count, IdentifierExpr)
run_test("repeat with variable count", t_repeat_expr_count)


# ─────────────────────────────────────────────
print("\n── 10. Return statement ─────────────────────")
# ─────────────────────────────────────────────

def t_return():
    src = "func f(x)\nreturn x * 2\nend"
    prog = parse(src)
    fn = prog.statements[0]
    ret = fn.body.statements[0]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, BinaryExpr)
run_test("return in function", t_return)


# ─────────────────────────────────────────────
print("\n── 11. Full programs ────────────────────────")
# ─────────────────────────────────────────────

def t_full_program_1():
    src = """x = 16
result = sqrt(x)
print result"""
    prog = parse(src)
    assert len(prog.statements) == 3
    assert isinstance(prog.statements[0], AssignStmt)
    assert isinstance(prog.statements[1], AssignStmt)
    assert isinstance(prog.statements[2], PrintStmt)
run_test("full program: assign+builtin+print", t_full_program_1)

def t_full_program_2():
    src = """func square(n) => n * n
y = 3
if y > 2 then
print square(y)
end"""
    prog = parse(src)
    assert len(prog.statements) == 3
    assert isinstance(prog.statements[0], FuncDefStmt)
    assert isinstance(prog.statements[1], AssignStmt)
    assert isinstance(prog.statements[2], IfStmt)
run_test("full program: func+assign+if", t_full_program_2)

def t_full_program_3():
    src = """x = 1
repeat 5 times
x = x * 2
end
print x"""
    prog = parse(src)
    assert len(prog.statements) == 3
    assert isinstance(prog.statements[1], RepeatStmt)
run_test("full program: repeat loop", t_full_program_3)


# ─────────────────────────────────────────────
print("\n── 12. Line & column tracking ───────────────")
# ─────────────────────────────────────────────

def t_location():
    prog = parse("x = 5\nprint x")
    assign = prog.statements[0]
    pr     = prog.statements[1]
    assert assign.line == 1 and assign.col == 1
    assert pr.line == 2 and pr.col == 1
run_test("statement line/col tracking", t_location)


# ─────────────────────────────────────────────
print("\n── 13. Error handling ───────────────────────")
# ─────────────────────────────────────────────

run_error_test("missing ) in call",   "sqrt(16")
run_error_test("missing then in if",  "if x > 0\nprint x\nend")
run_error_test("missing end for if",  "if x > 0 then\nprint x")
run_error_test("missing times",       "repeat 3\nx = 1\nend")
run_error_test("func missing paren",  "func f x) => x")


# ─────────────────────────────────────────────
print("\n── 14. Parse tree output (handwritten ref) ──")
# ─────────────────────────────────────────────

from parser import ASTPrinter
printer = ASTPrinter()

print("\n  Parse Tree 1: result = sqrt(x + 1)")
prog = parse("result = sqrt(x + 1)")
printer.print(prog)

print("\n  Parse Tree 2: if y > 2 then\\n  print square(y)\\nend")
prog2 = parse("if y > 2 then\nprint square(y)\nend")
printer.print(prog2)


# ─────────────────────────────────────────────
total = passed + failed
print(f"\n{'═'*45}")
print(f"  Results: {passed}/{total} passed", end="")
if failed == 0:
    print("  \033[92m All tests passed! \033[0m")
else:
    print(f"  \033[91m {failed} failed \033[0m")
print(f"{'═'*45}\n")