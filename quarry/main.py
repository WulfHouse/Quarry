"""Quarry - Pyrite build system"""

import sys
import os
import json
import subprocess
from pathlib import Path

# Set up path to forge before any other imports
# This allows quarry modules to import from forge/src
_repo_root = Path(__file__).parent.parent
_forge_path = _repo_root / "forge"
if str(_forge_path) not in sys.path:
    sys.path.insert(0, str(_forge_path))

# Import incremental compiler for build graph integration
try:
    from src.utils.incremental import IncrementalCompiler
except ImportError:
    IncrementalCompiler = None

# Import version bridge (FFI to Pyrite implementation)
try:
    from .bridge.version_bridge import _compare_versions, _version_satisfies_constraint
except ImportError:
    # Fallback to local implementation if bridge not available
    def _compare_versions(v1: str, v2: str) -> int:
        """Compare two version strings
        
        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        def version_tuple(v):
            parts = v.split('.')
            return tuple(int(p) for p in parts if p.isdigit())
        
        t1 = version_tuple(v1)
        t2 = version_tuple(v2)
        
        if t1 < t2:
            return -1
        elif t1 > t2:
            return 1
        else:
            return 0

    def _version_satisfies_constraint(version: str, constraint: str) -> bool:
        """Check if a version satisfies a constraint
        
        Args:
            version: Version string (e.g., "1.0.0")
            constraint: Constraint string (e.g., ">=1.0.0", "1.0.0", "*")
            
        Returns:
            True if version satisfies constraint
        """
        if constraint == "*":
            return True
        
        if constraint.startswith(">="):
            min_version = constraint[2:].strip()
            return _compare_versions(version, min_version) >= 0
        
        if constraint.startswith("~>"):
            # Pessimistic constraint: ~>1.0 means >=1.0.0 and <2.0.0
            base_version = constraint[2:].strip()
            parts = base_version.split('.')
            if len(parts) >= 2:
                major = parts[0]
                minor = parts[1]
                # Check if version starts with same major.minor
                return version.startswith(f"{major}.{minor}")
            return version.startswith(base_version)
        
        # Exact match
        return version == constraint


# _compare_versions is now imported from version_bridge (or defined above as fallback)


def cmd_new(project_name: str):
    """Create a new Pyrite project"""
    print(f"Creating binary project `{project_name}`...")
    
    # Create project structure
    project_dir = Path(project_name)
    project_dir.mkdir(exist_ok=True)
    
    (project_dir / "src").mkdir(exist_ok=True)
    (project_dir / "tests").mkdir(exist_ok=True)
    
    # Create Quarry.toml
    toml_content = f"""[package]
name = "{project_name}"
version = "0.1.0"
edition = "2025"

[dependencies]
"""
    (project_dir / "Quarry.toml").write_text(toml_content)
    
    # Create main.pyrite
    main_content = """fn main():
    print("Hello, world!")
"""
    (project_dir / "src" / "main.pyrite").write_text(main_content)
    
    # Create .gitignore
    gitignore_content = """target/
*.ll
*.o
*.out
"""
    (project_dir / ".gitignore").write_text(gitignore_content)
    
    # Create README
    readme_content = f"""# {project_name}

A Pyrite project.

## Building

```bash
quarry build
```

## Running

