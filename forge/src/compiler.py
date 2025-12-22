"""Forge - Main compiler driver for Pyrite

Forge is the Pyrite compiler, part of the Quarry development suite.
"""

import sys
from typing import Optional
from llvmlite import binding

from .frontend import lex, LexerError, parse, ParseError, Span
from .middle import type_check, TypeCheckError, analyze_ownership, check_borrows, resolve_modules, ModuleError
from .backend import generate_llvm, compile_to_executable, LLVMCodeGen, link_with_stdlib, link_llvm_ir, monomorphize_program
from .passes import ClosureInlinePass, WithDesugarPass
from .utils import ErrorFormatter
from pathlib import Path


class CompilationError(Exception):
    """Compilation error"""
    pass


def compile_file(source_path: str, output_path: Optional[str] = None, emit_llvm: bool = False, deterministic: bool = False, visual: bool = False, warn_cost: bool = False, incremental: bool = True) -> bool:
    """Compile a Pyrite source file
    
    Args:
        source_path: Path to source file
        output_path: Optional output file path
        emit_llvm: Emit LLVM IR instead of object file
        deterministic: Enable deterministic builds
        visual: Enable ownership timeline visualizations
        warn_cost: Enable cost transparency warnings
        incremental: Enable incremental compilation (default: True)
    
    Returns:
        True if compilation succeeded, False otherwise
    """
    
    # Read source
    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        return False
    
    return compile_source(source, source_path, output_path, emit_llvm, deterministic, visual, warn_cost, incremental)


