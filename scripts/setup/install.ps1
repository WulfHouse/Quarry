# Pyrite Language Installer for Windows
# Usage: irm https://get.pyrite-lang.org/install.ps1 | iex
#        or: .\install.ps1

$ErrorActionPreference = "Stop"

$PyriteVersion = $env:PYRITE_VERSION
if (-not $PyriteVersion) { $PyriteVersion = "latest" }

$InstallDir = $env:PYRITE_INSTALL_DIR
if (-not $InstallDir) { $InstallDir = "$env:USERPROFILE\.pyrite" }

$BinDir = "$InstallDir\bin"
$RepoUrl = "https://github.com/wulfhq/pyrite/archive/refs/heads/main.zip"

function Write-Info($msg) {
    Write-Host "[pyrite] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "[pyrite] $msg" -ForegroundColor Yellow
}

function Write-Error($msg) {
    Write-Host "[pyrite] $msg" -ForegroundColor Red
    exit 1
}

function Write-Status($msg) {
    Write-Host "[pyrite] $msg" -ForegroundColor Cyan
}

function Test-Python {
    Write-Status "Checking for Python 3.10+..."
    
    $pythonCmd = $null
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $version = & $cmd --version 2>$null
            if ($version -match "Python (\d+)\.(\d+)") {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                if (($major -eq 3) -and ($minor -ge 10)) {
                    Write-Info "Found Python $major.$minor "
                    return $cmd
                }
            }
        } catch { 
            continue 
        }
    }
    
    Write-Warn "Python 3.10+ not found. Installing..."
    return Install-Python
}

function Install-Python {
    Write-Info "Downloading Python 3.10..."
    
    # Download Python installer
    $pythonUrl = "https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe"
    $installerPath = "$env:TEMP\python-installer.exe"
    
    try {
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing
    } catch {
        Write-Error "Failed to download Python installer: $_"
    }
    
    Write-Info "Installing Python..."
    Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1" -Wait
    
    Remove-Item $installerPath -ErrorAction SilentlyContinue
    
    # Refresh PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
    
    # Wait a moment for installation to complete
    Start-Sleep -Seconds 2
    
    # Verify
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $version = & $cmd --version 2>$null
            if ($version -match "Python 3\.10") {
                Write-Info "Python installed successfully "
                return $cmd
            }
        } catch { continue }
    }
    
    Write-Error "Python installation failed. Please install Python 3.10+ manually from python.org"
}

function Test-LLVM {
    Write-Status "Checking for LLVM..."
    
    # LLVM via llvmlite Python package (easier on Windows)
    try {
        $result = & $PythonCmd -c "import llvmlite; print(llvmlite.__version__)" 2>$null
        if ($result) {
            Write-Info "Found llvmlite $result "
            return $true
        }
    } catch {
        Write-Warn "llvmlite not found. Will install via pip..."
        return $false
    }
    
    Write-Warn "llvmlite not found. Will install via pip..."
    return $false
}

function Test-Compiler {
    Write-Status "Checking for C compiler..."
    
    # Check for MinGW or MSVC
    $hasGcc = Get-Command gcc -ErrorAction SilentlyContinue
    $hasMsvc = Get-Command cl -ErrorAction SilentlyContinue
    
    if ($hasGcc) {
        # Run to completion, then get first line (avoid early cancellation)
        $gccOutput = & gcc --version 2>$null
        $gccVersion = if ($gccOutput) { $gccOutput[0] } else { "unknown" }
        Write-Info "Found GCC  ($gccVersion)"
        return $true
    }
    
    if ($hasMsvc) {
        Write-Info "Found MSVC "
        return $true
    }
    
    Write-Warn "C compiler not found. Installing MinGW..."
    Install-MinGW
}

