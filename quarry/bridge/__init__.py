"""Quarry bridge modules.

This package contains bridge modules that provide FFI bindings to Pyrite-compiled
standard library modules. These bridges enable Quarry to use Pyrite implementations
of core utilities like TOML parsing, version handling, path utilities, etc.

Modules:
    ast_bridge: AST bridge for Pyrite-compiled code
    build_graph_bridge: Build graph bridge
    dep_fingerprint_bridge: Dependency fingerprinting bridge
    dep_source_bridge: Dependency source tracking bridge
    locked_validate_bridge: Locked validation bridge
    lockfile_bridge: Lockfile handling bridge
    path_utils_bridge: Path utilities bridge
    resolve_bridge: Dependency resolution bridge
    toml_bridge: TOML parsing bridge
    version_bridge: Version handling bridge

See Also:
    src.bridge: Compiler bridge modules
    stdlib: Standard library modules (Pyrite implementations)
"""

# Re-export all bridge modules
from .build_graph_bridge import *
from .dep_fingerprint_bridge import *
from .dep_source_bridge import *
from .locked_validate_bridge import *
from .lockfile_bridge import *
from .path_utils_bridge import *
from .resolve_bridge import *
from .toml_bridge import *
from .version_bridge import *

__all__ = [
    'build_graph_bridge', 'dep_fingerprint_bridge',
    'dep_source_bridge', 'locked_validate_bridge', 'lockfile_bridge',
    'path_utils_bridge', 'resolve_bridge', 'toml_bridge', 'version_bridge'
]