```bash
quarry run
```
"""
    (project_dir / "README.md").write_text(readme_content)
    
    print(f"  Created {project_name}/")
    print(f"  Created {project_name}/Quarry.toml")
    print(f"  Created {project_name}/src/main.pyrite")
    print(f"  Created {project_name}/tests/")
    print(f"\nProject created successfully!")


def cmd_build(release: bool = False, incremental: bool = True, deterministic: bool = False, locked: bool = False, dogfood: bool = False):
    """Build the current project
    
    Args:
        release: Build in release mode (optimized)
        incremental: Use incremental compilation (default: True)
        deterministic: Enable deterministic builds (default: False)
        locked: Require Quarry.lock to match Quarry.toml (default: False)
        dogfood: Build predefined sample workspaces for dogfood validation (default: False)
    """
    # If --dogfood flag is set, build predefined workspaces
    if dogfood:
        print("Building dogfood workspaces...")
        # Get project root (parent of quarry directory)
        # __file__ is quarry/main.py, so parent.parent is project root
        project_root = Path(__file__).parent.parent
        
        workspaces = [
            ("tests/test-projects/test_e2e_project", project_root / "tests" / "test-projects" / "test_e2e_project"),
            ("forge/examples/projects/file_processor/processor", project_root / "forge" / "examples" / "projects" / "file_processor" / "processor"),
            ("forge/examples/projects/learned_project", project_root / "forge" / "examples" / "projects" / "learned_project"),
        ]
        
        failed = []
        for workspace_name, workspace_path in workspaces:
            if not workspace_path.exists():
                print(f"  Skipping {workspace_name} (not found)")
                continue
            
            print(f"\n  Building {workspace_name}...")
            # Build using quarry command via subprocess, running from workspace directory
            cmd = [sys.executable, "-m", "quarry.main", "build"]
            if release:
                cmd.append("--release")
            if not incremental:
                cmd.append("--no-incremental")
            if deterministic:
                cmd.append("--deterministic")
            if locked:
                cmd.append("--locked")
            
            # Run from workspace directory, but Python path should include forge and quarry root
            pythonpath = f"{project_root / 'forge'}{os.pathsep}{project_root}"
            result = subprocess.run(cmd, cwd=str(workspace_path), env={**os.environ, "PYTHONPATH": pythonpath})
            if result.returncode != 0:
                failed.append(workspace_name)
                print(f"  [FAILED] {workspace_name}")
            else:
                print(f"  [OK] {workspace_name}")
        
        if failed:
            print(f"\nDogfood build failed: {len(failed)} workspace(s) failed")
            for ws in failed:
                print(f"  - {ws}")
            return 1
        else:
            print(f"\nAll dogfood workspaces built successfully")
            return 0
    
    if not Path("Quarry.toml").exists():
        print("Error: Not in a Quarry project (Quarry.toml not found)")
        return 1
    
    # Validate lockfile if --locked flag is set
    if locked:
        try:
            import importlib.util
            dependency_path = Path(__file__).parent / "dependency.py"
            spec = importlib.util.spec_from_file_location("dependency", dependency_path)
            dependency_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dependency_module)
            
            lockfile_path = Path("Quarry.lock")
            if not lockfile_path.exists():
                print("Error: Quarry.lock not found. Run 'quarry resolve' to generate it.")
                return 1
            
            # Read Quarry.toml and Quarry.lock
            toml_deps = dependency_module.parse_quarry_toml("Quarry.toml")
            lockfile_deps = dependency_module.read_lockfile("Quarry.lock")
            
            # Try to use FFI bridge if available
            try:
                from .bridge.locked_validate_bridge import validate_locked_deps_ffi
                is_valid, errors, warnings = validate_locked_deps_ffi(toml_deps, lockfile_deps)
                
                if not is_valid:
                    for error in errors:
                        print(f"Error: {error}")
                    print("Run 'quarry resolve' to update Quarry.lock")
                    return 1
                
                for warning in warnings:
                    print(f"Warning: {warning}")
            except NameError:
                # Python fallback (original implementation)
                # Check if lockfile matches toml constraints
                # For each dependency in toml, check if lockfile has a version that satisfies it
                for name, toml_source in toml_deps.items():
                    if name not in lockfile_deps:
                        print(f"Error: Quarry.lock is outdated. Dependency '{name}' in Quarry.toml not found in lockfile.")
                        print("Run 'quarry resolve' to update Quarry.lock")
                        return 1
                    
                    locked_source = lockfile_deps[name]
                    
                    # For registry dependencies, verify locked version satisfies constraint
                    if toml_source.type == "registry" and locked_source.type == "registry":
                        if toml_source.version and locked_source.version:
                            if not _version_satisfies_constraint(locked_source.version, toml_source.version):
                                print(f"Error: Quarry.lock is outdated. Locked version '{locked_source.version}' for '{name}' does not satisfy constraint '{toml_source.version}'")
                                print("Run 'quarry resolve' to update Quarry.lock")
                                return 1
                    
                    # For git/path dependencies, verify source matches
                    elif toml_source.type != locked_source.type:
                        print(f"Error: Quarry.lock is outdated. Source type mismatch for '{name}'")
                        print("Run 'quarry resolve' to update Quarry.lock")
                        return 1
                
                # Check for extra dependencies in lockfile (shouldn't happen, but check anyway)
                for name in lockfile_deps:
                    if name not in toml_deps:
                        print(f"Warning: Quarry.lock contains '{name}' which is not in Quarry.toml")
            
        except Exception as e:
            print(f"Error validating lockfile: {e}")
            return 1
    else:
        # Auto-resolve if lockfile missing (when not --locked)
        lockfile_path = Path("Quarry.lock")
        if not lockfile_path.exists():
            print("Quarry.lock not found. Resolving dependencies...")
            try:
                import importlib.util
                dependency_path = Path(__file__).parent / "dependency.py"
                spec = importlib.util.spec_from_file_location("dependency", dependency_path)
                dependency_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(dependency_module)
                
                deps = dependency_module.parse_quarry_toml("Quarry.toml")
                resolved = dependency_module.resolve_dependencies(deps)
                dependency_module.generate_lockfile(resolved, "Quarry.lock")
                print("Generated Quarry.lock")
            except Exception as e:
                print(f"Warning: Failed to auto-resolve dependencies: {e}")
                # Continue with build anyway
    
    build_type = "release" if release else "debug"
    
    # Find main.pyrite (use absolute path)
    main_file = Path("src/main.pyrite").resolve()
    if not main_file.exists():
        print("Error: src/main.pyrite not found")
        return 1
    
    # Try incremental build with build graph (enabled by default, can be disabled with --no-incremental)
    # Note: Incremental builds are currently only for debug mode
    if incremental and not release:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from src.utils.incremental import IncrementalCompiler
            import time
            
            # Construct build graph
            try:
                import importlib.util
                build_graph_path = Path(__file__).parent / "build_graph.py"
                spec = importlib.util.spec_from_file_location("build_graph", build_graph_path)
                build_graph_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(build_graph_module)
                
                graph = build_graph_module.construct_build_graph(".")
                build_order = graph.topological_sort()
                
                # Ensure cache directory exists
                cache_dir = Path(".pyrite/cache")
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                inc_compiler = IncrementalCompiler(cache_dir)
                inc_compiler.load_cache_metadata()
                
                # Check each package in build order
                all_cached = True
                for package_name in build_order:
                    package_node = graph.nodes.get(package_name)
                    if package_node and package_node.path:
                        package_main = package_node.path / "src" / "main.pyrite"
                        if package_main.exists():
                            should_compile, reason = inc_compiler.should_recompile(str(package_main))
                            if should_compile:
                                all_cached = False
                                print(f"   Compiling {package_name} ({reason})")
                            else:
                                print(f"   Checking {package_name} [cached]")
                
                # Check main package
                should_compile, reason = inc_compiler.should_recompile(str(main_file))
                
                if not should_compile and all_cached:
                    print(f"   Checking src/main.pyrite")
                    print(f"    Finished {build_type} [cached] in 0.1s")
                    return 0
                else:
                    if should_compile:
                        print(f"   Compiling src/main.pyrite ({reason})")
            except Exception as e:
                # If build graph fails, fall back to single-package incremental
                cache_dir = Path(".pyrite/cache")
                cache_dir.mkdir(parents=True, exist_ok=True)
                
                inc_compiler = IncrementalCompiler(cache_dir)
                inc_compiler.load_cache_metadata()
                
                should_compile, reason = inc_compiler.should_recompile(str(main_file))
                
                if not should_compile:
                    print(f"   Checking src/main.pyrite")
                    print(f"    Finished {build_type} [cached] in 0.1s")
                    return 0
                else:
                    print(f"   Compiling src/main.pyrite ({reason})")
        except Exception as e:
            # If incremental fails, fall back to full compilation
            print(f"   Compiling project ({build_type})...")
    else:
        if not incremental:
            print(f"   Compiling project ({build_type}) [no incremental]...")
        else:
            print(f"   Compiling project ({build_type})...")
    
    # Create target directory (use absolute path)
    target_dir = Path("target") / build_type
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Compile using pyrite compiler
    output = target_dir / "main"
    
    # Get project root (parent of quarry directory)
    compiler_root = Path(__file__).parent.parent
    
    # Build compiler command
    cmd = [
        sys.executable, "-m", "src.compiler",
        str(main_file),
        "-o", str(output),
        "--emit-llvm"
    ]
    if deterministic:
        cmd.append("--deterministic")
    
    result = subprocess.run(cmd, cwd=compiler_root, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Compilation failed:")
        print(result.stdout)
        print(result.stderr)
        return 1
    
    print(f"    Finished {build_type} target(s)")
    
    # Generate BuildManifest if deterministic
    if deterministic:
        from quarry.deterministic import DeterministicBuilder
        builder = DeterministicBuilder()
        
        # Find all source files
        src_dir = Path("src")
        source_files = builder.find_all_source_files(src_dir)
        
        # Generate manifest
        manifest = builder.generate_manifest(
            output,
            source_files,
            compiler_version="2.0.0",
            build_flags=["--deterministic"] + (["--release"] if release else [])
        )
        
        # Save manifest
        manifest_dict = manifest.to_dict()
        manifest_path = Path("BuildManifest.toml")
        
        # Try to save as TOML, fall back to JSON
        try:
            import tomli_w
            toml_data = {
                'build': {
                    'hash': manifest_dict['build_hash'],
                    'timestamp': manifest_dict['timestamp'],
                    'compiler_version': manifest_dict['compiler_version'],
                    'target': manifest_dict['target'],
                    'flags': manifest_dict['build_flags']
                },
                'sources': manifest_dict['source_files'],
                'dependencies': manifest_dict['dependencies']
            }
            manifest_path.write_text(tomli_w.dumps(toml_data))
        except ImportError:
            # Fall back to JSON
            manifest_path = Path("BuildManifest.json")
            manifest_path.write_text(json.dumps(manifest_dict, indent=2))
        
        print(f"\n✓ Deterministic build complete")
        print(f"  Binary hash: {manifest.build_hash}")
        print(f"  Manifest saved to: {manifest_path}")
    
    # Save cache entry if incremental
    if incremental and not release:
        try:
            from src.utils.incremental import IncrementalCompiler, CacheEntry
            import time
            
            inc_compiler = IncrementalCompiler(Path(".quarry/cache"))
            inc_compiler.load_cache_metadata()
            
            # Create cache entry
            entry = CacheEntry(
                module_path=str(main_file),
                source_hash=inc_compiler.compute_file_hash(main_file),
                dependencies=[],
                dependency_hashes={},
                compiled_at=time.time(),
                compiler_version=inc_compiler.COMPILER_VERSION,
                object_file_path=str(output.with_suffix('.o'))
            )
            
            inc_compiler.save_cache_entry(str(main_file), entry)
            inc_compiler.save_cache_metadata()
        except Exception as e:
            pass  # Cache save is optional
    
    return 0


def cmd_run():
    """Build and run the project"""
    # Build first
    if cmd_build() != 0:
        return 1
    
    # Run the executable
    exe = Path("target/debug/main")
    if not exe.exists():
        # Try .ll file
        ll_file = Path("target/debug/main.ll")
        if ll_file.exists():
            print("\nNote: LLVM IR generated. Use 'clang main.ll -o main' to create executable")
            return 0
        print(f"Error: Executable not found: {exe}")
        return 1
    
    # Execute
    result = subprocess.run([str(exe)])
    return result.returncode


def cmd_clean():
    """Remove build artifacts"""
    import shutil
    
    if Path("target").exists():
        shutil.rmtree("target")
        print("Removed target/ directory")
    else:
        print("Nothing to clean")
    
    return 0


def cmd_test():
    """Run tests"""
    from .test_runner import run_tests
    
    return run_tests(Path.cwd())


def cmd_fmt():
    """Format code"""
    from .formatter import format_directory
    
    print("Formatting code...")
    
    # Format all .pyrite files in src/
    if Path("src").exists():
        success = format_directory("src")
        if success:
            print("  Formatted all files in src/")
            return 0
        else:
            print("  Some files could not be formatted")
            return 1
    else:
        print("  No src/ directory found")
        return 1


def cmd_fix(interactive: bool = True, auto: bool = False):
    """Run auto-fix on current project"""
    import sys
    from pathlib import Path
    # Add parent directory to path for imports
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    # Import using absolute path
    import importlib.util
    auto_fix_path = Path(__file__).parent / "auto_fix.py"
    spec = importlib.util.spec_from_file_location("auto_fix", auto_fix_path)
    auto_fix_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(auto_fix_module)
    return auto_fix_module.cmd_fix(interactive=interactive, auto=auto)


def cmd_cost(json_output: bool = False, level: str = "intermediate", baseline: str = None):
    """Analyze code costs"""
    import sys
    from pathlib import Path
    # Import using absolute path
    import importlib.util
    cost_analysis_path = Path(__file__).parent / "cost_analysis.py"
    spec = importlib.util.spec_from_file_location("cost_analysis", cost_analysis_path)
    cost_analysis_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cost_analysis_module)
    return cost_analysis_module.cmd_cost(json_output=json_output, level=level, baseline=baseline)


def cmd_bloat():
    """Analyze binary size"""
    from .binary_size import cmd_bloat as run_bloat_analysis
    
    # Parse arguments
    target = None
    compare = None
    fail_if_exceeds = None
    binary = None
    
    i = 2  # Start after "bloat"
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--target" and i + 1 < len(sys.argv):
            target = sys.argv[i + 1]
            i += 2
        elif arg == "--compare" and i + 1 < len(sys.argv):
            compare = sys.argv[i + 1]
            i += 2
        elif arg == "--fail-if-exceeds" and i + 1 < len(sys.argv):
            try:
                fail_if_exceeds = int(sys.argv[i + 1])
            except ValueError:
                print(f"Error: --fail-if-exceeds requires a number (bytes)")
                return 1
            i += 2
        elif arg == "--binary" and i + 1 < len(sys.argv):
            binary = sys.argv[i + 1]
            i += 2
        else:
            i += 1
    
    return run_bloat_analysis(
        target=target,
        compare=compare,
        fail_if_exceeds=fail_if_exceeds,
        binary=binary
    )


def cmd_perf(baseline: bool = False, check: bool = False, explain: bool = False, threshold: float = 5.0, diff_asm: str = None):
    """Performance profiling"""
    from .perf_lock import cmd_perf as run_perf
    # Only pass arguments that cmd_perf accepts
    return run_perf(baseline=baseline, check=check, explain=explain, threshold=threshold)


def cmd_resolve():
    """Resolve dependencies and generate Quarry.lock"""
    import sys
    from pathlib import Path
    
    # Check for Quarry.toml
    if not Path("Quarry.toml").exists():
        print("Error: Quarry.toml not found")
        print("Run this command from a Quarry project directory")
        return 1
    
    # Try to use Pyrite resolve bridge if available
    try:
        from .bridge.resolve_bridge import resolve_dependencies_ffi
        # Read TOML content
        toml_content = Path("Quarry.toml").read_text(encoding='utf-8')
        
        # Resolve using Pyrite bridge
        result = resolve_dependencies_ffi(toml_content, Path.cwd())
        
        # Write lockfile
        Path("Quarry.lock").write_text(result["lockfile_content"], encoding='utf-8')
        
        # Print output
        print(result["formatted_output"], end='')
        
        return 0
    
    except (NameError, ImportError):
        # Python fallback (original implementation)
        # Import using absolute path
        import importlib.util
        dependency_path = Path(__file__).parent / "dependency.py"
        spec = importlib.util.spec_from_file_location("dependency", dependency_path)
        dependency_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dependency_module)
        
        try:
            # Parse dependencies from Quarry.toml
            deps = dependency_module.parse_quarry_toml("Quarry.toml")
            
            if not deps:
                print("No dependencies found in Quarry.toml")
                # Still create empty lockfile for consistency
                dependency_module.generate_lockfile({}, "Quarry.lock")
                print("Generated Quarry.lock (empty)")
                return 0
            
            # Resolve versions
            resolved = dependency_module.resolve_dependencies(deps)
            
            # Generate lockfile
            dependency_module.generate_lockfile(resolved, "Quarry.lock")
            
            print(f"Resolved {len(resolved)} dependencies")
            for name, source in sorted(resolved.items()):
                if source.type == "registry":
                    print(f"  {name} = {source.version}")
                elif source.type == "git":
                    print(f"  {name} = {{ git = \"{source.git_url}\", branch = \"{source.git_branch or 'main'}\" }}")
                elif source.type == "path":
                    print(f"  {name} = {{ path = \"{source.path}\" }}")
            print("\nGenerated Quarry.lock")
            
            return 0
        
        except ValueError as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error resolving dependencies: {e}")
            import traceback
            traceback.print_exc()
            return 1
    except Exception as e:
        # FFI error, fall back to Python
        print(f"Warning: Pyrite resolve failed, falling back to Python: {e}", file=sys.stderr)
        # Continue with Python fallback (same as above)
        import importlib.util
        dependency_path = Path(__file__).parent / "dependency.py"
        spec = importlib.util.spec_from_file_location("dependency", dependency_path)
        dependency_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dependency_module)
        
        try:
            deps = dependency_module.parse_quarry_toml("Quarry.toml")
            
            if not deps:
                print("No dependencies found in Quarry.toml")
                dependency_module.generate_lockfile({}, "Quarry.lock")
                print("Generated Quarry.lock (empty)")
                return 0
            
            resolved = dependency_module.resolve_dependencies(deps)
            dependency_module.generate_lockfile(resolved, "Quarry.lock")
            
            print(f"Resolved {len(resolved)} dependencies")
            for name, source in sorted(resolved.items()):
                if source.type == "registry":
                    print(f"  {name} = {source.version}")
                elif source.type == "git":
                    print(f"  {name} = {{ git = \"{source.git_url}\", branch = \"{source.git_branch or 'main'}\" }}")
                elif source.type == "path":
                    print(f"  {name} = {{ path = \"{source.path}\" }}")
            print("\nGenerated Quarry.lock")
            
            return 0
        
        except ValueError as e:
            print(f"Error: {e}")
            return 1
        except Exception as e:
            print(f"Error resolving dependencies: {e}")
            import traceback
            traceback.print_exc()
            return 1


def cmd_update(package_name: str = None):
    """Update Quarry.lock with latest compatible versions
    
    Args:
        package_name: Optional package name to update (if None, update all)
    """
    import sys
    from pathlib import Path
    # Import using absolute path
    import importlib.util
    dependency_path = Path(__file__).parent / "dependency.py"
    spec = importlib.util.spec_from_file_location("dependency", dependency_path)
    dependency_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dependency_module)
    
    # Check for Quarry.toml
    if not Path("Quarry.toml").exists():
        print("Error: Quarry.toml not found")
        print("Run this command from a Quarry project directory")
        return 1
    
    print("Updating dependencies...")
    
    try:
        # Read current dependencies from Quarry.toml
        deps = dependency_module.parse_quarry_toml("Quarry.toml")
        
        if not deps:
            print("No dependencies to update")
            return 0
        
        # Read existing lockfile if it exists
        lockfile_path = Path("Quarry.lock")
        existing_locked = {}
        if lockfile_path.exists():
            existing_locked = dependency_module.read_lockfile("Quarry.lock")
        
        # Resolve dependencies (may get new versions)
        resolved = dependency_module.resolve_dependencies(deps)
        
        # If updating specific package, only update that one
        if package_name:
            if package_name not in deps:
                print(f"Error: Package '{package_name}' not found in Quarry.toml")
                return 1
            
            # Update only this package
            if package_name in existing_locked:
                old_source = existing_locked[package_name]
                new_source = resolved[package_name]
                # Compare versions for registry, or sources for git/path
                if old_source.type == "registry" and new_source.type == "registry":
                    if old_source.version != new_source.version:
                        existing_locked[package_name] = new_source
                        print(f"Updated {package_name}: {old_source.version} -> {new_source.version}")
                    else:
                        print(f"{package_name} is already at latest compatible version ({new_source.version})")
                else:
                    # Git/path dependencies - update if source changed
                    existing_locked[package_name] = new_source
                    print(f"Updated {package_name}")
            else:
                existing_locked[package_name] = resolved[package_name]
                print(f"Added {package_name}")
            
            resolved = existing_locked
        else:
            # Update all packages
            updated_count = 0
            for name, new_source in resolved.items():
                if name in existing_locked:
                    old_source = existing_locked[name]
                    if old_source.type == "registry" and new_source.type == "registry":
                        if old_source.version != new_source.version:
                            updated_count += 1
                            print(f"  Updated {name}: {old_source.version} -> {new_source.version}")
                    else:
                        # Git/path - always update
                        updated_count += 1
                        print(f"  Updated {name}")
                else:
                    updated_count += 1
                    if new_source.type == "registry":
                        print(f"  Added {name} = {new_source.version}")
                    else:
                        print(f"  Added {name}")
            
            if updated_count == 0:
                print("All dependencies are up to date")
        
        # Generate updated lockfile
        dependency_module.generate_lockfile(resolved, "Quarry.lock")
        
        print(f"\nUpdated Quarry.lock")
        
        return 0
    
    except ValueError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Error updating dependencies: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_install():
    """Install dependencies from Quarry.lock"""
    import sys
    from pathlib import Path
    # Import using absolute path
    import importlib.util
    
    dependency_path = Path(__file__).parent / "dependency.py"
    spec = importlib.util.spec_from_file_location("dependency", dependency_path)
    dependency_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dependency_module)
    
    installer_path = Path(__file__).parent / "installer.py"
    spec_installer = importlib.util.spec_from_file_location("installer", installer_path)
    installer_module = importlib.util.module_from_spec(spec_installer)
    spec_installer.loader.exec_module(installer_module)
    
    # Check for Quarry.lock
    lockfile_path = Path("Quarry.lock")
    if not lockfile_path.exists():
        print("Error: Quarry.lock not found")
        print("Run 'quarry resolve' to generate Quarry.lock first")
        return 1
    
    print("Installing dependencies...")
    
    try:
        # Read locked dependencies
        locked_deps = dependency_module.read_lockfile("Quarry.lock")
        
        if not locked_deps:
            print("No dependencies to install")
            return 0
        
        # Create deps directory
        deps_dir = Path("deps")
        deps_dir.mkdir(parents=True, exist_ok=True)
        
        installed_count = 0
        skipped_count = 0
        
        # Install each dependency based on source type
        for name, source in sorted(locked_deps.items()):
            target_path = None
            
            if source.type == "git":
                # Install git dependency
                try:
                    target_path = installer_module.install_git_dependency(
                        name, source.git_url, source.git_branch, deps_dir=deps_dir, expected_commit=source.commit
                    )
                    if target_path.exists() and (target_path / "Quarry.toml").exists():
                        # Check if this is a new installation
                        if not (deps_dir / name).exists() or not (deps_dir / name / "Quarry.toml").exists():
                            installed_count += 1
                            print(f"  Installed {name} from {source.git_url}")
                        else:
                            skipped_count += 1
                            print(f"  {name} already installed")
                except Exception as e:
                    print(f"  Error installing {name}: {e}")
                    return 1
            
            elif source.type == "path":
                # Install path dependency
                try:
                    target_path = installer_module.install_path_dependency(
                        name, source.path, deps_dir=deps_dir
                    )
                    if target_path.exists() and (target_path / "Quarry.toml").exists():
                        if not (deps_dir / name).exists() or not (deps_dir / name / "Quarry.toml").exists():
                            installed_count += 1
                            print(f"  Installed {name} from {source.path}")
                        else:
                            skipped_count += 1
                            print(f"  {name} already installed")
                except Exception as e:
                    print(f"  Error installing {name}: {e}")
                    return 1
            
            elif source.type == "registry":
                # Install registry dependency
                try:
                    target_path = installer_module.install_registry_dependency(
                        name, source.version, deps_dir=deps_dir, expected_checksum=source.checksum
                    )
                    if target_path.exists() and (target_path / "Quarry.toml").exists():
                        if not (deps_dir / f"{name}-{source.version}").exists():
                            installed_count += 1
                            print(f"  Installed {name} = {source.version}")
                        else:
                            skipped_count += 1
                            print(f"  {name} already installed")
                except Exception as e:
                    print(f"  Error installing {name}: {e}")
                    return 1
        
        print(f"\nInstalled {installed_count} dependencies")
        if skipped_count > 0:
            print(f"Skipped {skipped_count} dependencies (already installed)")
        
        return 0
    
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        import traceback
        traceback.print_exc()
        return 1


def cmd_search(query: str = None):
    """Search for packages in registry
    
    Args:
        query: Search query (package name pattern)
    """
    import importlib.util
    
    # Import registry module
    registry_path = Path(__file__).parent / "registry.py"
    spec = importlib.util.spec_from_file_location("registry", registry_path)
    registry_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry_module)
    
    if not query:
        print("Usage: quarry search <query>")
        print("Search for packages in registry")
        return 1
    
    # Read registry index
    index = registry_module.read_index()
    
    if not index:
        print("Registry is empty")
        return 0
    
    # Search for matching packages
    matches = []
    query_lower = query.lower()
    
    for package_name, versions in index.items():
        if query_lower in package_name.lower():
            matches.append((package_name, versions))
    
    if not matches:
        print(f"No packages found matching '{query}'")
        return 0
    
    # Print results
    print(f"Found {len(matches)} package(s) matching '{query}':")
    for package_name, versions in sorted(matches):
        versions_str = ", ".join(versions)
        print(f"  {package_name} (versions: {versions_str})")
    
    return 0


def cmd_info(package_name: str = None):
    """Show package information from registry
    
    Args:
        package_name: Package name to show info for
    """
    import importlib.util
    
    # Import registry module
    registry_path = Path(__file__).parent / "registry.py"
    spec = importlib.util.spec_from_file_location("registry", registry_path)
    registry_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(registry_module)
    
    if not package_name:
        print("Usage: quarry info <package>")
        print("Show package information from registry")
        return 1
    
    # Get package versions
    versions = registry_module.get_package_versions(package_name)
    
    if not versions:
        print(f"Package '{package_name}' not found in registry")
        return 1
    
    # Get metadata for latest version (or first version)
    latest_version = versions[-1]  # Sorted, so last is latest
    metadata = registry_module.get_package_metadata(package_name, latest_version)
    
    if metadata:
        print(f"Package: {metadata.get('name', package_name)}")
        print(f"Version: {metadata.get('version', latest_version)}")
        print(f"Available versions: {', '.join(versions)}")
        
        if 'description' in metadata:
            print(f"Description: {metadata['description']}")
        
        if 'license' in metadata:
            print(f"License: {metadata['license']}")
        
        if 'authors' in metadata:
            authors = metadata['authors']
            if isinstance(authors, list):
                print(f"Authors: {', '.join(authors)}")
            else:
                print(f"Authors: {authors}")
        
        if 'dependencies' in metadata:
            deps = metadata['dependencies']
            if deps:
                print("Dependencies:")
                for dep_name, dep_info in deps.items():
                    if isinstance(dep_info, dict):
                        dep_version = dep_info.get('version', '?')
                        print(f"  {dep_name} = {dep_version}")
                    else:
                        print(f"  {dep_name} = {dep_info}")
        
        if 'checksum' in metadata:
            print(f"Checksum: {metadata['checksum']}")
        
        return 0
    else:
        # Fallback: just show versions
        print(f"Package: {package_name}")
        print(f"Available versions: {', '.join(versions)}")
        print("(Metadata not available)")
    
        return 0


def cmd_publish(dry_run: bool = False, no_test: bool = False):
    """Publish package to registry
    
    Args:
        dry_run: Validate and package but don't publish
        no_test: Skip test validation (not recommended)
    """
    import importlib.util
    
    # Import publisher and registry modules
    publisher_path = Path(__file__).parent / "publisher.py"
    spec_pub = importlib.util.spec_from_file_location("publisher", publisher_path)
    publisher_module = importlib.util.module_from_spec(spec_pub)
    spec_pub.loader.exec_module(publisher_module)
    
    # Import registry module (try to use already-imported module if available)
    try:
        from quarry import registry as registry_module
    except ImportError:
        registry_path = Path(__file__).parent / "registry.py"
        spec_reg = importlib.util.spec_from_file_location("registry", registry_path)
        registry_module = importlib.util.module_from_spec(spec_reg)
        spec_reg.loader.exec_module(registry_module)
    
    dependency_path = Path(__file__).parent / "dependency.py"
    spec_dep = importlib.util.spec_from_file_location("dependency", dependency_path)
    dependency_module = importlib.util.module_from_spec(spec_dep)
    spec_dep.loader.exec_module(dependency_module)
    
    # Validate project
    print("Validating project...")
    is_valid, errors = publisher_module.validate_for_publish(".")
    
    if not is_valid:
        print("Validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    # Run tests (unless --no-test)
    if not no_test:
        print("Running tests...")
        test_result = cmd_test()
        if test_result != 0:
            print("Tests failed. Cannot publish.")
            print("Use --no-test to skip test validation (not recommended)")
            return 1
    
    # Package project
    print("Packaging project...")
    package_dir = publisher_module.package_project(".")
    
    if package_dir is None:
        print("Error: Failed to package project")
        return 1
    
    # Read package info from Quarry.toml
    toml_path = Path(".") / "Quarry.toml"
    try:
        import tomllib
        with open(toml_path, 'rb') as f:
            toml_data = tomllib.load(f)
    except ImportError:
        try:
            import tomli as tomllib
            with open(toml_path, 'rb') as f:
                toml_data = tomli.load(f)
        except ImportError:
            print("Error: Cannot parse Quarry.toml (tomllib/tomli not available)")
            return 1
    
    package_name = toml_data.get("package", {}).get("name", "unknown")
    package_version = toml_data.get("package", {}).get("version", "0.1.0")
    
    # Generate checksum
    print("Computing checksum...")
    checksum = publisher_module.compute_package_checksum(package_dir)
    checksum_str = f"sha256:{checksum}"
    
    # Read dependencies
    dependencies = dependency_module.parse_quarry_toml(str(toml_path))
    deps_dict = {}
    for dep_name, dep_source in dependencies.items():
        if dep_source.type == "registry":
            deps_dict[dep_name] = {"version": dep_source.version}
        elif dep_source.type == "git":
            deps_dict[dep_name] = {"git": dep_source.git_url, "branch": dep_source.git_branch}
        elif dep_source.type == "path":
            deps_dict[dep_name] = {"path": dep_source.path}
    
    # Create metadata
    metadata = {
        "name": package_name,
        "version": package_version,
        "dependencies": deps_dict,
        "checksum": checksum_str,
        "license": toml_data.get("package", {}).get("license", "Unknown"),
        "authors": toml_data.get("package", {}).get("authors", [])
    }
    
    if dry_run:
        print(f"\nDry run: Would publish {package_name} {package_version}")
        print(f"Checksum: {checksum_str}")
        print("Package directory:", package_dir)
        return 0
    
    # Store package in registry
    print(f"Publishing {package_name} {package_version} to registry...")
    registry_path_obj = registry_module.ensure_registry()
    target_dir = registry_path_obj / package_name / package_version
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy package directory to registry
    import shutil
    if target_dir.exists():
        shutil.rmtree(target_dir)
    shutil.copytree(package_dir, target_dir)
    
    # Store metadata
    registry_module.store_package_metadata(package_name, package_version, metadata)
    
    # Update index
    registry_module.add_to_index(package_name, package_version)
    
    print(f"Published {package_name} {package_version} to registry")
    print(f"Checksum: {checksum_str}")
    
    return 0


def print_usage():
    """Print usage information"""
    print("""Quarry - Pyrite build system

