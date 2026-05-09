"""
CalcScript Lexer Test Suite
============================
Tests all token categories with expected outputs.
Run: python test_lexer.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer, TokenType, LexerError

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

passed = 0
failed = 0


def run_test(name: str, source: str, expected: list[tuple]):
    """
    expected: list of (TokenType, value) tuples (EOF excluded from check).
    """
    global passed, failed
    lexer  = Lexer(source, filename="<test>")
    tokens = lexer.tokenize()
    # strip EOF for comparison
    actual = [(t.type, t.value) for t in tokens if t.type != TokenType.EOF]

    if actual == list(expected):
        print(f"  {PASS} {name}")
        passed += 1
    else:
        print(f"  {FAIL} {name}")
        print(f"       Expected: {expected}")
        print(f"       Got:      {actual}")
        failed += 1


def run_error_test(name: str, source: str, expected_msg_fragment: str):
    global passed, failed
    try:
        Lexer(source).tokenize()
        print(f"  {FAIL} {name}  (expected LexerError but got none)")
        failed += 1
    except LexerError as e:
        if expected_msg_fragment.lower() in str(e).lower():
            print(f"  {PASS} {name}")
            passed += 1
        else:
            print(f"  {FAIL} {name}  (wrong error: {e})")
            failed += 1


# ─────────────────────────────────────────────
#  Test Groups
# ─────────────────────────────────────────────

print("\n── 1. Number Literals ───────────────────────")
run_test("integer",         "42",      [(TokenType.NUMBER, "42")])
run_test("float",           "3.14",    [(TokenType.NUMBER, "3.14")])
run_test("leading dot",     ".5",      [(TokenType.NUMBER, ".5")])
run_test("trailing dot",    "7.",      [(TokenType.NUMBER, "7.")])
run_test("negative (expr)", "-3",      [(TokenType.MINUS, "-"), (TokenType.NUMBER, "3")])

print("\n── 2. Identifiers ───────────────────────────")
run_test("simple id",      "x",        [(TokenType.IDENTIFIER, "x")])
run_test("multi-char id",  "myVar",    [(TokenType.IDENTIFIER, "myVar")])
run_test("underscore id",  "_tmp",     [(TokenType.IDENTIFIER, "_tmp")])
run_test("id with digits", "val1",     [(TokenType.IDENTIFIER, "val1")])

print("\n── 3. Keywords ──────────────────────────────")
run_test("func",   "func",   [(TokenType.FUNC,   "func")])
run_test("if",     "if",     [(TokenType.IF,     "if")])
run_test("then",   "then",   [(TokenType.THEN,   "then")])
run_test("else",   "else",   [(TokenType.ELSE,   "else")])
run_test("end",    "end",    [(TokenType.END,    "end")])
run_test("repeat", "repeat", [(TokenType.REPEAT, "repeat")])
run_test("times",  "times",  [(TokenType.TIMES,  "times")])
run_test("print",  "print",  [(TokenType.PRINT,  "print")])
run_test("return", "return", [(TokenType.RETURN, "return")])

print("\n── 4. Built-in Functions ────────────────────")
run_test("sqrt", "sqrt", [(TokenType.SQRT, "sqrt")])
run_test("abs",  "abs",  [(TokenType.ABS,  "abs")])
run_test("sin",  "sin",  [(TokenType.SIN,  "sin")])
run_test("cos",  "cos",  [(TokenType.COS,  "cos")])
run_test("log",  "log",  [(TokenType.LOG,  "log")])
run_test("tan",  "tan",  [(TokenType.TAN,  "tan")])

print("\n── 5. Arithmetic Operators ──────────────────")
run_test("plus",   "+", [(TokenType.PLUS,  "+")])
run_test("minus",  "-", [(TokenType.MINUS, "-")])
run_test("star",   "*", [(TokenType.STAR,  "*")])
run_test("slash",  "/", [(TokenType.SLASH, "/")])
run_test("caret",  "^", [(TokenType.CARET, "^")])

print("\n── 6. Comparison Operators ──────────────────")
run_test("==",  "==", [(TokenType.EQ,  "==")])
run_test("!=",  "!=", [(TokenType.NEQ, "!=")])
run_test("<",   "<",  [(TokenType.LT,  "<")])
run_test(">",   ">",  [(TokenType.GT,  ">")])
run_test("<=",  "<=", [(TokenType.LTE, "<=")])
run_test(">=",  ">=", [(TokenType.GTE, ">=")])

print("\n── 7. Assignment & Delimiters ───────────────")
run_test("assign", "=",  [(TokenType.ASSIGN, "=")])
run_test("lparen", "(",  [(TokenType.LPAREN, "(")])
run_test("rparen", ")",  [(TokenType.RPAREN, ")")])
run_test("comma",  ",",  [(TokenType.COMMA,  ",")])
run_test("arrow",  "=>", [(TokenType.ARROW,  "=>")])

print("\n── 8. Comments ──────────────────────────────")
run_test("comment stripped",
    "x = 5 // set x",
    [(TokenType.IDENTIFIER, "x"),
     (TokenType.ASSIGN,     "="),
     (TokenType.NUMBER,     "5")])

run_test("comment only line",
    "// nothing here\nx = 1",
    [(TokenType.IDENTIFIER, "x"),
     (TokenType.ASSIGN,     "="),
     (TokenType.NUMBER,     "1")])

print("\n── 9. Newlines (statement separators) ───────")
run_test("two statements separated by newline",
    "x = 1\ny = 2",
    [(TokenType.IDENTIFIER, "x"),
     (TokenType.ASSIGN,     "="),
     (TokenType.NUMBER,     "1"),
     (TokenType.NEWLINE,    "\\n"),
     (TokenType.IDENTIFIER, "y"),
     (TokenType.ASSIGN,     "="),
     (TokenType.NUMBER,     "2")])

run_test("multiple newlines collapsed to one",
    "x = 1\n\n\ny = 2",
    [(TokenType.IDENTIFIER, "x"),
     (TokenType.ASSIGN,     "="),
     (TokenType.NUMBER,     "1"),
     (TokenType.NEWLINE,    "\\n"),
     (TokenType.IDENTIFIER, "y"),
     (TokenType.ASSIGN,     "="),
     (TokenType.NUMBER,     "2")])

print("\n── 10. Full Program Snippets ────────────────")
run_test("assignment expression",
    "result = sqrt(16)",
    [(TokenType.IDENTIFIER, "result"),
     (TokenType.ASSIGN,     "="),
     (TokenType.SQRT,       "sqrt"),
     (TokenType.LPAREN,     "("),
     (TokenType.NUMBER,     "16"),
     (TokenType.RPAREN,     ")")])

run_test("function definition",
    "func square(n) => n * n",
    [(TokenType.FUNC,       "func"),
     (TokenType.IDENTIFIER, "square"),
     (TokenType.LPAREN,     "("),
     (TokenType.IDENTIFIER, "n"),
     (TokenType.RPAREN,     ")"),
     (TokenType.ARROW,      "=>"),
     (TokenType.IDENTIFIER, "n"),
     (TokenType.STAR,       "*"),
     (TokenType.IDENTIFIER, "n")])

run_test("if conditional",
    "if y > 2 then print y end",
    [(TokenType.IF,         "if"),
     (TokenType.IDENTIFIER, "y"),
     (TokenType.GT,         ">"),
     (TokenType.NUMBER,     "2"),
     (TokenType.THEN,       "then"),
     (TokenType.PRINT,      "print"),
     (TokenType.IDENTIFIER, "y"),
     (TokenType.END,        "end")])

run_test("repeat loop",
    "repeat 3 times x = x + 1 end",
    [(TokenType.REPEAT,     "repeat"),
     (TokenType.NUMBER,     "3"),
     (TokenType.TIMES,      "times"),
     (TokenType.IDENTIFIER, "x"),
     (TokenType.ASSIGN,     "="),
     (TokenType.IDENTIFIER, "x"),
     (TokenType.PLUS,       "+"),
     (TokenType.NUMBER,     "1"),
     (TokenType.END,        "end")])

print("\n── 11. Line & Column Tracking ───────────────")
def check_positions(name, source, checks):
    global passed, failed
    tokens = Lexer(source).tokenize()
    ok = True
    for tok_type, val, exp_line, exp_col in checks:
        match = next((t for t in tokens if t.type == tok_type and t.value == val), None)
        if not match or match.line != exp_line or match.column != exp_col:
            ok = False
            actual = f"({match.line}:{match.column})" if match else "not found"
            print(f"  {FAIL} {name}: {tok_type.name} '{val}' expected {exp_line}:{exp_col}, got {actual}")
    if ok:
        print(f"  {PASS} {name}")
        passed += 1
    else:
        failed += 1

check_positions(
    "positions in multi-line source",
    "x = 5\ny = 10",
    [
        (TokenType.IDENTIFIER, "x",  1, 1),
        (TokenType.NUMBER,     "5",  1, 5),
        (TokenType.IDENTIFIER, "y",  2, 1),
        (TokenType.NUMBER,     "10", 2, 5),
    ]
)

print("\n── 12. Error Handling ───────────────────────")
run_error_test("illegal character @", "x = @5",  "Unexpected character")
run_error_test("illegal character $", "val$ = 3", "Unexpected character")
run_error_test("illegal character #", "# comment", "Unexpected character")


# ─────────────────────────────────────────────
#  Summary
# ─────────────────────────────────────────────
total = passed + failed
print(f"\n{'═'*45}")
print(f"  Results: {passed}/{total} passed", end="")
if failed == 0:
    print("  \033[92m All tests passed! \033[0m")
else:
    print(f"  \033[91m {failed} failed \033[0m")
print(f"{'═'*45}\n")