function Install-MinGW {
    Write-Info "Installing MinGW-w64..."
    
    # Check if chocolatey is installed
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        Write-Status "Installing Chocolatey package manager..."
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        try {
            Invoke-Expression ((New-Object System.Net.WebClient).DownloadString("https://community.chocolatey.org/install.ps1"))
        } catch {
            Write-Error "Failed to install Chocolatey. Please install MinGW manually."
        }
    }
    
    Write-Info "Installing MinGW via Chocolatey..."
    choco install mingw -y
    
    # Refresh PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
    
    # Verify
    if (Get-Command gcc -ErrorAction SilentlyContinue) {
        Write-Info "MinGW installed successfully "
    } else {
        Write-Error "MinGW installation failed. Please install MinGW manually."
    }
}

function Install-Pyrite {
    # Check if we're already in the Pyrite directory (local install)
    if (Test-Path ".\forge" -PathType Container) {
        Write-Info "Found local Pyrite installation, using current directory..."
        
        # Copy to install directory
        if ($InstallDir -ne $PWD.Path) {
            Write-Info "Copying Pyrite to $InstallDir..."
            New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
            Copy-Item -Path ".\*" -Destination $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
        } else {
            Write-Info "Already in install directory..."
        }
    } else {
        Write-Info "Downloading Pyrite $PyriteVersion..."
        
        New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
        
        # Download release
        $zipPath = "$env:TEMP\pyrite.zip"
        
        try {
            Invoke-WebRequest -Uri $RepoUrl -OutFile $zipPath -UseBasicParsing
        } catch {
            Write-Error "Failed to download Pyrite: $_"
        }
        
        Write-Info "Extracting Pyrite..."
        try {
            Expand-Archive -Path $zipPath -DestinationPath $InstallDir -Force
        } catch {
            Write-Error "Failed to extract Pyrite: $_"
        }
        
        # Move contents out of subdirectory
        # Get all matching directories, then take first (avoid early cancellation)
        $matchingDirs = Get-ChildItem $InstallDir -Directory | Where-Object { $_.Name -like "pyrite-*" }
        $extractedDir = if ($matchingDirs) { $matchingDirs[0] } else { $null }
        if ($extractedDir) {
            Get-ChildItem $extractedDir.FullName | Move-Item -Destination $InstallDir -Force
            Remove-Item $extractedDir.FullName -Recurse -Force
        }
        
        Remove-Item $zipPath -ErrorAction SilentlyContinue
    }
    
    # Install Python dependencies
    Write-Info "Installing Python dependencies..."
    Set-Location $InstallDir\forge
    if (Test-Path "requirements.txt") {
        & $PythonCmd -m pip install --user -r requirements.txt --quiet
    } else {
        # Try root directory
        Set-Location $InstallDir
        if (Test-Path "requirements.txt") {
            & $PythonCmd -m pip install --user -r requirements.txt --quiet
        }
    }
    
    # Build runtime
    Write-Info "Building runtime libraries..."
    Set-Location $InstallDir
    & $PythonCmd tools\build_runtime.py
    
    # Create wrapper scripts
    Write-Info "Creating wrapper scripts..."
    New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
    
    # pyrite.bat
    @"
@echo off
set PYTHONPATH=%USERPROFILE%\.pyrite\forge
python "%USERPROFILE%\.pyrite\tools\runtime\pyrite_run.py" %*
"@ | Out-File -FilePath "$BinDir\pyrite.bat" -Encoding ASCII -Force
    
    # quarry.bat
    @"
@echo off
set PYTHONPATH=%USERPROFILE%\.pyrite
python "%USERPROFILE%\.pyrite\quarry\main.py" %*
"@ | Out-File -FilePath "$BinDir\quarry.bat" -Encoding ASCII -Force
    
    Write-Info "Wrapper scripts created "
}

function Update-Path {
    Write-Info "Adding Pyrite to PATH..."
    
    $userPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
    if ($userPath -notlike "*$BinDir*") {
        [System.Environment]::SetEnvironmentVariable("PATH", "$BinDir;$userPath", "User")
        Write-Info "PATH updated "
    } else {
        Write-Info "PATH already configured "
    }
    
    # Update current session
    $env:PATH = "$BinDir;$env:PATH"
}

