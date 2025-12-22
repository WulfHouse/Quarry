"""Cost analysis for Pyrite code - track allocations and performance"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass, asdict


@dataclass
class AllocationSite:
    """Represents a heap allocation"""
    file: str
    line: int
    function: str
    type_allocated: str
    estimated_bytes: int
    in_loop: bool = False
    loop_iterations: int = 1
    closure_type: str = "none"  # "parameter" (fn[...]), "runtime" (fn(...)), or "none"
    suggestion: str = ""  # Optimization suggestion


@dataclass
class CopySite:
    """Represents a large value copy"""
    file: str
    line: int
    function: str
    type_copied: str
    bytes_copied: int


@dataclass
class CostReport:
    """Complete cost analysis report"""
    allocations: List[AllocationSite]
    copies: List[CopySite]
    total_allocations: int
    total_allocation_bytes: int
    total_copies: int
    total_copy_bytes: int
    
    def to_dict(self) -> Dict:
        return {
            'allocations': [asdict(a) for a in self.allocations],
            'copies': [asdict(c) for c in self.copies],
            'summary': {
                'total_allocations': self.total_allocations,
                'total_allocation_bytes': self.total_allocation_bytes,
                'total_copies': self.total_copies,
                'total_copy_bytes': self.total_copy_bytes
            }
        }


class CostAnalyzer:
    """Analyze code for performance costs"""
    
    def __init__(self):
        self.allocations: List[AllocationSite] = []
        self.copies: List[CopySite] = []
        self.loop_depth: int = 0  # Track nested loop depth
        self.loop_iterations: List[int] = []  # Track iterations for each loop level
    
    def analyze_file(self, filepath: Path) -> CostReport:
        """Analyze a Pyrite file for costs"""
        try:
            # Parse the file - add forge to path
            repo_root = Path(__file__).parent.parent
            forge_path = repo_root / "forge"
            if str(forge_path) not in sys.path:
                sys.path.insert(0, str(forge_path))
            from src.frontend import lex
            from src.frontend import parse
            
            with open(filepath, 'r') as f:
                source = f.read()
            
            tokens = lex(source, str(filepath))
            ast = parse(tokens)
            
            # Analyze AST for allocations and copies
            self._analyze_ast(ast, str(filepath))
            
        except Exception as e:
            print(f"Warning: Could not analyze {filepath}: {e}")
            import traceback
            traceback.print_exc()
        
        return self._generate_report()
    
    def _analyze_ast(self, ast, filepath: str):
        """Walk AST and find allocation/copy sites"""
        # Reset loop tracking
        self.loop_depth = 0
        self.loop_iterations = []
        
        # Look for heap-allocating operations
        self._find_allocations(ast, filepath)
        
        # Look for large value copies
        self._find_copies(ast, filepath)
    
    def _find_allocations(self, ast, filepath: str):
        """Find heap allocation sites"""
        # Look for patterns like:
        # - List.new()
        # - Map.new()
        # - String.new()
        # - Box.new()
        
        # Handle Program AST
        if hasattr(ast, 'items'):
            for item in ast.items:
                if hasattr(item, '__class__'):
                    class_name = item.__class__.__name__
                    if class_name == 'FunctionDef':
                        function_name = getattr(item, 'name', 'unknown')
                        if hasattr(item, 'body'):
                            self._analyze_block(item.body, filepath, function_name)
                    else:
                        self._check_node_for_allocation(item, filepath, "global")
        elif hasattr(ast, 'statements'):
            for stmt in ast.statements:
                self._check_node_for_allocation(stmt, filepath, "main")
        else:
            # Try to analyze the AST directly
            self._check_node_for_allocation(ast, filepath, "main")
    
    def _analyze_block(self, block, filepath: str, function: str):
        """Analyze a block of statements"""
        if hasattr(block, 'statements'):
            for stmt in block.statements:
                self._check_node_for_allocation(stmt, filepath, function)
    
    def _check_node_for_allocation(self, node, filepath: str, function: str):
        """Check if node contains allocation"""
        if not hasattr(node, '__class__'):
            return
        
        class_name = node.__class__.__name__
        
        # Track loop entry
        was_in_loop = self.loop_depth > 0
        if class_name in ['WhileStmt', 'ForStmt']:
            self.loop_depth += 1
            estimated_iterations = self._estimate_loop_iterations(node)
            self.loop_iterations.append(estimated_iterations)
        
        # Check for allocations
        if class_name == 'MethodCall':
            method = getattr(node, 'method', None) or getattr(node, 'method_name', None)
            if method in ['new', 'with_capacity', 'from', 'clone']:
                loop_iterations = self._get_total_loop_iterations()
                suggestion = self._generate_suggestion(node, loop_iterations > 1)
                
                self.allocations.append(AllocationSite(
                    file=filepath,
                    line=self._get_line_number(node),
                    function=function,
                    type_allocated="unknown",
                    estimated_bytes=24,  # Default estimate
                    in_loop=self.loop_depth > 0,
                    loop_iterations=loop_iterations,
                    closure_type="none",
                    suggestion=suggestion
                ))
        
        # Check for parameter closures (fn[...]) - zero-cost, but note them
        if class_name == 'ParameterClosure':
            # Parameter closures are inlined, no allocation
            # But we can note them for distinction
            pass
        
        # Check for runtime closures with captures (environment allocation)
        if class_name == 'RuntimeClosure':
            env_size = getattr(node, 'environment_size', 0)
            captures = getattr(node, 'captures', [])
            if env_size > 0 or len(captures) > 0:
                # Closure environment is allocated on heap
                loop_iterations = self._get_total_loop_iterations()
                suggestion = "Consider using parameter closure (fn[...]) if compile-time known"
                
                self.allocations.append(AllocationSite(
                    file=filepath,
                    line=self._get_line_number(node),
                    function=function,
                    type_allocated=f"ClosureEnvironment({len(captures)} captures)",
                    estimated_bytes=env_size or (len(captures) * 8),  # Estimate if not provided
                    in_loop=self.loop_depth > 0,
                    loop_iterations=loop_iterations,
                    closure_type="runtime",
                    suggestion=suggestion
                ))
        
        # Recurse into child nodes (before exiting loop)
        if hasattr(node, '__dict__'):
            for attr_name, attr_value in node.__dict__.items():
                # Skip certain attributes to avoid infinite recursion
                if attr_name in ['span', 'parent']:
                    continue
                
                # Handle blocks specially to track loops
                if attr_name == 'body' and class_name in ['WhileStmt', 'ForStmt']:
                    # Analyze loop body
                    if hasattr(attr_value, 'statements'):
                        for stmt in attr_value.statements:
                            self._check_node_for_allocation(stmt, filepath, function)
                elif hasattr(attr_value, '__class__') and hasattr(attr_value, '__dict__'):
                    self._check_node_for_allocation(attr_value, filepath, function)
                elif isinstance(attr_value, list):
                    for item in attr_value:
                        if hasattr(item, '__class__') and hasattr(item, '__dict__'):
                            self._check_node_for_allocation(item, filepath, function)
        
        # Exit loop tracking (after recursing)
        if class_name in ['WhileStmt', 'ForStmt']:
            if self.loop_depth > 0:
                self.loop_depth -= 1
            if self.loop_iterations:
                self.loop_iterations.pop()
    
    def _get_line_number(self, node) -> int:
        """Extract line number from node"""
        if hasattr(node, 'span') and node.span:
            return node.span.start_line
        elif hasattr(node, 'line'):
            return node.line
        return 0
    
    def _estimate_loop_iterations(self, loop_node) -> int:
        """Estimate loop iterations (conservative estimate)"""
        # For range loops (0..n), we can estimate
        if hasattr(loop_node, '__class__'):
            if loop_node.__class__.__name__ == 'ForStmt':
                if hasattr(loop_node, 'iterable'):
                    iterable = loop_node.iterable
                    # Check for range: 0..n
                    if hasattr(iterable, '__class__') and iterable.__class__.__name__ == 'BinOp':
                        if hasattr(iterable, 'op') and iterable.op == '..':
                            # Try to extract end value
                            if hasattr(iterable, 'right'):
                                right = iterable.right
                                if hasattr(right, '__class__') and right.__class__.__name__ == 'IntLiteral':
                                    if hasattr(right, 'value'):
                                        return max(1, int(right.value))  # At least 1 iteration
        
        # Default: conservative estimate for unknown loops
        return 1000
    
    def _get_total_loop_iterations(self) -> int:
        """Get total loop iterations (multiply nested loops)"""
        if not self.loop_iterations:
            return 1
        total = 1
        for iterations in self.loop_iterations:
            total *= iterations
        return total
    
    def _generate_suggestion(self, node, in_loop: bool) -> str:
        """Generate optimization suggestion"""
        if in_loop:
            return "Consider moving allocation outside the loop"
        return ""
    
    def _find_copies(self, ast, filepath: str):
        """Find large value copy sites"""
        # For MVP, we'll skip detailed copy analysis
        # Full implementation would track struct sizes and assignments
        pass
    
    def _generate_report(self) -> CostReport:
        """Generate cost report"""
        total_alloc_bytes = sum(a.estimated_bytes * a.loop_iterations for a in self.allocations)
        total_copy_bytes = sum(c.bytes_copied for c in self.copies)
        
        return CostReport(
            allocations=self.allocations,
            copies=self.copies,
            total_allocations=len(self.allocations),
            total_allocation_bytes=total_alloc_bytes,
            total_copies=len(self.copies),
            total_copy_bytes=total_copy_bytes
        )


def cmd_cost(json_output: bool = False, level: str = "intermediate", baseline: str = None):
    """Analyze code costs
    
    Args:
        json_output: Output JSON format for CI
        level: Output level - "beginner", "intermediate", or "advanced"
        baseline: Path to baseline JSON file for comparison
    """
    if not Path("src/main.pyrite").exists():
        print("Error: src/main.pyrite not found")
        return 1
    
    print("Analyzing performance costs...")
    
    # Use both AST analysis and codegen tracking
    analyzer = CostAnalyzer()
    ast_report = analyzer.analyze_file(Path("src/main.pyrite"))
    
    # Also get cost data from codegen (if available)
    codegen_allocations = []
    try:
        # Compile with cost tracking enabled - add forge to path
        repo_root = Path(__file__).parent.parent
        forge_path = repo_root / "forge"
        if str(forge_path) not in sys.path:
            sys.path.insert(0, str(forge_path))
        from src.compiler import compile_source
        from src.backend import LLVMCodeGen
        
        with open(Path("src/main.pyrite"), 'r') as f:
            source = f.read()
        
        # Create codegen with cost tracking
        codegen = LLVMCodeGen(deterministic=False)
        codegen.track_costs = True
        
        # Try to compile (may fail, but we'll get allocation data)
        try:
            from src.frontend import lex
            from src.frontend import parse
            from src.middle import type_check
            
            tokens = lex(source, "src/main.pyrite")
            program_ast = parse(tokens)
            type_checker = type_check(program_ast)
            codegen.type_checker = type_checker
            codegen.compile_program(program_ast)
            
            # Get cost report from codegen
            codegen_report = codegen.get_cost_report()
            codegen_allocations = codegen_report.get("allocations", [])
        except Exception:
            # Compilation may fail, but we still have AST analysis
            pass
    except Exception:
        # Fall back to AST analysis only
        pass
    
    # Merge AST and codegen allocations
    # Convert codegen allocations to AllocationSite objects
    merged_allocations = list(ast_report.allocations)
    for alloc in codegen_allocations:
        merged_allocations.append(AllocationSite(
            file=alloc.get("file", "src/main.pyrite"),
            line=alloc.get("line", 0),
            function=alloc.get("function", "unknown"),
            type_allocated=alloc.get("type", "unknown"),
            estimated_bytes=alloc.get("bytes", 0),
            in_loop=False,
            loop_iterations=1,
            closure_type="none",
            suggestion=alloc.get("description", "")
        ))
    
    # Create merged report
    total_allocations = len(merged_allocations)
    total_allocation_bytes = sum(a.estimated_bytes for a in merged_allocations)
    report = CostReport(
        allocations=merged_allocations,
        copies=ast_report.copies,
        total_allocations=total_allocations,
        total_allocation_bytes=total_allocation_bytes,
        total_copies=ast_report.total_copies,
        total_copy_bytes=ast_report.total_copy_bytes
    )
    
    # Load baseline if provided
    baseline_report = None
    if baseline and Path(baseline).exists():
        try:
            baseline_data = json.loads(Path(baseline).read_text())
            baseline_report = CostReport(
                allocations=[AllocationSite(**a) for a in baseline_data.get('allocations', [])],
                copies=[CopySite(**c) for c in baseline_data.get('copies', [])],
                total_allocations=baseline_data.get('summary', {}).get('total_allocations', 0),
                total_allocation_bytes=baseline_data.get('summary', {}).get('total_allocation_bytes', 0),
                total_copies=baseline_data.get('summary', {}).get('total_copies', 0),
                total_copy_bytes=baseline_data.get('summary', {}).get('total_copy_bytes', 0)
            )
        except Exception as e:
            print(f"Warning: Could not load baseline: {e}")
    
    if json_output:
        # JSON output for tools/CI
        output = report.to_dict()
        if baseline_report:
            # Add comparison data
            output['comparison'] = {
                'allocations_delta': report.total_allocations - baseline_report.total_allocations,
                'allocation_bytes_delta': report.total_allocation_bytes - baseline_report.total_allocation_bytes,
                'copies_delta': report.total_copies - baseline_report.total_copies,
                'copy_bytes_delta': report.total_copy_bytes - baseline_report.total_copy_bytes
            }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable output based on level
        if level == "beginner":
            _print_beginner_output(report, baseline_report)
        elif level == "advanced":
            _print_advanced_output(report, baseline_report)
        else:  # intermediate
            _print_intermediate_output(report, baseline_report)
    
    return 0


def _print_beginner_output(report: CostReport, baseline: CostReport = None):
    """Print beginner-friendly output"""
    total_allocations = sum(a.loop_iterations for a in report.allocations)
    total_bytes = report.total_allocation_bytes
    
    print("\n🔹 Performance Analysis")
    print("=" * 50)
    
    if total_allocations > 0:
        print(f"\nYour code allocates memory {total_allocations} times")
        print(f"Total memory: {total_bytes:,} bytes ({total_bytes / 1024:.1f} KB)")
        
        # Show top 3 most significant
        sorted_allocations = sorted(report.allocations, 
                                   key=lambda a: a.estimated_bytes * a.loop_iterations, 
                                   reverse=True)
        
        print("\nMost significant:")
        for i, alloc in enumerate(sorted_allocations[:3], 1):
            iterations_text = f" ({alloc.loop_iterations} times)" if alloc.loop_iterations > 1 else ""
            print(f"  {i}. Line {alloc.line}: {alloc.type_allocated}{iterations_text}")
            if alloc.suggestion:
                print(f"     -> {alloc.suggestion}")
    else:
        print("\n✓ No significant allocations detected")
    
    if baseline:
        delta = total_allocations - sum(a.loop_iterations for a in baseline.allocations)
        if delta > 0:
            print(f"\n⚠️  {delta} more allocations than baseline")
        elif delta < 0:
            print(f"\n✓ {abs(delta)} fewer allocations than baseline")


def _print_intermediate_output(report: CostReport, baseline: CostReport = None):
    """Print intermediate-level output"""
    print("\nPerformance Analysis")
    print("=" * 50)
    
    # Calculate effective allocations (with loop multiplication)
    effective_allocations = sum(a.loop_iterations for a in report.allocations)
    total_bytes = report.total_allocation_bytes
    
    print(f"\nAllocations: {len(report.allocations)} sites, {effective_allocations} effective ({total_bytes:,} bytes)")
    
    if report.allocations:
        print("\nAllocation sites:")
        # Sort by impact (bytes × iterations)
        sorted_allocations = sorted(report.allocations,
                                   key=lambda a: a.estimated_bytes * a.loop_iterations,
                                   reverse=True)
        
        for alloc in sorted_allocations[:10]:  # Show top 10
            loop_info = ""
            if alloc.in_loop:
                loop_info = f" [in loop ×{alloc.loop_iterations}]"
            
            closure_info = ""
            if alloc.closure_type == "runtime":
                closure_info = " [runtime closure]"
            elif alloc.closure_type == "parameter":
                closure_info = " [parameter closure - zero-cost]"
            
            print(f"  • Line {alloc.line}: {alloc.type_allocated} ({alloc.estimated_bytes} bytes){loop_info}{closure_info}")
            if alloc.suggestion:
                print(f"    -> {alloc.suggestion}")
    
    print(f"\nCopies: {report.total_copies} sites ({report.total_copy_bytes:,} bytes)")
    
    if report.copies:
        print("\nCopy sites:")
        for copy in report.copies[:10]:
            print(f"  • Line {copy.line}: {copy.type_copied} ({copy.bytes_copied:,} bytes)")
    
    if baseline:
        _print_baseline_comparison(report, baseline)
    
    if not report.allocations and not report.copies:
        print("\n✓ No significant allocations or copies detected")


def _print_advanced_output(report: CostReport, baseline: CostReport = None):
    """Print advanced-level output with detailed metrics"""
    print("\nPerformance Analysis (Advanced)")
    print("=" * 50)
    
    effective_allocations = sum(a.loop_iterations for a in report.allocations)
    total_bytes = report.total_allocation_bytes
    
    print(f"\nSummary:")
    print(f"  Allocation sites: {len(report.allocations)}")
    print(f"  Effective allocations: {effective_allocations} (with loop multiplication)")
    print(f"  Total bytes: {total_bytes:,} ({total_bytes / 1024:.2f} KB)")
    print(f"  Copy sites: {report.total_copies}")
    print(f"  Total copy bytes: {report.total_copy_bytes:,}")
    
    # Group by type
    by_type = {}
    for alloc in report.allocations:
        typ = alloc.type_allocated
        if typ not in by_type:
            by_type[typ] = []
        by_type[typ].append(alloc)
    
    if by_type:
        print("\nBy type:")
        for typ, allocs in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
            total_for_type = sum(a.estimated_bytes * a.loop_iterations for a in allocs)
            print(f"  {typ}: {len(allocs)} sites, {total_for_type:,} bytes")
    
    # Show all allocations with full details
    if report.allocations:
        print("\nAll allocation sites:")
        sorted_allocations = sorted(report.allocations,
                                   key=lambda a: a.estimated_bytes * a.loop_iterations,
                                   reverse=True)
        
        for alloc in sorted_allocations:
            print(f"  Line {alloc.line} ({alloc.function}):")
            print(f"    Type: {alloc.type_allocated}")
            print(f"    Bytes: {alloc.estimated_bytes}")
            print(f"    In loop: {alloc.in_loop} (×{alloc.loop_iterations})")
            print(f"    Closure type: {alloc.closure_type}")
            print(f"    Effective bytes: {alloc.estimated_bytes * alloc.loop_iterations:,}")
            if alloc.suggestion:
                print(f"    Suggestion: {alloc.suggestion}")
    
    if baseline:
        _print_baseline_comparison(report, baseline, detailed=True)


def _print_baseline_comparison(report: CostReport, baseline: CostReport, detailed: bool = False):
    """Print comparison with baseline"""
    print("\n" + "=" * 50)
    print("Baseline Comparison")
    print("=" * 50)
    
    alloc_delta = report.total_allocations - baseline.total_allocations
    bytes_delta = report.total_allocation_bytes - baseline.total_allocation_bytes
    
    print(f"\nAllocations:")
    print(f"  Current: {report.total_allocations} sites ({report.total_allocation_bytes:,} bytes)")
    print(f"  Baseline: {baseline.total_allocations} sites ({baseline.total_allocation_bytes:,} bytes)")
    print(f"  Delta: {alloc_delta:+d} sites ({bytes_delta:+,d} bytes)")
    
    if alloc_delta > 0:
        print(f"  ⚠️  Regression: {alloc_delta} more allocation sites")
    elif alloc_delta < 0:
        print(f"  ✓ Improvement: {abs(alloc_delta)} fewer allocation sites")
    else:
        print(f"  ✓ No change")


if __name__ == '__main__':
    cmd_cost()

