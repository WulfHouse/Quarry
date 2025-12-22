# run_logged.ps1 - Run command to completion, log output, then show head/tail
# Prevents early cancellation by never piping live output to truncators
#
# Usage:
#   pwsh -NoProfile -NonInteractive -File tools/run_logged.ps1 -Cmd "python script.py" -Head 20 -Tail 20
#
# Parameters:
#   -Cmd (required): Full command line to execute
#   -Log (optional): Path to log file (default: auto-generated in .logs/)
#   -Head (optional, default: 80): Number of first lines to print
#   -Tail (optional, default: 80): Number of last lines to print

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
$repoRoot = Split-Path -Parent $scriptDir
$logDir = Join-Path $repoRoot ".logs"

# Create log directory if it doesn't exist
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# Determine log file path
# If not specified, generate a unique filename in .logs/ directory
if ([string]::IsNullOrEmpty($Log)) {
    # Generate unique log filename based on timestamp and command hash
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    # Simple hash of command (first 8 chars of MD5)
    $cmdBytes = [System.Text.Encoding]::UTF8.GetBytes($Cmd)
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $hashBytes = $md5.ComputeHash($cmdBytes)
    $hashString = [System.BitConverter]::ToString($hashBytes) -replace '-', ''
    $cmdHash = $hashString.Substring(0, 8).ToLower()
    
    $logName = "dev-$timestamp-$cmdHash.log"
    $Log = Join-Path $logDir $logName
} else {
    # If Log is specified as relative path, put it in .logs/ unless it already includes that path
    if (-not [System.IO.Path]::IsPathRooted($Log)) {
        if ($Log -notlike ".logs*" -and $Log -notlike "*\.logs*") {
            $Log = Join-Path $logDir (Split-Path -Leaf $Log)
        } else {
            # Already has .logs in path, resolve relative to repo root
            $Log = Join-Path $repoRoot $Log
        }
    }
}

# Delete existing log if present
# Use -ErrorAction SilentlyContinue to handle file locks gracefully
if (Test-Path $Log) {
    Remove-Item $Log -Force -ErrorAction SilentlyContinue
}

# Run command to completion, capturing ALL output (stdout + stderr) to log
# Use cmd /c for external commands to ensure proper exit code handling
$exitCode = 0
try {
    # For simplicity and robustness, use cmd /c which works for most external commands
    # Redirect both stdout (1) and stderr (2) to log file
    # In cmd, use > for stdout and 2>&1 to redirect stderr to stdout, then redirect all to file
    # cmd /c ensures the command runs to completion and exit code is preserved
    $null = cmd /c "$Cmd > `"$Log`" 2>&1"
    $exitCode = $LASTEXITCODE
    
    # If LASTEXITCODE is null or 0 but we want to be sure, check if log exists
    if ($exitCode -eq $null) {
        $exitCode = 0
    }
} catch {
    # If command execution fails, capture error
    $errorMsg = $_.Exception.Message
    $errorMsg | Out-File -FilePath $Log -Append -Encoding utf8
    $exitCode = 1
}

# Read log file if it exists
if (Test-Path $Log) {
    $logContent = Get-Content $Log
    
    # Print first N lines
    if ($logContent.Count -gt 0) {
        $headLines = if ($logContent.Count -lt $Head) { $logContent } else { $logContent[0..($Head-1)] }
        Write-Host "=== First $Head lines ===" -ForegroundColor Cyan
        $headLines | Write-Host
        
        # Print last N lines if there's more content than Head
        if ($logContent.Count -gt $Head) {
            Write-Host "`n=== Last $Tail lines ===" -ForegroundColor Cyan
            $startTail = [Math]::Max(0, $logContent.Count - $Tail)
            $tailLines = $logContent[$startTail..($logContent.Count-1)]
            $tailLines | Write-Host
        }
        
        Write-Host "`n=== Full log available at: $Log ===" -ForegroundColor Yellow
    } else {
        Write-Host "Log file is empty" -ForegroundColor Yellow
    }
} else {
    Write-Host "No log file created (command may have failed before producing output)" -ForegroundColor Yellow
}

# Exit with the original command's exit code
exit $exitCode
