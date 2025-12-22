#!/usr/bin/env bash
# Pyrite Language Installer for Unix (macOS, Linux)
# Usage: curl -sSf https://get.pyrite-lang.org | sh
#        or: bash install.sh

set -e

PYRITE_VERSION="${PYRITE_VERSION:-latest}"
INSTALL_DIR="${PYRITE_INSTALL_DIR:-$HOME/.pyrite}"
BIN_DIR="$INSTALL_DIR/bin"
REPO_URL="https://github.com/wulfhq/pyrite/archive/refs/heads/main.tar.gz"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[pyrite]${NC} $1"; }
warn() { echo -e "${YELLOW}[pyrite]${NC} $1"; }
error() { echo -e "${RED}[pyrite]${NC} $1" >&2; exit 1; }
info() { echo -e "${BLUE}[pyrite]${NC} $1"; }

# Detect OS and Architecture
detect_platform() {
    local os=$(uname -s | tr '[:upper:]' '[:lower:]')
    local arch=$(uname -m)
    
    case "$os" in
        linux*)   os="linux" ;;
        darwin*)  os="macos" ;;
        *)        error "Unsupported OS: $os" ;;
    esac
    
    case "$arch" in
        x86_64|amd64)  arch="x86_64" ;;
        aarch64|arm64) arch="aarch64" ;;
        *)             error "Unsupported architecture: $arch" ;;
    esac
    
    echo "${os}-${arch}"
}

# Check for Python 3.10+
check_python() {
    info "Checking for Python 3.10+..."
    
    if command -v python3 &> /dev/null; then
        local version=$(python3 --version 2>&1 | cut -d' ' -f2)
        local major=$(echo $version | cut -d'.' -f1)
        local minor=$(echo $version | cut -d'.' -f2)
        
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            log "Found Python $version ✓"
            PYTHON_CMD="python3"
            return 0
        else
            warn "Found Python $version, but 3.10+ is required"
        fi
    fi
    
    warn "Python 3.10+ not found. Installing..."
    install_python
}

# Install Python (platform-specific)
install_python() {
    case "$PLATFORM" in
        linux-*)
            if command -v apt-get &> /dev/null; then
                log "Installing Python via apt..."
                sudo apt-get update -qq
                sudo apt-get install -y python3.10 python3-pip python3.10-venv
            elif command -v dnf &> /dev/null; then
                log "Installing Python via dnf..."
                sudo dnf install -y python3.10 python3-pip
            elif command -v pacman &> /dev/null; then
                log "Installing Python via pacman..."
                sudo pacman -S --noconfirm python python-pip
            else
                error "Cannot auto-install Python. Please install Python 3.10+ manually and re-run this script."
            fi
            ;;
        macos-*)
            if command -v brew &> /dev/null; then
                log "Installing Python via Homebrew..."
                brew install python@3.10
            else
                error "Homebrew not found. Please install Homebrew (https://brew.sh) or install Python 3.10+ manually."
            fi
            ;;
    esac
    
    PYTHON_CMD="python3"
    
    # Verify installation
    if ! command -v python3 &> /dev/null; then
        error "Python installation failed. Please install Python 3.10+ manually."
    fi
}

# Check for LLVM
check_llvm() {
    info "Checking for LLVM..."
    
    # First check if llvmlite Python package is installed (easier option)
    if $PYTHON_CMD -c "import llvmlite" 2>/dev/null; then
        log "Found llvmlite Python package ✓"
        return 0
    fi
    
    # Check for system LLVM
    if command -v llvm-config &> /dev/null; then
        local version=$(llvm-config --version 2>/dev/null | cut -d'.' -f1)
        if [ "$version" -ge 15 ] 2>/dev/null; then
            log "Found LLVM $version ✓"
            return 0
        fi
    fi
    
    warn "LLVM not found. Will install via Python package (llvmlite)..."
    # We'll install it via pip along with other Python dependencies
}

# Check for C compiler
check_compiler() {
    info "Checking for C compiler..."
    
    if command -v gcc &> /dev/null; then
        local gcc_version=$(gcc --version | head -n1)
        log "Found GCC ✓ ($gcc_version)"
        return 0
    elif command -v clang &> /dev/null; then
        local clang_version=$(clang --version | head -n1)
        log "Found Clang ✓ ($clang_version)"
        return 0
    fi
    
    warn "C compiler not found. Installing..."
    install_compiler
}

# Install C compiler (platform-specific)
install_compiler() {
    case "$PLATFORM" in
        linux-*)
            if command -v apt-get &> /dev/null; then
                log "Installing GCC via apt..."
                sudo apt-get install -y build-essential
            elif command -v dnf &> /dev/null; then
                log "Installing GCC via dnf..."
                sudo dnf groupinstall -y "Development Tools"
            elif command -v pacman &> /dev/null; then
                log "Installing GCC via pacman..."
                sudo pacman -S --noconfirm base-devel
            else
                error "Cannot auto-install C compiler. Please install GCC or Clang manually."
            fi
            ;;
        macos-*)
            log "Installing Xcode Command Line Tools..."
            if ! xcode-select -p &> /dev/null; then
                xcode-select --install
                warn "Please complete the Xcode Command Line Tools installation and re-run this script."
                exit 1
            else
                log "Xcode Command Line Tools already installed ✓"
            fi
            ;;
    esac
}

