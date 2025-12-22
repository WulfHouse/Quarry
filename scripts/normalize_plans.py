#!/usr/bin/env python3
"""Normalize plan file names to kebab-case."""
import os
import shutil
from pathlib import Path

def to_kebab_case(name):
    """Convert UPPER_SNAKE_CASE or PascalCase to kebab-case."""
    # Remove .md extension
    base, ext = os.path.splitext(name)
    # Convert to lowercase and replace underscores/hyphens with hyphens
    kebab = base.lower().replace('_', '-')
    # Remove duplicate hyphens
    while '--' in kebab:
        kebab = kebab.replace('--', '-')
    return f"{kebab}{ext}"

# Files to normalize (top-level plans that are UPPER_SNAKE_CASE)
files_to_normalize = [
    'plans/AI_AGENT_TRAVERSAL_OPTIMIZATION.md',
    'plans/CANCELLATION_PREVENTION.md',
    'plans/CURSOR_RULES_OPTIMIZATION.md',
    'plans/LANGUAGE_COMPLETENESS_PORTING_PLAN.md',
    'plans/ORGANIZATION_OPPORTUNITIES.md',
    'plans/POST_HARDENING_ROADMAP.md',
    'plans/POST_SELF_HOSTING_HARDENING.md',
    'plans/REPL_DECOUPLING_PROMPT.md',
    'plans/SSOT_MODULARIZATION.md',
]

moved = []
for file_path in files_to_normalize:
    src = Path(file_path)
    if src.exists():
        new_name = to_kebab_case(src.name)
        dst = src.parent / new_name
        if src != dst:
            shutil.move(str(src), str(dst))
            moved.append((file_path, str(dst)))
            print(f"Renamed: {src.name} -> {new_name}")

print(f"\nTotal files renamed: {len(moved)}")
