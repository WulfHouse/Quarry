# Wrapper script to run debug commands safely (no cancellation)
# Usage: .\scripts\run_debug_wrapper.ps1
# This script uses the run_logged wrapper to ensure commands complete fully

$env:PYRITE_DEBUG_TYPE_RESOLUTION='1'

# Use the run_logged wrapper to run the command to completion
$cmd = 'python -m src.compiler forge/src-pyrite/tokens.pyrite --emit-llvm'
$logFile = '.debug-tokens.log'

# Run command to completion using wrapper
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$wrapperPath = Join-Path $repoRoot 'tools' 'utils' 'run_logged.ps1'

# tools/utils/run_logged.ps1 is the canonical version

if (Test-Path $wrapperPath) {
    # Use the wrapper - it will run to completion and show output
    # We can filter the log AFTER the command completes (no cancellation risk)
    & powershell -NoProfile -NonInteractive -File $wrapperPath -Cmd $cmd -Log $logFile -Head 0 -Tail 0
    $exitCode = $LASTEXITCODE
    
    # Now filter the log file for relevant patterns (AFTER command completes)
    # This is safe because the command has already finished - we're reading from a file, not a live pipe
    # SAFE: Select-Object on a file read is OK; it's only dangerous when used on live command output
    if (Test-Path $logFile) {
        $logContent = Get-Content $logFile
        $filtered = $logContent | Select-String -Pattern "Option|Some|check_field_access|TRACE|register_option"
        $filteredLines = $filtered | Select-Object -First 30
        if ($filteredLines) {
            Write-Host "`n=== Filtered debug output (first 30 matches) ===" -ForegroundColor Cyan
            $filteredLines | Write-Host
        }
    }
    
    exit $exitCode
} else {
    Write-Host "Error: run_logged.ps1 wrapper not found at $wrapperPath" -ForegroundColor Red
    exit 1
}