Usage:
    quarry new <name>       Create a new project
    quarry build            Build the project
    quarry build --release  Build in release mode
    quarry build --dogfood  Build predefined sample workspaces for validation
    quarry run              Build and run the project
    quarry clean            Remove build artifacts
    quarry test             Run tests
    quarry test --verbose   Show detailed test output
    quarry test <name>      Run specific test
    quarry test --no-fail-fast  Continue on failure
    quarry fmt              Format code
    quarry fix              Auto-fix common errors (interactive by default)
    quarry fix --interactive Auto-fix common errors (interactive mode)
    quarry fix --auto       Auto-fix common errors (automatic, no prompts)
    quarry resolve          Resolve dependencies and generate Quarry.lock
    quarry install          Install dependencies from Quarry.lock
    quarry search <query>   Search for packages in registry
    quarry info <package>   Show package information
    quarry publish          Publish package to registry
    quarry publish --dry-run  Validate and package without publishing
    quarry publish --no-test  Skip test validation
    quarry update           Update Quarry.lock with latest compatible versions
    quarry update --package <name>  Update specific package only
    quarry cost             Analyze performance costs
    quarry bloat            Analyze binary size
    quarry perf --baseline  Generate performance baseline (Perf.lock)
    quarry perf --check     Check for performance regressions
    quarry --help           Show this help

