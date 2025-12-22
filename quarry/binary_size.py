"""Binary size analysis for Pyrite executables"""

import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import platform

# Binary parsing libraries (optional, with fallbacks)
try:
    from elftools.elf.elffile import ELFFile
    from elftools.elf.sections import SymbolTableSection
    HAS_ELF = True
except ImportError:
    HAS_ELF = False

try:
    import pefile
    HAS_PE = True
except ImportError:
    HAS_PE = False

try:
    from macholib.MachO import MachO
    HAS_MACHO = True
except ImportError:
    HAS_MACHO = False


@dataclass
class Symbol:
    """Represents a symbol in the binary"""
    name: str
    size: int
    section: str
    type: str  # function, data, etc.
    crate: Optional[str] = None  # Crate/module name if available


@dataclass
class SizeReport:
    """Binary size analysis report"""
    total_size: int
    text_size: int      # Code
    rodata_size: int    # Read-only data
    data_size: int      # Initialized data
    bss_size: int       # Uninitialized data
    symbols: List[Symbol]
    
    def format_size(self, bytes: int) -> str:
        """Format size in human-readable form"""
        if bytes < 1024:
            return f"{bytes} B"
        elif bytes < 1024 * 1024:
            return f"{bytes / 1024:.1f} KB"
        else:
            return f"{bytes / (1024 * 1024):.1f} MB"


