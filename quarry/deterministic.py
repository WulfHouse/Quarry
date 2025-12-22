"""Deterministic builds for Pyrite - bit-for-bit reproducibility"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict

# Try to import TOML libraries (optional)
try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    HAS_TOMLLIB = False

try:
    import tomli_w
    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False


@dataclass
class BuildManifest:
    """Manifest for reproducible builds"""
    build_hash: str
    timestamp: str
    compiler_version: str
    target: str
    build_flags: List[str]
    source_files: Dict[str, Dict[str, any]]  # path -> {hash, size}
    dependencies: Dict[str, Dict[str, str]]  # name -> {version, hash}
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BuildManifest':
        return cls(**data)


class DeterministicBuilder:
    """Build with deterministic output"""
    
    def __init__(self):
        # Get SOURCE_DATE_EPOCH from environment or use default
        source_date_epoch_str = os.environ.get('SOURCE_DATE_EPOCH')
        if source_date_epoch_str:
            try:
                self.source_date_epoch = int(source_date_epoch_str)
            except ValueError:
                self.source_date_epoch = 1640000000  # Default: 2021-12-20
        else:
            self.source_date_epoch = 1640000000
        
        # Set Python hash seed for deterministic dict ordering
        # Use SOURCE_DATE_EPOCH as seed if not already set
        if 'PYTHONHASHSEED' not in os.environ:
            os.environ['PYTHONHASHSEED'] = str(self.source_date_epoch % (2**32))
        
        # Set deterministic mode flags
        self._setup_deterministic_environment()
    
    def _setup_deterministic_environment(self):
        """Setup environment for deterministic builds"""
        # Set timezone to UTC for consistent timestamps
        os.environ['TZ'] = 'UTC'
        if hasattr(time, 'tzset'):
            time.tzset()
        
        # Set LLVM deterministic flags via environment
        # LLVM will use these when available
        os.environ['LLVM_DETERMINISTIC'] = '1'
    
    def compute_binary_hash(self, binary_path: Path) -> str:
        """Compute SHA-256 hash of binary"""
        hasher = hashlib.sha256()
        
        with open(binary_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def hash_file(self, file_path: Path) -> str:
        """Compute SHA-256 hash of a file"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def find_all_source_files(self, root: Path) -> List[Path]:
        """Find all .pyrite source files in a directory"""
        source_files = []
        if root.is_dir():
            for pyrite_file in root.rglob("*.pyrite"):
                source_files.append(pyrite_file)
        elif root.exists() and root.suffix == ".pyrite":
            source_files.append(root)
        return sorted(source_files)  # Sort for deterministic order
    
    def generate_manifest(self, binary_path: Path, source_files: List[Path], 
                         compiler_version: str = "2.0.0", 
                         build_flags: Optional[List[str]] = None) -> BuildManifest:
        """Generate build manifest"""
        # Compute binary hash
        binary_hash = self.compute_binary_hash(binary_path)
        
        # Compute source file hashes (sorted for deterministic order)
        source_info = {}
        for source_file in sorted(source_files):
            if source_file.exists():
                file_hash = self.hash_file(source_file)
                source_info[str(source_file)] = {
                    'hash': file_hash,
                    'size': source_file.stat().st_size
                }
        
        # Use SOURCE_DATE_EPOCH for timestamp
        build_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", 
                                       time.gmtime(self.source_date_epoch))
        
        manifest = BuildManifest(
            build_hash=binary_hash,
            timestamp=build_timestamp,
            compiler_version=compiler_version,
            target="native",
            build_flags=build_flags or ["--deterministic"],
            source_files=source_info,
            dependencies={}
        )
        
        return manifest
    
    def verify_build(self, binary_path: Path, manifest_path: Path) -> bool:
        """Verify binary matches manifest"""
        if not manifest_path.exists():
            print(f"Error: Manifest not found: {manifest_path}")
            return False
        
        # Load manifest (support both TOML and JSON)
        try:
            manifest_text = manifest_path.read_text()
            # Try TOML first if available
            if HAS_TOMLLIB and manifest_path.suffix == '.toml':
                try:
                    manifest_data = tomllib.loads(manifest_text)
                    # Convert TOML structure to BuildManifest format
                    build_data = manifest_data.get('build', {})
                    manifest = BuildManifest(
                        build_hash=build_data.get('hash', ''),
                        timestamp=build_data.get('timestamp', ''),
                        compiler_version=build_data.get('compiler_version', ''),
                        target=build_data.get('target', 'native'),
                        build_flags=build_data.get('flags', []),
                        source_files=manifest_data.get('sources', {}),
                        dependencies=manifest_data.get('dependencies', {})
                    )
                except Exception:
                    # Fall back to JSON
                    manifest_data = json.loads(manifest_text)
                    manifest = BuildManifest.from_dict(manifest_data)
            else:
                # Use JSON
                manifest_data = json.loads(manifest_text)
                manifest = BuildManifest.from_dict(manifest_data)
        except Exception as e:
            print(f"Error loading manifest: {e}")
            return False
        
        # Compute current binary hash
        current_hash = self.compute_binary_hash(binary_path)
        
        print("Verifying build...")
        print(f"  Expected hash: {manifest.build_hash}")
        print(f"  Current hash:  {current_hash}")
        
        if current_hash == manifest.build_hash:
            print("\n✓ VERIFIED: Binary is reproducible")
            return True
        else:
            print("\n✗ MISMATCH: Binary differs from manifest")
            return False


def cmd_build_deterministic():
    """Build with deterministic output (legacy - use 'quarry build --deterministic')"""
    # Redirect to main build command
    from quarry.main import cmd_build
    return cmd_build(release=True, deterministic=True)


def cmd_verify_build(binary_path: Optional[str] = None, manifest_path: Optional[str] = None):
    """Verify build is reproducible"""
    # Default paths
    if binary_path is None:
        # Try debug first, then release
        if Path("target/debug/main").exists():
            binary_path = "target/debug/main"
        elif Path("target/release/main").exists():
            binary_path = "target/release/main"
        else:
            print("Error: Binary not found. Run 'quarry build --deterministic' first.")
            return 1
    
    if manifest_path is None:
        # Try JSON first (what we generate), then TOML
        if Path("BuildManifest.json").exists():
            manifest_path = "BuildManifest.json"
        elif Path("BuildManifest.toml").exists():
            manifest_path = "BuildManifest.toml"
        else:
            print("Error: Manifest not found. Run 'quarry build --deterministic' first.")
            return 1
    
    binary = Path(binary_path)
    manifest = Path(manifest_path)
    
    if not binary.exists():
        print(f"Error: Binary not found: {binary}")
        return 1
    
    builder = DeterministicBuilder()
    verified = builder.verify_build(binary, manifest)
    
    return 0 if verified else 1


if __name__ == '__main__':
    import sys
    if '--verify' in sys.argv:
        cmd_verify_build()
    else:
        cmd_build_deterministic()

