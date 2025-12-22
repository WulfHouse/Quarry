# Status Matrix

Compact reference table: area → supported? → evidence pointer.

## Language Features

| Area | Supported? | Evidence |
|------|------------|----------|
| Functions (basic) | ✅ | `test_parse_simple_function()`, `forge/examples/basic/hello.pyrite` |
| Functions (with params) | ✅ | `test_parse_function_with_params()` |
| Functions (generics) | ✅ | `forge/examples/basic/generics.pyrite` |
| Variables (`let`) | ✅ | `test_parse_let_statement()`, `forge/examples/basic/simple.pyrite` |
| Variables (`var`) | ✅ | `test_parse_var_statement()` |
| Structs | ✅ | `test_parse_struct()`, `forge/examples/basic/structs.pyrite` |
| Enums | ✅ | `test_parse_enum()`, `forge/examples/basic/enums.pyrite` |
| Traits | ✅ | Parser: `parse_trait()` |
| Impl blocks | ✅ | Parser: `parse_impl()` |
| If statements | ✅ | `test_parse_if_statement()` |
| If expressions | ✅ | `test_parse_if_expression()` |
| While loops | ✅ | `test_parse_while_loop()`, `tests/acceptance/test9_loops.pyrite` |
| For loops | ✅ | `test_parse_for_loop()`, `tests/acceptance/test9_loops.pyrite` |
| Match statements | ✅ | `test_parse_match_statement()`, `tests/acceptance/test5_match.pyrite` |
| Defer | ✅ | `test_parse_defer_statement()`, `tests/acceptance/test_defer.pyrite` |
| With statements | ✅ | `test_parse_with_statement()` |
| Unsafe blocks | ✅ | `test_parse_unsafe_block()` |
| Try expressions | ✅ | `test_parse_try_expression()` |
| Ownership | ✅ | `tests/acceptance/test2_ownership_error.pyrite` |
| Borrowing | ✅ | `forge/examples/basic/borrowing.pyrite`, `tests/acceptance/test3_borrowing.pyrite` |
| Closures (parameter) | ✅ | `test_parse_parameter_closure()`, `forge/examples/basic/closures.pyrite` |
| Closures (runtime) | ✅ | `test_parse_runtime_closure()`, `forge/examples/basic/closures.pyrite` |
| Generics | ✅ | `forge/examples/basic/generics.pyrite`, `tests/acceptance/test_monomorphization.pyrite` |
| Tuple literals | ❌ | `LIMITATIONS.md` |
| Tuple destructuring | ❌ | `LIMITATIONS.md` |
| Iterator protocol | ⚠️ | `LIMITATIONS.md`: Partial |

## Compiler Features

| Area | Supported? | Evidence |
|------|------------|----------|
| Lexing | ✅ | `forge/src/frontend/lexer.py`, tests |
| Parsing | ✅ | `forge/src/frontend/parser.py`, tests |
| Type checking | ✅ | `forge/src/middle/type_checker.py`, tests |
| Ownership analysis | ✅ | `forge/src/middle/ownership.py`, tests |
| Borrow checking | ✅ | `forge/src/middle/borrow_checker.py`, tests |
| LLVM IR generation | ✅ | `forge/src/backend/codegen.py`, examples compile |
| Linking | ✅ | `forge/src/backend/linker.py` |
| Monomorphization | ✅ | `forge/src/backend/monomorphization.py`, `tests/acceptance/test_monomorphization.pyrite` |
| Closure inlining | ⚠️ | `LIMITATIONS.md`: Partial |
| With desugaring | ✅ | `forge/src/passes/with_desugar_pass.py` |
| Incremental compilation | ✅ | `forge/src/utils/incremental.py` |
| Error explanations | ✅ | `forge/src/compiler.py:413-421` |

## Quarry Commands

| Command | Supported? | Evidence |
|---------|-------------|----------|
| `new` | ✅ | `forge/quarry/main.py:cmd_new()`, registered |
| `build` | ✅ | `forge/quarry/main.py:cmd_build()`, registered |
| `run` | ✅ | `forge/quarry/main.py:cmd_run()`, registered |
| `clean` | ✅ | `forge/quarry/main.py:cmd_clean()`, registered |
| `test` | ✅ | `forge/quarry/main.py:cmd_test()`, registered |
| `fmt` | ✅ | `forge/quarry/main.py:cmd_fmt()`, registered |
| `fix` | ✅ | `forge/quarry/main.py:cmd_fix()`, registered |
| `cost` | ✅ | `forge/quarry/main.py:cmd_cost()`, registered |
| `bloat` | ✅ | `forge/quarry/main.py:cmd_bloat()`, registered |
| `perf` | ✅ | `forge/quarry/main.py:cmd_perf()`, registered |
| `resolve` | ✅ | `forge/quarry/main.py:cmd_resolve()`, registered |
| `update` | ✅ | `forge/quarry/main.py:cmd_update()`, registered |
| `install` | ✅ | `forge/quarry/main.py:cmd_install()`, registered |
| `search` | ✅ | `forge/quarry/main.py:cmd_search()`, registered |
| `info` | ✅ | `forge/quarry/main.py:cmd_info()`, registered |
| `publish` | ✅ | `forge/quarry/main.py:cmd_publish()`, registered |

## Experimental

| Feature | Status | Evidence |
|---------|--------|----------|

## Legend

- ✅ = Fully supported and proven
- ⚠️ = Partially supported (see `LIMITATIONS.md`)
- ❌ = Not supported (see `LIMITATIONS.md`)

## Quick Reference

- **Proven syntax**: See `docs/proven/language_syntax.md`
- **Proven commands**: See `docs/proven/cli_commands.md`
- **Detailed features**: See `docs/proven/features.md`
- **Known limitations**: See `LIMITATIONS.md`