def compile_source(source: str, filename: str = "<input>", output_path: Optional[str] = None, emit_llvm: bool = False, deterministic: bool = False, visual: bool = False, warn_cost: bool = False, incremental: bool = True) -> bool:
    """Compile Pyrite source code
    
    Args:
        source: Source code to compile
        filename: Source file name (used for error messages and module resolution)
        output_path: Output file path (if None, uses default based on input filename)
        emit_llvm: Emit LLVM IR instead of object file
        deterministic: Enable deterministic builds (sort symbol tables)
        visual: Enable ownership timeline visualizations
        warn_cost: Enable cost transparency warnings
        incremental: Enable incremental compilation (default: True)
    
    Returns:
        True if compilation succeeded, False otherwise
    
    Raises:
        LexerError: If lexical analysis fails
        ParseError: If parsing fails
        TypeCheckError: If type checking fails
        CompilationError: If compilation fails
    
    Example:
        >>> success = compile_source("fn main(): return 42", "main.pyrite")
        >>> if success:
        ...     print("Compilation succeeded")
    """
    
    # Check incremental cache if enabled
    if incremental and not emit_llvm:
        try:
            from .incremental import IncrementalCompiler
            compiler = IncrementalCompiler()
            compiler.load_cache_metadata()
            
            # Check if module should be recompiled
            should_recompile, reason = compiler.should_recompile(filename)
            if not should_recompile:
                print(f"[SKIP] Module unchanged, using cache ({reason})")
                # Load cached object file if available
                cache_entry = compiler.cache_entries.get(filename)
                if cache_entry and cache_entry.object_file_path:
                    obj_path = Path(cache_entry.object_file_path)
                    if obj_path.exists():
                        # Copy cached object file to output path if specified
                        if output_path:
                            import shutil
                            output_obj = Path(output_path).with_suffix(".o")
                            shutil.copy2(obj_path, output_obj)
                            print(f"  [OK] Using cached object file: {output_obj}")
                        return True
        except Exception as e:
            # If incremental check fails, continue with normal compilation
            print(f"[WARN] Incremental check failed: {e}, continuing with full compilation")
    
    try:
        # Phase 1: Lexical analysis
        print(f"[1/6] Lexing...")
        tokens = lex(source, filename)
        
        # Phase 2: Parsing
        print(f"[2/7] Parsing...")
        program_ast = parse(tokens)
        
        # Phase 2.3: Module resolution (load imported modules)
        print(f"[2.3/7] Resolving modules...")
        imported_modules_list = None
        try:
            from pathlib import Path as PathLib
            main_file_path = PathLib(filename)
            all_modules = resolve_modules(main_file_path)
            # Filter out the main module - we only want imported modules
            # The main module is registered as 'main' in resolve_modules
            imported_modules_list = [m for m in all_modules if m.name != 'main' and m.path != main_file_path]
        except ModuleError as e:
            print(f"Module resolution error: {e}")
            return False
        except Exception as e:
            # If module resolution fails, continue without imports (backward compatibility)
            print(f"Warning: Module resolution failed: {e}, continuing without imports")
        
        # Phase 2.5: Desugar with statements (with → let + defer)
        print(f"[2.5/7] Desugaring with statements...")
        with_desugar = WithDesugarPass()
        program_ast = with_desugar.desugar_program(program_ast)
        
        # Phase 2.6: Monomorphization (generate specialized functions)
        print(f"[2.6/7] Monomorphizing...")
        program_ast = monomorphize_program(program_ast)
        
        # Phase 3: Type checking
        print(f"[3/7] Type checking...")
        # Pass imported modules to type checker for symbol import
        type_checker = type_check(program_ast, imported_modules=imported_modules_list)
        
        if type_checker.has_errors():
            print("\nType errors found:")
            for error in type_checker.errors:
                print(f"  {error}")
            for error in type_checker.resolver.errors:
                print(f"  {error}")
            return False
        
        # Phase 4: Ownership analysis
        print(f"[4/7] Checking ownership...")
        type_env = {}
        for name, symbol in type_checker.resolver.global_scope.get_all_symbols().items():
            type_env[name] = symbol.type
        
        ownership_analyzer = analyze_ownership(program_ast, type_env, track_timeline=visual)
        
        if ownership_analyzer.has_errors():
            print("\nOwnership errors found:")
            formatter = ErrorFormatter()
            source_lines = source.split('\n')
            
            for error in ownership_analyzer.errors:
                # Enhanced error formatting for ownership errors
                if "moved value" in error.message and hasattr(error, 'span'):
                    # Extract variable name from message
                    import re
                    match = re.search(r"'([^']+)'", error.message)
                    if match:
                        var_name = match.group(1)
                        # Try to get more context from the error
                        print(formatter.format_ownership_error(
                            var_name,
                            error.span,
                            source_lines,
                            "<function parameter>"  # We'd need to enhance ownership analyzer to track this
                        ))
                        
                        # Show timeline if visual mode is enabled
                        if visual:
                            timeline = ownership_analyzer.format_timeline(var_name)
                            if timeline:
                                print(f"\n{timeline}")
                    else:
                        print(f"  {error}")
                else:
                    print(f"  {error}")
            return False
        
        # Phase 5: Borrow checking
        print(f"[5/7] Checking borrows...")
        borrow_checker = check_borrows(program_ast, type_env, type_checker, track_timeline=visual)
        
        if borrow_checker.has_errors():
            print("\nBorrow checking errors found:")
            for error in borrow_checker.errors:
                print(f"  {error}")
                # Show timeline if visual mode is enabled
                if visual and hasattr(error, 'span'):
                    # Extract variable name from error message if possible
                    import re
                    var_match = re.search(r"'([^']+)'", error.message)
                    if var_match:
                        var_name = var_match.group(1)
                        timeline = borrow_checker.format_timeline(var_name)
                        if timeline:
                            print(f"\n{timeline}")
            return False
        
        # Phase 5.5: Parameter closure inlining (post-type-check, with type information)
        print(f"[5.5/7] Inlining parameter closures...")
        inline_pass = ClosureInlinePass(type_checker)
        program_ast = inline_pass.inline_closures_in_program(program_ast)
        
        # Phase 6: Code generation
        print(f"[6/7] Generating code...")
        
        # Create codegen with type checker reference
        codegen = LLVMCodeGen(deterministic=deterministic)
        codegen.type_checker = type_checker
        codegen.warn_costs = warn_cost  # Enable cost warnings if requested
        module = codegen.compile_program(program_ast)
        llvm_ir = str(module)
        
        # Display cost warnings if enabled
        if warn_cost and codegen.cost_warnings:
            print("\nCost Warnings:")
            from .diagnostics import Diagnostic
            # ErrorFormatter already imported at module level
            formatter = ErrorFormatter()
            source_lines = source.split('\n')
            
            for warning in codegen.cost_warnings:
                diag = Diagnostic(
                    code="C0001",  # Cost warning code
                    message=warning["message"],
                    span=warning["span"],
                    level="warning",
                    help_messages=[warning.get("help_hint", "")]
                )
                print(diag.format(source))
        
        if emit_llvm:
            # Output LLVM IR only
            output = output_path or "output.ll"
            with open(output, 'w') as f:
                f.write(llvm_ir)
            print(f"\n[OK] Generated LLVM IR: {output}")
        else:
            # Compile to executable using llvmlite
            output = output_path or "a.out"
            
            print(f"[7/7] Compiling to object code...")
            
            # Initialize LLVM (if not already done)
            try:
                binding.initialize_native_target()
                binding.initialize_native_asmprinter()
            except:
                pass  # Already initialized
            
            # Parse and verify LLVM IR
            llvm_module = binding.parse_assembly(llvm_ir)
            llvm_module.verify()
            
            # Create target machine
            target = binding.Target.from_default_triple()
            target_machine = target.create_target_machine(
                reloc='pic',  # Position-independent code
                codemodel='small'
            )
            
            # Generate object file
            obj_file = output + ".o"
            with open(obj_file, "wb") as f:
                f.write(target_machine.emit_object(llvm_module))
            
            print(f"  Generated object file: {obj_file}")
            
            # Update incremental cache if enabled
            if incremental and PathLib(obj_file).exists():
                try:
                    from .incremental import IncrementalCompiler, CacheEntry
                    import time
                    compiler = IncrementalCompiler()
                    compiler.load_cache_metadata()
                    
                    # Extract dependencies from AST
                    deps = compiler.extract_dependencies(program_ast)
                    dep_hashes = {}
                    for dep in deps:
                        # Try to find dependency file and compute hash
                        # For now, just track the dependency name
                        dep_hashes[dep] = compiler.module_hashes.get(dep, "")
                    
                    # Create cache entry
                    module_hash = compiler.compute_file_hash(Path(filename))
                    entry = CacheEntry(
                        module_path=filename,
                        source_hash=module_hash,
                        dependencies=deps,
                        dependency_hashes=dep_hashes,
                        compiled_at=time.time(),
                        compiler_version=compiler.COMPILER_VERSION,
                        object_file_path=obj_file
                    )
                    compiler.save_cache_entry(filename, entry)
                    compiler.save_cache_metadata()
                except Exception as e:
                    # Cache update failure is not fatal
                    pass
            
            # Link with runtime
            print(f"[8/8] Linking...")
            from .backend.linker import link_object_files
            
            # Get runtime object files
            import os
            from pathlib import Path
            compiler_root = Path(__file__).parent.parent
            runtime_dir = compiler_root / 'runtime'
            runtime_objs = list(runtime_dir.glob("*.o"))
            
            if link_object_files([obj_file] + [str(f) for f in runtime_objs], output):
                print(f"\n[OK] Compiled executable: {output}")
                print(f"  Run with: {output}")
            else:
                print(f"\n[OK] Generated object file: {obj_file}")
                from .backend.linker import find_clang, find_gcc
                compiler = find_clang() or find_gcc() or "gcc"
                print(f"  To create executable: {compiler} {obj_file} runtime/*.o -o {output}")
        
        return True
    
    except LexerError as e:
        print(f"\nLexer error: {e}")
        return False
    except ParseError as e:
        print(f"\nParse error: {e}")
        return False
    except Exception as e:
        print(f"\nInternal compiler error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main() -> int:
    """Main entry point for pyritec compiler
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    if len(sys.argv) < 2:
        print("Usage: python -m src.compiler <input.pyrite> [-o output] [--emit-llvm] [--deterministic] [--visual] [--warn-cost] [--incremental] [--no-incremental] [--explain CODE]")
        print("\nOptions:")
        print("  -o <output>      Specify output file")
        print("  --emit-llvm      Output LLVM IR instead of executable")
        print("  --deterministic  Enable deterministic builds (sort symbol tables)")
        print("  --visual         Show ownership timeline visualizations")
        print("  --warn-cost      Enable cost transparency warnings")
        print("  --incremental    Enable incremental compilation (default: on)")
        print("  --no-incremental Disable incremental compilation")
        print("  --explain CODE   Show detailed explanation for error code")
        return 1
    
    # Check for --explain flag
    if sys.argv[1] == '--explain':
        if len(sys.argv) < 3:
            from .utils.error_explanations import list_error_codes
            print(list_error_codes())
            return 0
        else:
            from .utils.error_explanations import get_explanation
            print(get_explanation(sys.argv[2]))
            return 0
    
    input_file = sys.argv[1]
    output_file = None
    emit_llvm = False
    deterministic = False
    visual = False
    warn_cost = False
    incremental = True  # Default to incremental
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '-o' and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--emit-llvm':
            emit_llvm = True
            i += 1
        elif sys.argv[i] == '--deterministic':
            deterministic = True
            i += 1
        elif sys.argv[i] == '--visual':
            visual = True
            i += 1
        elif sys.argv[i] == '--warn-cost':
            warn_cost = True
            i += 1
        elif sys.argv[i] == '--incremental':
            incremental = True
            i += 1
        elif sys.argv[i] == '--no-incremental':
            incremental = False
            i += 1
        elif sys.argv[i] == '--explain':
                if i + 1 < len(sys.argv):
                    from .utils.error_explanations import get_explanation
                    print(get_explanation(sys.argv[i + 1]))
                    return 0
                else:
                    from .utils.error_explanations import list_error_codes
                    print(list_error_codes())
                    return 0
        else:
            print(f"Unknown option: {sys.argv[i]}")
            return 1
    
    # Compile
    success = compile_file(input_file, output_file, emit_llvm, deterministic, visual, warn_cost, incremental)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