Examples:
    quarry new myproject
    cd myproject
    quarry resolve          # Resolve dependencies
    quarry build
    quarry run
    quarry fix              # Interactive fix selection
""")


def main():
    """Main entry point for quarry"""
    if len(sys.argv) < 2:
        print_usage()
        return 0  # Help is a successful operation
    
    command = sys.argv[1]
    
    if command == "new":
        if len(sys.argv) < 3:
            print("Error: Project name required")
            print("Usage: quarry new <name>")
            return 1
        return cmd_new(sys.argv[2])
    
    elif command == "build":
        release = "--release" in sys.argv
        deterministic = "--deterministic" in sys.argv
        incremental = "--no-incremental" not in sys.argv  # Default to True, disable with flag
        locked = "--locked" in sys.argv
        dogfood = "--dogfood" in sys.argv
        return cmd_build(release, incremental=incremental, deterministic=deterministic, locked=locked, dogfood=dogfood)
    
    elif command == "run":
        # Parse --release flag
        release = "--release" in sys.argv
        # Parse --args to pass arguments to binary
        binary_args = []
        if "--args" in sys.argv:
            idx = sys.argv.index("--args")
            binary_args = sys.argv[idx + 1:]
        return cmd_run(release=release, args=binary_args)
    
    elif command == "clean":
        return cmd_clean()
    
    elif command == "test":
        return cmd_test()
    
    elif command == "fmt":
        return cmd_fmt()
    
    elif command == "fix":
        auto = "--auto" in sys.argv
        interactive = "--interactive" in sys.argv or (not auto)  # Interactive by default, or if --interactive specified
        return cmd_fix(interactive=interactive, auto=auto)
    
    elif command == "cost":
        json_output = "--json" in sys.argv
        
        # Parse --level flag
        level = "intermediate"
        for i, arg in enumerate(sys.argv):
            if arg == "--level" and i + 1 < len(sys.argv):
                level = sys.argv[i + 1]
                if level not in ["beginner", "intermediate", "advanced"]:
                    print(f"Error: --level must be 'beginner', 'intermediate', or 'advanced'")
                    return 1
                break
            elif arg.startswith("--level="):
                level = arg.split("=", 1)[1]
                if level not in ["beginner", "intermediate", "advanced"]:
                    print(f"Error: --level must be 'beginner', 'intermediate', or 'advanced'")
                    return 1
                break
        
        # Parse --baseline flag
        baseline = None
        if "--baseline" in sys.argv:
            idx = sys.argv.index("--baseline")
            if idx + 1 < len(sys.argv):
                baseline = sys.argv[idx + 1]
        
        return cmd_cost(json_output=json_output, level=level, baseline=baseline)
    
    elif command == "bloat":
        return cmd_bloat()
    
    elif command == "verify-build":
        from quarry.deterministic import cmd_verify_build
        # Parse --binary and --manifest flags
        binary_path = None
        manifest_path = None
        for i, arg in enumerate(sys.argv):
            if arg == "--binary" and i + 1 < len(sys.argv):
                binary_path = sys.argv[i + 1]
            elif arg == "--manifest" and i + 1 < len(sys.argv):
                manifest_path = sys.argv[i + 1]
            elif arg.startswith("--binary="):
                binary_path = arg.split("=", 1)[1]
            elif arg.startswith("--manifest="):
                manifest_path = arg.split("=", 1)[1]
        return cmd_verify_build(binary_path, manifest_path)
    
    elif command == "perf":
        baseline = "--baseline" in sys.argv
        check = "--check" in sys.argv
        explain = "--explain" in sys.argv
        
        # Parse --diff-asm
        diff_asm = None
        if "--diff-asm" in sys.argv:
            idx = sys.argv.index("--diff-asm")
            if idx + 1 < len(sys.argv):
                diff_asm = sys.argv[idx + 1]
        
        # Parse --threshold
        threshold = 5.0
        if "--threshold" in sys.argv:
            idx = sys.argv.index("--threshold")
            if idx + 1 < len(sys.argv):
                try:
                    threshold = float(sys.argv[idx + 1])
                except ValueError:
                    print("Error: --threshold requires a number")
                    return 1
        
        return cmd_perf(baseline=baseline, check=check, explain=explain, 
                       threshold=threshold, diff_asm=diff_asm)
    
    elif command == "resolve":
        return cmd_resolve()
    
    elif command == "install":
        return cmd_install()
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("Error: Search query required")
            print("Usage: quarry search <query>")
            return 1
        return cmd_search(sys.argv[2])
    
    elif command == "info":
        if len(sys.argv) < 3:
            print("Error: Package name required")
            print("Usage: quarry info <package>")
            return 1
        return cmd_info(sys.argv[2])
    
    elif command == "publish":
        dry_run = "--dry-run" in sys.argv
        no_test = "--no-test" in sys.argv
        return cmd_publish(dry_run=dry_run, no_test=no_test)
    
    elif command in ["--help", "-h", "help"]:
        print_usage()
        return 0
    
    else:
        print(f"Unknown command: {command}")
        print_usage()
        return 1


if __name__ == "__main__":
    sys.exit(main())

