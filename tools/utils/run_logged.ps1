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
#   -LogMode (optional, default: full): full, minimal, none
#   -TimeoutSec (optional, default: 0): Timeout in seconds (0 = none)
#   -NoPreview (optional): If present, do not print log head/tail
#   -LogDir (optional): Custom log directory

param(
    [Parameter(Mandatory=$true)]
    [string]$Cmd,
    
    [Parameter(Mandatory=$false)]
    [string]$Log = "",
    
    [Parameter(Mandatory=$false)]
    [int]$Head = 80,
    
    [Parameter(Mandatory=$false)]
    [int]$Tail = 80,

    [Parameter(Mandatory=$false)]
    [ValidateSet("full", "minimal", "none")]
    [string]$LogMode = "full",

    [Parameter(Mandatory=$false)]
    [int]$TimeoutSec = 0,

    [Parameter(Mandatory=$false)]
    [switch]$NoPreview,

    [Parameter(Mandatory=$false)]
    [string]$LogDir = ""
)

# Get script directory to find repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

# Determine log directory
if ([string]::IsNullOrEmpty($LogDir)) {
    $LogDir = Join-Path $repoRoot ".logs"
} else {
    # Ensure LogDir is rooted
    if (-not [System.IO.Path]::IsPathRooted($LogDir)) {
        $LogDir = Join-Path $repoRoot $LogDir
    }
}

# Create log directory if it doesn't exist
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

# Determine log file path
if ([string]::IsNullOrEmpty($Log)) {
    # Generate unique log filename based on timestamp and command hash
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $cmdBytes = [System.Text.Encoding]::UTF8.GetBytes($Cmd)
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $hashBytes = $md5.ComputeHash($cmdBytes)
    $hashString = [System.BitConverter]::ToString($hashBytes) -replace '-', ''
    $cmdHash = $hashString.Substring(0, 8).ToLower()
    
    $logName = "dev-$timestamp-$cmdHash.log"
    $Log = Join-Path $LogDir $logName
} else {
    # If Log is specified as relative path, put it in LogDir
    if (-not [System.IO.Path]::IsPathRooted($Log)) {
        # Check if it already looks like it's in a logs dir
        if ($Log -notlike ".logs*" -and $Log -notlike "*\.logs*") {
            $Log = Join-Path $LogDir (Split-Path -Leaf $Log)
        } else {
            $Log = Join-Path $repoRoot $Log
        }
    }
}

# Delete existing log if present
if (Test-Path $Log) {
    Remove-Item $Log -Force -ErrorAction SilentlyContinue
}

# Execution logic using Start-Process for timeout support
$exitCode = 0
$isTimeout = $false

try {
    # We use cmd /c with redirection inside it to capture all output.
    # We use Start-Process to get a handle for timeout management.
    $p = Start-Process "cmd" -ArgumentList "/c `"$Cmd > `"$Log`" 2>&1`"" -PassThru -NoNewWindow
    
    if ($TimeoutSec -gt 0) {
        if (-not ($p | Wait-Process -Timeout $TimeoutSec -ErrorAction SilentlyContinue)) {
            $p | Stop-Process -Force
            $isTimeout = $true
            $exitCode = -1
            "`n[TIMEOUT] Process killed after $TimeoutSec seconds" | Out-File -FilePath $Log -Append -Encoding utf8
        } else {
            $exitCode = $p.ExitCode
        }
    } else {
        $p | Wait-Process
        $exitCode = $p.ExitCode
    }
} catch {
    $errorMsg = $_.Exception.Message
    "`n[ERROR] $errorMsg" | Out-File -FilePath $Log -Append -Encoding utf8
    $exitCode = 1
}

# Print summary
Write-Host "`n--- Command Summary ---" -ForegroundColor Gray
Write-Host "Command: $Cmd"
Write-Host "Log:     $Log"
if ($isTimeout) {
    Write-Host "Status:  TIMEOUT" -ForegroundColor Red
} else {
    $statusColor = if ($exitCode -eq 0) { "Green" } else { "Red" }
    Write-Host "Status:  Exit Code $exitCode" -ForegroundColor $statusColor
}

# Preview log if requested
if (-not $NoPreview -and ($LogMode -ne "none") -and (Test-Path $Log)) {
    $fileInfo = Get-Item $Log
    if ($fileInfo.Length -gt 0) {
        if ($LogMode -eq "full") {
            Write-Host "=== First $Head lines ===" -ForegroundColor Cyan
            Get-Content $Log -TotalCount $Head | ForEach-Object { Write-Host $_ }
            
            Write-Host "`n=== Last $Tail lines ===" -ForegroundColor Cyan
            Get-Content $Log -Tail $Tail | ForEach-Object { Write-Host $_ }
        } elseif ($LogMode -eq "minimal" -and ($exitCode -ne 0 -or $isTimeout)) {
            Write-Host "=== Last $Tail lines (failure) ===" -ForegroundColor Red
            Get-Content $Log -Tail $Tail | ForEach-Object { Write-Host $_ }
        }
    } else {
        Write-Host "Log file is empty" -ForegroundColor Yellow
    }
}

exit $exitCode
