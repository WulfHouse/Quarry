#!/usr/bin/env python3
"""Validate documentation links in markdown files.

This script checks for broken internal links in markdown documentation files.
It validates:
- Relative file links (e.g., [text](path/to/file.md))
- Anchor links (e.g., [text](#anchor))
- Cross-references between documentation files

Usage:
    python tools/utils/validate_doc_links.py
    python tools/utils/validate_doc_links.py --fix  # Attempt to fix common issues
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set
from urllib.parse import urlparse


class LinkValidator:
    """Validates links in markdown files."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.errors: List[Tuple[str, str, str]] = []  # (file, link, error)
        self.warnings: List[Tuple[str, str, str]] = []
        self.checked_files: Set[Path] = set()
        
    def find_markdown_files(self) -> List[Path]:
        """Find all markdown files in the repository."""
        markdown_files = []
        exclude_dirs = {'.git', 'node_modules', 'build', 'dist', '.venv', 'venv', '__pycache__'}
        
        for path in self.root_dir.rglob('*.md'):
            # Skip files in excluded directories
            if any(excluded in path.parts for excluded in exclude_dirs):
                continue
            markdown_files.append(path)
            
        return sorted(markdown_files)
    
    def extract_links(self, content: str, file_path: Path) -> List[Tuple[str, int]]:
        """Extract all markdown links from content.
        
        Returns:
            List of (link_url, line_number) tuples
        """
        links = []
        lines = content.split('\n')
        in_code_block = False
        code_block_marker = None
        
        # Pattern for markdown links: [text](url)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        for line_num, line in enumerate(lines, 1):
            # Track code blocks (fenced and indented)
            stripped = line.strip()
            
            # Check for fenced code blocks (``` or ~~~)
            if stripped.startswith('```') or stripped.startswith('~~~'):
                if in_code_block and (code_block_marker is None or stripped.startswith(code_block_marker)):
                    in_code_block = False
                    code_block_marker = None
                else:
                    in_code_block = True
                    # Extract language identifier if present
                    marker = stripped[:3]
                    code_block_marker = marker
                continue
            
            # Check for indented code blocks (4+ spaces or tab)
            if not in_code_block and (line.startswith('    ') or line.startswith('\t')):
                # Could be code, but we'll be conservative and still check
                pass
            
            # Skip links inside code blocks
            if in_code_block:
                continue
            
            # Skip inline code (backticks)
            # Simple heuristic: if line has backticks, skip links that are inside them
            for match in re.finditer(link_pattern, line):
                link_url = match.group(2)
                
                # Skip external URLs
                parsed = urlparse(link_url)
                if parsed.scheme or link_url.startswith('//'):
                    continue
                
                # Skip if link looks like code (contains common code patterns)
                if any(pattern in link_url for pattern in ['[', ']', '(', ')', '.len(', '.append(']):
                    # Check if it's actually in a code context
                    link_start = match.start()
                    # Look for backticks before the link
                    before_link = line[:link_start]
                    if before_link.count('`') % 2 == 1:  # Odd number means we're inside code
                        continue
                
                links.append((link_url, line_num))
        
        return links
    
    def resolve_link(self, link: str, from_file: Path) -> Path:
        """Resolve a relative link to an absolute path."""
        # Remove anchor if present
        if '#' in link:
            link = link.split('#')[0]
        
        if not link:
            return None
        
        # Resolve relative to the file's directory
        if link.startswith('/'):
            # Absolute from repo root
            return self.root_dir / link.lstrip('/')
        else:
            # Relative to current file
            return (from_file.parent / link).resolve()
    
    def file_exists(self, path: Path) -> bool:
        """Check if a file exists."""
        if path is None:
            return False
        try:
            return path.exists() and path.is_file()
        except (OSError, ValueError):
            return False
    
    def check_anchor(self, link: str, target_file: Path) -> bool:
        """Check if an anchor exists in the target file."""
        if '#' not in link:
            return True  # No anchor to check
        
        anchor = link.split('#')[1]
        
        if not target_file.exists():
            return False
        
        try:
            content = target_file.read_text(encoding='utf-8')
            
            # Check for markdown headers (anchors are usually generated from headers)
            # Pattern: # Header Name -> anchor is usually "header-name"
            header_pattern = r'^#+\s+(.+)$'
            anchors = set()
            
            for line in content.split('\n'):
                match = re.match(header_pattern, line)
                if match:
                    header_text = match.group(1).strip()
                    # Generate anchor (simplified - markdown processors may differ)
                    anchor_candidate = header_text.lower().replace(' ', '-').replace('_', '-')
                    # Remove special characters
                    anchor_candidate = re.sub(r'[^\w-]', '', anchor_candidate)
                    anchors.add(anchor_candidate)
                    # Also check exact match
                    anchors.add(header_text.lower().replace(' ', '-'))
            
            # Check if anchor matches (exact or simplified)
            anchor_normalized = anchor.lower().replace('_', '-')
            return anchor_normalized in anchors or anchor in anchors
            
        except Exception:
            return False
    
    def validate_file(self, file_path: Path):
        """Validate all links in a markdown file."""
        if file_path in self.checked_files:
            return
        self.checked_files.add(file_path)
        
        try:
            content = file_path.read_text(encoding='utf-8')
            links = self.extract_links(content, file_path)
            
            for link, line_num in links:
                target_path = self.resolve_link(link, file_path)
                
                # Check if file exists
                if not self.file_exists(target_path):
                    # Check if it's an anchor-only link (same file)
                    if link.startswith('#') and '#' not in link:
                        # Anchor in same file
                        if not self.check_anchor(link, file_path):
                            self.errors.append((
                                str(file_path.relative_to(self.root_dir)),
                                link,
                                f"Line {line_num}: Anchor '{link}' not found"
                            ))
                    else:
                        self.errors.append((
                            str(file_path.relative_to(self.root_dir)),
                            link,
                            f"Line {line_num}: File not found: {target_path.relative_to(self.root_dir) if target_path else 'None'}"
                        ))
                else:
                    # File exists, check anchor if present
                    if '#' in link:
                        anchor = link.split('#')[1]
                        if not self.check_anchor(link, target_path):
                            self.warnings.append((
                                str(file_path.relative_to(self.root_dir)),
                                link,
                                f"Line {line_num}: Anchor '{anchor}' may not exist in target file"
                            ))
        
        except Exception as e:
            self.errors.append((
                str(file_path.relative_to(self.root_dir)),
                "",
                f"Error reading file: {e}"
            ))
    
    def validate_all(self) -> bool:
        """Validate all markdown files.
        
        Returns:
            True if no errors found, False otherwise
        """
        markdown_files = self.find_markdown_files()
        
        print(f"Found {len(markdown_files)} markdown files")
        print("Validating links...")
        
        for file_path in markdown_files:
            self.validate_file(file_path)
        
        return len(self.errors) == 0
    
    def print_report(self):
        """Print validation report."""
        if self.errors:
            print(f"\n[ERROR] Found {len(self.errors)} broken links:\n")
            for file, link, error in self.errors:
                print(f"  {file}")
                print(f"    Link: {link}")
                print(f"    Error: {error}\n")
        
        if self.warnings:
            print(f"\n[WARNING] Found {len(self.warnings)} potential issues:\n")
            for file, link, warning in self.warnings:
                print(f"  {file}")
                print(f"    Link: {link}")
                print(f"    Warning: {warning}\n")
        
        if not self.errors and not self.warnings:
            print("\n[SUCCESS] All links are valid!")
        elif not self.errors:
            print(f"\n[SUCCESS] No broken links found (but {len(self.warnings)} warnings)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate documentation links in markdown files"
    )
    parser.add_argument(
        '--root',
        type=Path,
        default=Path(__file__).parent.parent.parent,
        help='Root directory to search (default: repository root)'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to fix common issues (not implemented yet)'
    )
    
    args = parser.parse_args()
    
    validator = LinkValidator(args.root)
    success = validator.validate_all()
    validator.print_report()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