class BinarySizeAnalyzer:
    """Analyze binary size and provide optimization suggestions"""
    
    def __init__(self):
        self.symbols: List[Symbol] = []
    
    def analyze_binary(self, binary_path: Path) -> Optional[SizeReport]:
        """Analyze a binary file"""
        if not binary_path.exists():
            print(f"Error: Binary not found: {binary_path}")
            return None
        
        # Get file size
        total_size = binary_path.stat().st_size
        
        # Try to get section sizes and symbols
        text_size, rodata_size, data_size, bss_size = self._get_section_sizes(binary_path)
        symbols = self._get_symbols(binary_path)
        
        return SizeReport(
            total_size=total_size,
            text_size=text_size,
            rodata_size=rodata_size,
            data_size=data_size,
            bss_size=bss_size,
            symbols=symbols
        )
    
    def _get_section_sizes(self, binary_path: Path) -> Tuple[int, int, int, int]:
        """Get sizes of binary sections"""
        # Try ELF parsing first (Linux, embedded)
        if HAS_ELF:
            try:
                with open(binary_path, 'rb') as f:
                    elf = ELFFile(f)
                    text_size = 0
                    rodata_size = 0
                    data_size = 0
                    bss_size = 0
                    
                    for section in elf.iter_sections():
                        name = section.name
                        size = section.data_size
                        
                        if name == '.text':
                            text_size = size
                        elif name == '.rodata':
                            rodata_size = size
                        elif name == '.data':
                            data_size = size
                        elif name == '.bss':
                            bss_size = size
                    
                    if text_size > 0 or rodata_size > 0 or data_size > 0 or bss_size > 0:
                        return text_size, rodata_size, data_size, bss_size
            except Exception:
                pass
        
        # Try PE parsing (Windows)
        if HAS_PE:
            try:
                pe = pefile.PE(str(binary_path))
                text_size = 0
                rodata_size = 0
                data_size = 0
                bss_size = 0
                
                for section in pe.sections:
                    name = section.Name.decode('utf-8', errors='ignore').rstrip('\x00')
                    size = section.SizeOfRawData
                    characteristics = section.Characteristics
                    
                    # Check section characteristics (PE constants)
                    # IMAGE_SCN_CNT_CODE = 0x00000020
                    # IMAGE_SCN_MEM_READ = 0x40000000
                    # IMAGE_SCN_CNT_INITIALIZED_DATA = 0x00000040
                    is_code = (characteristics & 0x00000020) != 0
                    is_readonly = (characteristics & 0x40000000) != 0
                    is_initialized = (characteristics & 0x00000040) != 0
                    
                    if is_code:
                        text_size += size
                    elif is_readonly and is_initialized:
                        rodata_size += size
                    elif is_initialized:
                        data_size += size
                    else:
                        bss_size += size
                
                if text_size > 0 or rodata_size > 0 or data_size > 0 or bss_size > 0:
                    return text_size, rodata_size, data_size, bss_size
            except Exception:
                pass
        
        # Try Mach-O parsing (macOS)
        if HAS_MACHO:
            try:
                macho = MachO(str(binary_path))
                text_size = 0
                rodata_size = 0
                data_size = 0
                bss_size = 0
                
                for header in macho.headers:
                    for load_command, dylib_command, data in header.commands:
                        # Parse segment commands to get section sizes
                        # Mach-O uses segments (__TEXT, __DATA, __LINKEDIT, etc.)
                        if hasattr(load_command, 'segname'):
                            segname = load_command.segname.decode('utf-8', errors='ignore').rstrip('\x00')
                            segsize = getattr(load_command, 'vmsize', 0)
                            
                            if segname == '__TEXT':
                                text_size += segsize
                            elif segname == '__DATA':
                                data_size += segsize
                            elif segname == '__LINKEDIT':
                                # Link edit is metadata, not code/data
                                pass
                
                if text_size > 0 or data_size > 0:
                    return text_size, rodata_size, data_size, bss_size
            except Exception:
                pass
        
        # Fallback: try using size command (Unix)
        try:
            result = subprocess.run(
                ['size', str(binary_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 3:
                        text = int(parts[0])
                        data = int(parts[1])
                        bss = int(parts[2])
                        return text, 0, data, bss
        except Exception:
            pass
        
        # Final fallback: estimate from total size
        total = binary_path.stat().st_size
        return total, 0, 0, 0
    
    def _get_symbols(self, binary_path: Path) -> List[Symbol]:
        """Get symbol table from binary"""
        symbols = []
        
        # Try ELF parsing first
        if HAS_ELF:
            try:
                with open(binary_path, 'rb') as f:
                    elf = ELFFile(f)
                    
                    # Get symbol tables
                    for section in elf.iter_sections():
                        if isinstance(section, SymbolTableSection):
                            for symbol in section.iter_symbols():
                                # Only include defined symbols with size
                                if symbol['st_size'] > 0 and symbol['st_shndx'] != 'SHN_UNDEF':
                                    symbol_type = 'F' if symbol['st_info']['type'] == 'STT_FUNC' else 'O'
                                    section_name = ''
                                    try:
                                        section_header = elf.get_section(symbol['st_shndx'])
                                        if section_header:
                                            section_name = section_header.name
                                    except:
                                        pass
                                    
                                    # Try to extract crate name from symbol name
                                    crate_name = None
                                    if '::' in symbol.name:
                                        # Rust-style: crate::module::function
                                        parts = symbol.name.split('::')
                                        if len(parts) > 0:
                                            crate_name = parts[0]
                                    
                                    symbols.append(Symbol(
                                        name=symbol.name,
                                        size=symbol['st_size'],
                                        section=section_name,
                                        type=symbol_type,
                                        crate=crate_name
                                    ))
                
                if symbols:
                    return symbols
            except Exception:
                pass
        
        # Try PE parsing (Windows)
        if HAS_PE:
            try:
                pe = pefile.PE(str(binary_path))
                
                # PE files may have symbol tables, but they're often stripped
                # Try to get symbols from export table or debug info
                if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
                    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                        if exp.name:
                            # PE exports don't have size info directly
                            # Estimate size from section or use debug info
                            # For now, skip (would need debug info parsing)
                            pass
                
                # Try to get symbols from debug directory (PDB)
                # This requires more complex parsing
                # For MVP, we'll rely on nm fallback
            except Exception:
                pass
        
        # Fallback: try using nm command (Unix)
        try:
            result = subprocess.run(
                ['nm', '-S', '--size-sort', str(binary_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            size = int(parts[1], 16)
                            symbol_type = parts[2]
                            name = ' '.join(parts[3:])  # Handle names with spaces
                            
                            symbols.append(Symbol(
                                name=name,
                                size=size,
                                section="",
                                type=symbol_type
                            ))
                        except:
                            continue
        except Exception:
            pass
        
        return symbols


# Embedded target flash budgets (in bytes)
EMBEDDED_TARGETS = {
    'stm32f103': 64 * 1024,      # 64 KB
    'stm32f4': 256 * 1024,        # 256 KB
    'stm32f7': 512 * 1024,        # 512 KB
    'arduino-uno': 32 * 1024,     # 32 KB
    'arduino-mega': 256 * 1024,   # 256 KB
    'esp8266': 4 * 1024 * 1024,   # 4 MB
    'esp32': 4 * 1024 * 1024,     # 4 MB
}


def cmd_bloat(
    target: Optional[str] = None,
    compare: Optional[str] = None,
    fail_if_exceeds: Optional[int] = None,
    binary: Optional[str] = None
):
    """Analyze binary size
    
    Args:
        target: Embedded target name (e.g., stm32f4)
        compare: Path to baseline binary for comparison
        fail_if_exceeds: Maximum size in bytes (for CI)
        binary: Path to binary file (default: auto-detect)
    """
    # Find binary
    if binary:
        binary_path = Path(binary)
    else:
        binary_path = Path("target/debug/main")
        if not binary_path.exists():
            binary_path = Path("target/release/main")
    
    if not binary_path.exists():
        print("Error: No binary found. Run 'quarry build' first.")
        return 1
    
    analyzer = BinarySizeAnalyzer()
    report = analyzer.analyze_binary(binary_path)
    
    if not report:
        return 1
    
    # Handle comparison mode
    baseline_report = None
    if compare:
        baseline_path = Path(compare)
        if baseline_path.exists():
            baseline_report = analyzer.analyze_binary(baseline_path)
            if not baseline_report:
                print(f"Warning: Could not analyze baseline binary: {compare}")
        else:
            print(f"Warning: Baseline binary not found: {compare}")
    
    # Determine target and flash budget
    target_name = target or "generic"
    flash_budget = EMBEDDED_TARGETS.get(target_name.lower(), None)
    
    # Display report
    print("Binary Size Analysis")
    print("=" * 60)
    print()
    
    if flash_budget:
        print(f"Target: {target_name.upper()} ({report.format_size(flash_budget)} flash)")
    print(f"Binary: {binary_path}")
    print()
    
    total_used = report.text_size + report.rodata_size + report.data_size + report.bss_size
    if total_used == 0:
        total_used = report.total_size
    
    # Handle comparison
    size_diff = 0
    size_diff_percent = 0.0
    if baseline_report:
        baseline_total = (baseline_report.text_size + baseline_report.rodata_size + 
                         baseline_report.data_size + baseline_report.bss_size)
        if baseline_total == 0:
            baseline_total = baseline_report.total_size
        size_diff = total_used - baseline_total
        if baseline_total > 0:
            size_diff_percent = (size_diff / baseline_total) * 100
    
    print(f"Total: {report.format_size(total_used)}", end="")
    if baseline_report:
        if size_diff > 0:
            print(f" (+{report.format_size(size_diff)}, +{size_diff_percent:.1f}%)", end="")
        elif size_diff < 0:
            print(f" ({report.format_size(size_diff)}, {size_diff_percent:.1f}%)", end="")
        else:
            print(" (no change)", end="")
    if flash_budget:
        percent = (total_used / flash_budget) * 100
        print(f" ({percent:.1f}% of budget)", end="")
        if percent < 80:
            print(" ✓")
        elif percent < 95:
            print(" ⚠️")
        else:
            print(" ✗")
    else:
        print()
    print()
    
    # Section breakdown
    if report.text_size > 0 or report.rodata_size > 0 or report.data_size > 0 or report.bss_size > 0:
        print("Largest Contributors:")
        print()
        print(f"{'Section':<20} {'Size':>12} {'Percent':>8}")
        print("-" * 42)
        
        sections = [
            (".text (code)", report.text_size),
            (".rodata (data)", report.rodata_size),
            (".data (init)", report.data_size),
            (".bss (uninit)", report.bss_size),
        ]
        
        for name, size in sections:
            if size > 0:
                percent = (size / total_used) * 100 if total_used > 0 else 0
                print(f"{name:<20} {report.format_size(size):>12} {percent:>7.1f}%")
        print()
    
    # Top functions
    if report.symbols:
        # Filter to functions only (type 'F' or 'T' for ELF)
        functions = [s for s in report.symbols if s.type in ('F', 'T', 't', 'W', 'w')]
        if not functions:
            # If no type info, assume all are functions
            functions = report.symbols
        
        # Sort by size
        sorted_functions = sorted(functions, key=lambda s: s.size, reverse=True)
        
        if sorted_functions:
            print("Top 10 Functions by Size:")
            print()
            print(f"{'Function':<40} {'Size':>12} {'Percent':>8}")
            print("-" * 62)
            
            for i, symbol in enumerate(sorted_functions[:10], 1):
                percent = (symbol.size / total_used) * 100 if total_used > 0 else 0
                name = symbol.name[:38]  # Truncate long names
                crate_info = f" [{symbol.crate}]" if symbol.crate else ""
                print(f"{i:2}. {name:<38} {report.format_size(symbol.size):>12} {percent:>7.1f}%{crate_info}")
            print()
            
            # Crate attribution summary
            if any(s.crate for s in sorted_functions):
                crate_sizes: Dict[str, int] = {}
                for symbol in sorted_functions:
                    if symbol.crate:
                        crate_sizes[symbol.crate] = crate_sizes.get(symbol.crate, 0) + symbol.size
                
                if crate_sizes:
                    sorted_crates = sorted(crate_sizes.items(), key=lambda x: x[1], reverse=True)
                    print("Size by Crate/Module:")
                    print()
                    print(f"{'Crate':<30} {'Size':>12} {'Percent':>8}")
                    print("-" * 52)
                    for crate, size in sorted_crates[:10]:
                        percent = (size / total_used) * 100 if total_used > 0 else 0
                        print(f"{crate[:28]:<30} {report.format_size(size):>12} {percent:>7.1f}%")
                    print()
    
    # Optimization suggestions
    suggestions = []
    
    if flash_budget and total_used > flash_budget * 0.9:
        suggestions.append(("🔴 CRITICAL", f"Binary exceeds 90% of {target_name} flash budget"))
        suggestions.append(("", "  - Use 'quarry build --release --optimize=size'"))
        suggestions.append(("", "  - Strip debug symbols: 'quarry build --strip-all'"))
        suggestions.append(("", "  - Use minimal panic handler: 'quarry build --minimal-panic'"))
    
    if report.text_size > total_used * 0.8:
        suggestions.append(("⚠️  HIGH", "Code section is very large (>80%)"))
        suggestions.append(("", "  - Enable LTO for cross-module optimization"))
        suggestions.append(("", "  - Check for generic instantiation bloat"))
        suggestions.append(("", "  - Review largest functions above"))
    
    # Check for common bloat sources
    if report.symbols:
        large_functions = [s for s in sorted_functions[:5] if s.size > 2000]
        if large_functions:
            suggestions.append(("⚠️  MEDIUM", f"Found {len(large_functions)} functions >2KB"))
            suggestions.append(("", "  - Review function implementations"))
            suggestions.append(("", "  - Consider splitting large functions"))
        
        # Check for stdlib bloat
        stdlib_functions = [s for s in sorted_functions if 'std::' in s.name or 'fmt::' in s.name]
        if stdlib_functions:
            stdlib_size = sum(s.size for s in stdlib_functions)
            if stdlib_size > total_used * 0.3:
                suggestions.append(("⚠️  MEDIUM", "Standard library is large (>30%)"))
                suggestions.append(("", "  - Use minimal formatting (avoid println! with format strings)"))
                suggestions.append(("", "  - Consider --panic=abort instead of unwinding"))
    
    if report.rodata_size > total_used * 0.2:
        suggestions.append(("⚠️  MEDIUM", "Read-only data section is large (>20%)"))
        suggestions.append(("", "  - Check for large string literals"))
        suggestions.append(("", "  - Consider using minimal formatting"))
    
    # Check for potentially unused code
    # This is a heuristic: if we have many symbols but can't determine references,
    # suggest using --gc-sections
    if report.symbols and len(report.symbols) > 50:
        suggestions.append(("💡 INFO", "Large number of symbols detected"))
        suggestions.append(("", "  - Use 'quarry build --gc-sections' to remove unused code"))
        suggestions.append(("", "  - Compare sizes: 'quarry bloat' vs 'quarry bloat --compare=baseline'"))
        suggestions.append(("", "  - Unused code detection requires linker integration (future feature)"))
    
    if suggestions:
        print("Optimization Suggestions:")
        print()
        for level, msg in suggestions:
            if level:
                print(f"{level} {msg}")
            else:
                print(msg)
        print()
    elif not report.symbols:
        print("Note: Symbol information not available")
        print("  - Install binary parsing libraries for detailed analysis:")
        print("    pip install pyelftools pefile macholib")
        print()
    
    # CI integration: fail if exceeds threshold
    if fail_if_exceeds is not None:
        if total_used > fail_if_exceeds:
            print(f"❌ ERROR: Binary size ({report.format_size(total_used)}) exceeds limit ({report.format_size(fail_if_exceeds)})")
            return 1
        else:
            print(f"✓ Binary size ({report.format_size(total_used)}) within limit ({report.format_size(fail_if_exceeds)})")
    
    return 0


if __name__ == '__main__':
    cmd_bloat()