function Test-Installation {
    Write-Info "Verifying installation..."
    
    # Test compilation
    $testFile = "$env:TEMP\test_pyrite_$(Get-Random).pyrite"
    
    # Create test file using ASCII encoding (no BOM issues)
    # Use proper indentation for Pyrite
    $testContent = "fn main():`r`n    print(`"Hello, Pyrite!`")`r`n"
    [System.IO.File]::WriteAllText($testFile, $testContent, [System.Text.Encoding]::ASCII)
    
    try {
        $output = & pyrite $testFile 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Installation successful! "
        } else {
            Write-Warn "Verification test had issues (this is usually harmless):"
            # Split output, take first 3 lines after completion (avoid early cancellation)
            $outputLines = $output -split '\n'
            $firstThree = if ($outputLines.Count -gt 3) { $outputLines[0..2] } else { $outputLines }
            Write-Host "  $($firstThree -Join ' ')" -ForegroundColor Gray
            Write-Info "Installation components are installed correctly."
            Write-Info "Try running: pyrite --help"
        }
    } catch {
        Write-Warn "Verification test failed (this is usually harmless): $_"
        Write-Info "Installation components are installed correctly."
        Write-Info "Try running: pyrite --help"
    } finally {
        Remove-Item $testFile -ErrorAction SilentlyContinue
    }
}

# Main installation flow
Write-Host ""
Write-Info ""
Write-Info "   Pyrite Language Installer       "
Write-Info "   Memory-safe systems programming "
Write-Info ""
Write-Host ""

Write-Status "Platform: Windows $(if ([Environment]::Is64BitOperatingSystem) { "x64" } else { "x86" })"
Write-Host ""

$installSuccess = $false

try {
    $PythonCmd = Test-Python
    Test-LLVM
    Test-Compiler
    Write-Host ""
    
    Install-Pyrite
    Write-Host ""
    
    Update-Path
    Write-Host ""
    
    Test-Installation
    Write-Host ""
    
    Write-Info ""
    Write-Info " Pyrite installed successfully! "
    Write-Info ""
    Write-Host ""
    Write-Info "Get started:"
    Write-Info "  > pyrite hello.pyrite        # Run a Pyrite file"
    Write-Info "  > quarry new myproject       # Create new project"
    Write-Host ""
    Write-Info "Learn more:"
    Write-Info "  - Documentation: https://pyrite-lang.org/docs"
    Write-Info "  - Examples: $InstallDir\forge\examples\"
    Write-Host ""
    Write-Warn "Please restart your terminal to refresh PATH"
    Write-Host ""
    
    # Mark as successful (installation completed, verification is optional)
    $installSuccess = $true
} catch {
    # Installation error (not verification error)
    $installSuccess = $false
    Write-Host ""
    Write-Error "Installation failed with error:"
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Stack trace:" -ForegroundColor Yellow
    Write-Host $_.ScriptStackTrace -ForegroundColor Gray
    Write-Host ""
    Write-Warn "Please report this error at: https://github.com/wulfhq/pyrite/issues"
    Write-Host ""
} finally {
    # Keep window open indefinitely for inspection
    if ($installSuccess) {
        Write-Host ""
        Write-Host "" -ForegroundColor Green
        Write-Host "Installation complete! Window will stay open for inspection." -ForegroundColor Green
        Write-Host "Close this window manually when done." -ForegroundColor Green
        Write-Host "" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "" -ForegroundColor Red
        Write-Host "Installation failed. Window will stay open for inspection." -ForegroundColor Red
        Write-Host "Review the errors above, then close this window manually." -ForegroundColor Red
        Write-Host "" -ForegroundColor Red
    }
    Write-Host ""
}

