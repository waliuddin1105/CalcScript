# CalcScript

A compiler for a small domain-specific language inspired by classic programmable calculators. CalcScript lets you write programs that do arithmetic, define functions, use conditionals, and run loops — then compiles and runs them through a full pipeline ending in a lightweight virtual machine.

---

## How it works

Source code goes through six phases:

1. **Lexer** — breaks the source into tokens
2. **Parser** — builds an abstract syntax tree
3. **Semantic Analyzer** — checks for errors like undefined variables and wrong argument counts
4. **IR Generator** — converts the AST into Three-Address Code (TAC)
5. **Optimizer** — folds constants and removes dead code
6. **VM** — executes the optimized instructions and prints results

---

## Requirements

- Python 3.10 or higher
- No external dependencies — standard library only

---

## Setup

Clone the repo and you're ready to go. No installation needed.

```
git clone https://github.com/your-username/calcscript.git
cd calcscript
```

---

## Usage

### Run a .calc file

```
python compiler.py samples/sample1.calc
```

### Run with debug output

Shows the token stream, AST, symbol table, TAC, and optimization diff.

```
python compiler.py samples/sample1.calc --debug
```

### Interactive REPL

Type CalcScript code directly. Press Enter on a blank line to run.

```
python compiler.py --interactive
```

---

## Language basics

```
// Variables
x = 16
y = 3

// Built-in math functions
result = sqrt(x)
print result          // >> 4

// User-defined functions
func square(n) => n * n

// Conditionals
if y > 2 then
    print square(y)   // >> 9
end

// Loops
repeat 4 times
    x = x + 1
end
print x               // >> 20
```

Built-in functions: `sqrt`, `abs`, `sin`, `cos`, `log`, `tan`

---

## Running the tests

Each phase has its own test file.

```
python test_lexer.py       // Phase 1 - tokenization
python test_parser.py      // Phase 2 - parse trees
python test_semantic.py    // Phase 3 - symbol table and scope checks
python test_ir.py          // Phase 4 - TAC generation
python test_optimizer.py   // Phase 5 - constant folding and dead code elimination
python test_vm.py          // Phase 6 - execution and output
```

---

## Sample files

The `samples/` folder contains `.calc` programs that demonstrate different features of the language. You can run any of them with:

```
python compiler.py samples/sample1.calc
```

Add `--debug` to see all intermediate representations for that file.
