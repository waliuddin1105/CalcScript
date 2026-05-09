"""
CalcScript Symbol Table - Phase 3: Semantic Analysis
=====================================================
Implements a scoped symbol table supporting:
  - Global scope for variables and functions
  - Local scope per function call (parameters + locals)
  - Built-in function registry

Symbol Table Structure:
─────────────────────────────────────────────────
Each scope is a dict: name -> Symbol
Scopes are stacked; lookup walks inward -> outward.

Scope stack during  func square(n):
  [0] global:  { square: FuncSymbol }
  [1] local:   { n: VarSymbol }        <- current
─────────────────────────────────────────────────
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field


# ─────────────────────────────────────────────
#  Symbol kinds
# ─────────────────────────────────────────────

@dataclass
class VarSymbol:
    name:  str
    type:  str = "number"      # CalcScript is numeric-only
    scope: int = 0             # scope depth where defined

    def __repr__(self):
        return f"Var({self.name!r}, type={self.type}, scope={self.scope})"


@dataclass
class FuncSymbol:
    name:       str
    params:     List[str]
    scope:      int = 0
    is_builtin: bool = False

    def __repr__(self):
        return f"Func({self.name!r}, params={self.params}, builtin={self.is_builtin})"


# ─────────────────────────────────────────────
#  Built-in registry
# ─────────────────────────────────────────────

BUILTIN_FUNCTIONS: Dict[str, FuncSymbol] = {
    "sqrt": FuncSymbol("sqrt", ["x"],    is_builtin=True),
    "abs":  FuncSymbol("abs",  ["x"],    is_builtin=True),
    "sin":  FuncSymbol("sin",  ["x"],    is_builtin=True),
    "cos":  FuncSymbol("cos",  ["x"],    is_builtin=True),
    "log":  FuncSymbol("log",  ["x"],    is_builtin=True),
    "tan":  FuncSymbol("tan",  ["x"],    is_builtin=True),
}


# ─────────────────────────────────────────────
#  Scoped Symbol Table
# ─────────────────────────────────────────────

class SymbolTable:
    """
    A stack of scopes.
    enter_scope() pushes a new dict.
    exit_scope()  pops it.
    define()      adds to current (innermost) scope.
    lookup()      walks from inner -> outer.
    """

    def __init__(self):
        # Stack of dicts; index 0 = global
        self._scopes: List[Dict[str, Any]] = [{}]
        # Pre-load built-ins into global scope
        for name, sym in BUILTIN_FUNCTIONS.items():
            self._scopes[0][name] = sym

    # ── Scope management ────────────────────────

    @property
    def depth(self) -> int:
        return len(self._scopes) - 1

    def enter_scope(self) -> None:
        self._scopes.append({})

    def exit_scope(self) -> Dict[str, Any]:
        """Pop and return the innermost scope (useful for printing)."""
        if len(self._scopes) == 1:
            raise RuntimeError("Cannot exit global scope")
        return self._scopes.pop()

    # ── Symbol operations ────────────────────────

    def define(self, symbol) -> None:
        """Add symbol to current (innermost) scope."""
        symbol.scope = self.depth
        self._scopes[-1][symbol.name] = symbol

    def lookup(self, name: str) -> Optional[Any]:
        """Walk from innermost to outermost scope."""
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_current_scope(self, name: str) -> Optional[Any]:
        """Look only in the current (innermost) scope."""
        return self._scopes[-1].get(name)

    def is_defined(self, name: str) -> bool:
        return self.lookup(name) is not None

    # ── Debug / pretty print ─────────────────────

    def pretty_print(self) -> None:
        """Print the full symbol table — used for --debug and handwritten ref."""
        print("\n── Symbol Table ─────────────────────────────")
        for depth, scope in enumerate(self._scopes):
            label = "global" if depth == 0 else f"local (depth {depth})"
            print(f"\n  Scope {depth} [{label}]:")
            print(f"  {'Name':<16} {'Kind':<10} {'Type/Params':<20} {'Depth'}")
            print(f"  {'-'*56}")
            if not scope:
                print("  (empty)")
            for name, sym in scope.items():
                if isinstance(sym, VarSymbol):
                    print(f"  {name:<16} {'var':<10} {sym.type:<20} {sym.scope}")
                elif isinstance(sym, FuncSymbol):
                    params = f"({', '.join(sym.params)})"
                    kind   = "builtin" if sym.is_builtin else "func"
                    print(f"  {name:<16} {kind:<10} {params:<20} {sym.scope}")
        print()