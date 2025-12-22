# Pyrite Development Setup Script
# Adds convenient aliases for running Pyrite tools from anywhere in the repo
#
# Usage: . .\setup-dev.ps1
# Or add to PowerShell profile for automatic loading

# Find the Pyrite repo root
if ($PSScriptRoot) {
    # When sourced as a script file
    # If we're in scripts/, go up one level to get repo root
    if ((Split-Path $PSScriptRoot -Leaf) -eq "scripts") {
        $repoRoot = Split-Path $PSScriptRoot -Parent
    } else {
        $repoRoot = $PSScriptRoot
    }
} else {
    # When sourced from profile, find repo root by looking for forge directory
    $currentPath = Get-Location
    $repoRoot = $null
    
    # Walk up the directory tree
    $path = $currentPath.Path
    while ($path -and -not $repoRoot) {
        if (Test-Path (Join-Path $path "forge")) {
            $repoRoot = $path
            break
        }
        $parent = Split-Path $path -Parent
        if ($parent -eq $path) { break }  # Reached root
        $path = $parent
    }
    
    # If not found, try common locations
    if (-not $repoRoot) {
        $commonPaths = @(
            "$env:USERPROFILE\OneDrive\Desktop\.WulfHouse\pyrite_alpha",
            "$env:USERPROFILE\Desktop\.WulfHouse\pyrite_alpha",
            "$env:USERPROFILE\.pyrite"
        )
        foreach ($commonPath in $commonPaths) {
            if (Test-Path (Join-Path $commonPath "forge")) {
                $repoRoot = $commonPath
                break
            }
        }
    }
}

# Check for .cmd files in scripts/ directory
$scriptsDir = Join-Path $repoRoot "scripts"
if (-not $repoRoot -or -not (Test-Path (Join-Path $scriptsDir "quarry.cmd"))) {
    Write-Warning "Pyrite repository not found. Skipping alias setup."
    Write-Warning "Make sure you're in the Pyrite repo or update setup-dev.ps1 with the correct path."
    return
}

# Create functions that work from anywhere
function quarry {
    & "$scriptsDir\quarry.cmd" $args
}

function pyrite {
    & "$scriptsDir\pyrite.cmd" $args
}

function rebuild {
    & "$scriptsDir\rebuild.cmd" $args
}

function pyrite_lsp {
    & "$scriptsDir\pyrite_lsp.cmd" $args
}

function pyrite_test {
    & "$scriptsDir\pyrite_test.cmd" $args
}

# Only show message if not already loaded (check if function exists)
if (-not (Get-Command quarry -ErrorAction SilentlyContinue)) {
    Write-Host "Pyrite development aliases loaded!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Available commands:" -ForegroundColor Cyan
    Write-Host "  quarry <command>      # Build system (build, test, fmt, etc.)" -ForegroundColor White
    Write-Host "  pyrite <file>         # Compiler (compile and run)" -ForegroundColor White
    Write-Host "  rebuild               # Rebuild runtime library" -ForegroundColor White
    Write-Host "  pyrite_lsp            # LSP server (for IDE integration)" -ForegroundColor White
    Write-Host "  pyrite_test [args]    # Run tests" -ForegroundColor White
    Write-Host ""
    Write-Host "All commands work from anywhere in the repo!" -ForegroundColor Yellow
}