# Download and install Pyrite
install_pyrite() {
    log "Downloading Pyrite ${PYRITE_VERSION}..."
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Download release (using GitHub for now)
    local temp_file="/tmp/pyrite-${PYRITE_VERSION}.tar.gz"
    if command -v curl &> /dev/null; then
        curl -sSL "$REPO_URL" -o "$temp_file"
    elif command -v wget &> /dev/null; then
        wget -q "$REPO_URL" -O "$temp_file"
    else
        error "Neither curl nor wget found. Please install one of them."
    fi
    
    # Extract
    log "Extracting Pyrite..."
    tar xzf "$temp_file" --strip-components=1
    rm -f "$temp_file"
    
    # Install Python dependencies
    log "Installing Python dependencies..."
    cd forge
    if [ -f "requirements.txt" ]; then
        $PYTHON_CMD -m pip install --user -r requirements.txt --quiet
    else
        # Try root directory
        cd ..
        if [ -f "requirements.txt" ]; then
            $PYTHON_CMD -m pip install --user -r requirements.txt --quiet
        fi
    fi
    cd ..
    
    # Build runtime libraries
    log "Building runtime libraries..."
    cd ..
    $PYTHON_CMD tools/build/build_runtime.py
    
    # Create wrapper scripts
    log "Creating wrapper scripts..."
    mkdir -p "$BIN_DIR"
    
    # pyrite wrapper
    cat > "$BIN_DIR/pyrite" << 'EOF'
#!/usr/bin/env bash
PYRITE_HOME="${PYRITE_HOME:-$HOME/.pyrite}"
exec python3 "$PYRITE_HOME/tools/pyrite_run.py" "$@"
EOF
    chmod +x "$BIN_DIR/pyrite"
    
    # quarry wrapper
    cat > "$BIN_DIR/quarry" << 'EOF'
#!/usr/bin/env bash
PYRITE_HOME="${PYRITE_HOME:-$HOME/.pyrite}"
exec python3 "$PYRITE_HOME/quarry/main.py" "$@"
EOF
    chmod +x "$BIN_DIR/quarry"
}

# Update PATH
update_path() {
    log "Updating PATH..."
    
    local shell_rc=""
    case "$SHELL" in
        */bash) shell_rc="$HOME/.bashrc" ;;
        */zsh)  shell_rc="$HOME/.zshrc" ;;
        */fish) shell_rc="$HOME/.config/fish/config.fish" ;;
        *)      shell_rc="$HOME/.profile" ;;
    esac
    
    # Check if already in PATH
    if grep -q "\.pyrite/bin" "$shell_rc" 2>/dev/null; then
        log "PATH already configured ✓"
    else
        log "Adding Pyrite to PATH in $shell_rc"
        echo "" >> "$shell_rc"
        echo "# Pyrite Language" >> "$shell_rc"
        echo "export PATH=\"$BIN_DIR:\$PATH\"" >> "$shell_rc"
    fi
    
    # Update current session
    export PATH="$BIN_DIR:$PATH"
}

# Verify installation
verify_install() {
    log "Verifying installation..."
    
    # Create test file
    local test_file="/tmp/test_pyrite_${RANDOM}.pyrite"
    cat > "$test_file" << 'EOF'
fn main():
    print("Hello, Pyrite!")
EOF
    
    # Test compilation
    if "$BIN_DIR/pyrite" "$test_file" > /dev/null 2>&1; then
        log "Installation successful! ✓"
        rm -f "$test_file"
        return 0
    else
        error "Installation verification failed. Please check the logs above for errors."
    fi
}

# Main installation flow
main() {
    echo ""
    log "╔════════════════════════════════════╗"
    log "║   Pyrite Language Installer       ║"
    log "║   Memory-safe systems programming ║"
    log "╚════════════════════════════════════╝"
    echo ""
    
    # Detect platform
    PLATFORM=$(detect_platform)
    info "Platform: $PLATFORM"
    echo ""
    
    # Check dependencies
    check_python
    check_llvm
    check_compiler
    echo ""
    
    # Install Pyrite
    install_pyrite
    echo ""
    
    # Update PATH
    update_path
    echo ""
    
    # Verify
    verify_install
    echo ""
    
    # Success message
    log "═══════════════════════════════════════════════════════"
    log "✨ Pyrite installed successfully! ✨"
    log "═══════════════════════════════════════════════════════"
    echo ""
    log "Get started:"
    log "  $ source ~/.bashrc           # Reload shell config"
    log "  $ pyrite hello.pyrite        # Run a Pyrite file"
    log "  $ quarry new myproject       # Create new project"
    echo ""
    log "Learn more:"
    log "  • Documentation: https://pyrite-lang.org/docs"
    log "  • Examples: ~/.pyrite/forge/examples/"
    echo ""
}

main

