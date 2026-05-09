#!/usr/bin/env python3
"""
CalcScript Compiler - CLI Entry Point
======================================
Usage:
    python compiler.py input.calc             # compile and run
    python compiler.py input.calc --debug     # show all intermediate representations
    python compiler.py --interactive          # REPL mode
"""

import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer, LexerError, TokenType
from parser import Parser, ParseError, ASTPrinter
from semantic import SemanticAnalyzer, SemanticError
from ir_gen import IRGenerator
from optimizer import Optimizer
from vm import VM, RuntimeError_


def run_repl(debug=False):
    print("CalcScript REPL (All Phases)")
    print("Type CalcScript source. Enter blank line to run. Ctrl-C to exit.\n")
    while True:
        try:
            lines = []
            while True:
                prompt = ">>> " if not lines else "... "
                line = input(prompt)
                if line == "" and lines:
                    break
                lines.append(line)
            source = "\n".join(lines)
            if not source.strip():
                continue

            tokens    = Lexer(source, "<repl>").tokenize()
            tree      = Parser(tokens).parse()
            sa        = SemanticAnalyzer()
            sa.analyze(tree)
            instrs    = IRGenerator().generate(tree)
            optimized = Optimizer().optimize(instrs)

            if debug:
                Lexer(source, "<repl>").pretty_print(tokens)
                ASTPrinter().print(tree)
                sa.symbol_table.pretty_print()
                IRGenerator().pretty_print(instrs)

            VM(debug=debug).run(optimized)

        except (LexerError, ParseError, SemanticError, RuntimeError_) as e:
            print(f"\n{e}\n")
        except KeyboardInterrupt:
            print("\nBye!"); break
        except EOFError:
            print("\nBye!"); break


def compile_file(path, debug=False):
    if not os.path.isfile(path):
        print(f"[Error] File not found: {path}"); sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        source = f.read()

    print(f"\nCompiling: {path}")
    print("─" * 40)

    # Phase 1
    lexer = Lexer(source, filename=path)
    try:
        tokens = lexer.tokenize()
    except LexerError as e:
        print(e); sys.exit(1)
    non_eof = [t for t in tokens if t.type != TokenType.EOF]
    print(f"  Phase 1 — Lexical analysis  : {len(non_eof)} tokens  [OK]")
    if debug:
        print("\n── Token Stream ─────────────────────────────")
        lexer.pretty_print(tokens)

    # Phase 2
    try:
        tree = Parser(tokens).parse()
    except ParseError as e:
        print(e); sys.exit(1)
    print(f"  Phase 2 — Syntax analysis   : AST built ({len(tree.statements)} top-level statements)  [OK]")
    if debug:
        print("\n── Abstract Syntax Tree ─────────────────────")
        ASTPrinter().print(tree)

    # Phase 3
    sa = SemanticAnalyzer()
    try:
        sa.analyze(tree)
    except SemanticError as e:
        print(e); sys.exit(1)
    for w in sa.warnings:
        print(f"  {w}")
    sym_count = sum(1 for s in list(sa.symbol_table._scopes[0].values())
                    if not getattr(s, 'is_builtin', False))
    print(f"  Phase 3 — Semantic analysis : {sym_count} user symbol(s) defined  [OK]")
    if debug:
        sa.symbol_table.pretty_print()

    # Phase 4
    gen    = IRGenerator()
    instrs = gen.generate(tree)
    print(f"  Phase 4 — IR generation     : {len(instrs)} TAC instructions  [OK]")
    if debug:
        gen.pretty_print(instrs)

    # Phase 5
    opt       = Optimizer()
    optimized = opt.optimize(instrs)
    removed   = len(instrs) - len(optimized)
    print(f"  Phase 5 — Optimization      : {removed} instruction(s) removed  [OK]")
    if debug:
        opt.pretty_print_diff(instrs, optimized)

    # Phase 6
    print(f"  Phase 6 — Execution\n")
    print("── Output ───────────────────────────────────")
    try:
        VM(debug=debug).run(optimized)
    except RuntimeError_ as e:
        print(e); sys.exit(1)
    print()


def main():
    parser = argparse.ArgumentParser(prog="compiler", description="CalcScript Compiler")
    parser.add_argument("input", nargs="?", help="Source file (.calc)")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--debug", action="store_true", help="Show all intermediate representations")
    parser.add_argument("--interactive", action="store_true", help="Launch REPL mode")
    args = parser.parse_args()

    if args.interactive:
        run_repl(debug=args.debug)
    elif args.input:
        compile_file(args.input, debug=args.debug)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()