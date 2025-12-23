# Helper script to enforce wrapper usage for developer commands
# Usage: .\tools\utils\run_safe.ps1 -Cmd "<command>" [-NoPreview] [-PreviewLines <N>] [-TimeoutSec <S>] [-LogDir <path>]
#
# This script ensures all commands go through the run_logged wrapper
# It's a convenience wrapper around the wrapper to make it easier for developers

param(
    [Parameter(Mandatory=$true)]
    [string]$Cmd,
    
    [Parameter(Mandatory=$false)]
    [string]$Log = "",
    
    [Parameter(Mandatory=$false)]
    [int]$PreviewLines = 80,
    
    [Parameter(Mandatory=$false)]
    [switch]$NoPreview,

    [Parameter(Mandatory=$false)]
    [int]$TimeoutSec = 0,

    [Parameter(Mandatory=$false)]
    [string]$LogDir = "",

    [Parameter(Mandatory=$false)]
    [ValidateSet("full", "minimal", "none")]
    [string]$LogMode = "full"
)

# Bound preview lines to reasonable value to prevent agent crashes
if ($PreviewLines -gt 1000) {
    $PreviewLines = 1000
}

# Get script directory to find repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsDir = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent $toolsDir

# Find the wrapper script (prefer utils version)
$utilsDir = Join-Path $toolsDir 'utils'
$wrapperPath = Join-Path $utilsDir 'run_logged.ps1'
if (-not (Test-Path $wrapperPath)) {
    $wrapperPath = Join-Path $toolsDir 'run_logged.ps1'
}

if (-not (Test-Path $wrapperPath)) {
    Write-Host "ERROR: run_logged.ps1 wrapper not found!" -ForegroundColor Red
    Write-Host "Expected at: $wrapperPath" -ForegroundColor Red
    exit 1
}

# Default LogDir if not provided: use LOCALAPPDATA to avoid OneDrive issues
if ([string]::IsNullOrEmpty($LogDir)) {
    $LogDir = Join-Path $env:LOCALAPPDATA "pyrite\logs"
}

# Create log directory if it doesn't exist
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Determine log file paths
if ([string]::IsNullOrEmpty($Log)) {
    $StdoutLog = Join-Path $LogDir "stdout.log"
    $StderrLog = Join-Path $LogDir "stderr.log"
} else {
    $LogBase = if ($Log -like "*.log") { $Log -replace "\.log$", "" } else { $Log }
    $StdoutLog = "$LogBase-stdout.log"
    $StderrLog = "$LogBase-stderr.log"
}

# Build wrapper command
$wrapperArgs = @(
    '-NoProfile',
    '-NonInteractive',
    '-File',
    $wrapperPath,
    '-Cmd',
    $Cmd,
    '-Head', $PreviewLines.ToString(),
    '-Tail', $PreviewLines.ToString(),
    '-StdoutLog', $StdoutLog,
    '-StderrLog', $StderrLog
)

if ($NoPreview) {
    $wrapperArgs += @('-NoPreview')
}

if ($TimeoutSec -gt 0) {
    $wrapperArgs += @('-TimeoutSec', $TimeoutSec.ToString())
}

if ($LogDir) {
    $wrapperArgs += @('-LogDir', $LogDir)
}

if ($LogMode) {
    $wrapperArgs += @('-LogMode', $LogMode)
}

# Execute wrapper
& powershell $wrapperArgs
exit $LASTEXITCODE
