# Helper script to enforce wrapper usage for developer commands
# Usage: .\tools\run_safe.ps1 -Cmd "<command>" [-Head <N>] [-Tail <N>] [-Log <path>]
#
# This script ensures all commands go through the run_logged wrapper
# It's a convenience wrapper around the wrapper to make it easier for developers

param(
    [Parameter(Mandatory=$true)]
    [string]$Cmd,
    
    [Parameter(Mandatory=$false)]
    [string]$Log = "",
    
    [Parameter(Mandatory=$false)]
    [int]$Head = 80,
    
    [Parameter(Mandatory=$false)]
    [int]$Tail = 80
)

# Get script directory to find repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsDir = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent $toolsDir

# Find the wrapper script (prefer utils version)
# Join-Path in older PowerShell doesn't accept multiple segments, so chain them
$toolsDir = Join-Path $repoRoot 'tools'
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

# Build wrapper command
$wrapperArgs = @(
    '-NoProfile',
    '-NonInteractive',
    '-File',
    $wrapperPath,
    '-Cmd',
    $Cmd
)

if ($Log) {
    $wrapperArgs += @('-Log', $Log)
}

$wrapperArgs += @('-Head', $Head.ToString())
$wrapperArgs += @('-Tail', $Tail.ToString())

# Execute wrapper
& powershell $wrapperArgs
exit $LASTEXITCODE
