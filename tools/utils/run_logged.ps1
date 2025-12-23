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
    [string]$StdoutLog = "",
    
    [Parameter(Mandatory=$false)]
    [string]$StderrLog = "",
    
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

# Determine log file paths
if ([string]::IsNullOrEmpty($Log) -and [string]::IsNullOrEmpty($StdoutLog)) {
    # Generate unique log filename base based on timestamp and command hash
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
    $cmdBytes = [System.Text.Encoding]::UTF8.GetBytes($Cmd)
    $md5 = [System.Security.Cryptography.MD5]::Create()
    $hashBytes = $md5.ComputeHash($cmdBytes)
    $hashString = [System.BitConverter]::ToString($hashBytes) -replace '-', ''
    $cmdHash = $hashString.Substring(0, 8).ToLower()
    
    $StdoutLog = Join-Path $LogDir "dev-$timestamp-$cmdHash-stdout.log"
    $StderrLog = Join-Path $LogDir "dev-$timestamp-$cmdHash-stderr.log"
    $Log = Join-Path $LogDir "dev-$timestamp-$cmdHash.log"
} else {
    # If Log is specified, use it for base if Stdout/Stderr not provided
    if ([string]::IsNullOrEmpty($StdoutLog)) {
        if ([string]::IsNullOrEmpty($Log)) {
            $StdoutLog = Join-Path $LogDir "stdout.log"
        } else {
            $StdoutLog = if ($Log -like "*.log") { $Log -replace "\.log$", "-stdout.log" } else { "$Log-stdout" }
        }
    }
    if ([string]::IsNullOrEmpty($StderrLog)) {
        if ([string]::IsNullOrEmpty($Log)) {
            $StderrLog = Join-Path $LogDir "stderr.log"
        } else {
            $StderrLog = if ($Log -like "*.log") { $Log -replace "\.log$", "-stderr.log" } else { "$Log-stderr" }
        }
    }
}

# Ensure all paths are rooted
function Root-Path($p) {
    if ([string]::IsNullOrEmpty($p)) { return $p }
    if (-not [System.IO.Path]::IsPathRooted($p)) {
        return Join-Path $repoRoot $p
    }
    return $p
}

$StdoutLog = Root-Path $StdoutLog
$StderrLog = Root-Path $StderrLog
if (-not [string]::IsNullOrEmpty($Log)) { $Log = Root-Path $Log }

# Delete existing logs if present
foreach ($l in @($StdoutLog, $StderrLog)) {
    if (Test-Path $l) {
        Remove-Item $l -Force -ErrorAction SilentlyContinue
    }
}

# Execution logic using Start-Process for timeout support
$exitCode = 0
$isTimeout = $false

try {
    # We use separate redirection for stdout and stderr.
    # We use Start-Process to get a handle for timeout management.
    $p = Start-Process "cmd" -ArgumentList "/c `"$Cmd > `"$StdoutLog`" 2> `"$StderrLog`"`"" -PassThru -NoNewWindow
    
    if ($TimeoutSec -gt 0) {
        if (-not ($p | Wait-Process -Timeout $TimeoutSec -ErrorAction SilentlyContinue)) {
            $p | Stop-Process -Force
            $isTimeout = $true
            $exitCode = -1
            "`n[TIMEOUT] Process killed after $TimeoutSec seconds" | Out-File -FilePath $StderrLog -Append -Encoding utf8
        } else {
            $exitCode = $p.ExitCode
        }
    } else {
        $p | Wait-Process
        $exitCode = $p.ExitCode
    }
} catch {
    $errorMsg = $_.Exception.Message
    "`n[ERROR] $errorMsg" | Out-File -FilePath $StderrLog -Append -Encoding utf8
    $exitCode = 1
}

# Print summary
Write-Host "`n--- Command Summary ---" -ForegroundColor Gray
Write-Host "Command: $Cmd"
Write-Host "Stdout:  $StdoutLog"
Write-Host "Stderr:  $StderrLog"
if ($isTimeout) {
    Write-Host "Status:  TIMEOUT" -ForegroundColor Red
} else {
    if ($exitCode -eq 0) {
        $statusColor = "Green"
    } else {
        $statusColor = "Red"
    }
    Write-Host "Status:  Exit Code $exitCode" -ForegroundColor $statusColor
}

# Preview logs if requested
if (-not $NoPreview -and ($LogMode -ne "none")) {
    foreach ($logFile in @($StdoutLog, $StderrLog)) {
        if (Test-Path $logFile) {
            $fileInfo = Get-Item $logFile
            $isStderr = ($logFile -eq $StderrLog)
            $label = if ($isStderr) { "Stderr" } else { "Stdout" }
            $color = if ($isStderr) { "Yellow" } else { "Cyan" }
            
            if ($fileInfo.Length -gt 0) {
                if ($LogMode -eq "full") {
                    Write-Host "=== ${label}: First $Head lines ===" -ForegroundColor $color
                    Get-Content $logFile -TotalCount $Head | ForEach-Object { Write-Host $_ }
                    
                    Write-Host "`n=== ${label}: Last $Tail lines ===" -ForegroundColor $color
                    Get-Content $logFile -Tail $Tail | ForEach-Object { Write-Host $_ }
                } elseif ($LogMode -eq "minimal" -and ($exitCode -ne 0 -or $isTimeout)) {
                    Write-Host "=== ${label}: Last $Tail lines (failure) ===" -ForegroundColor Red
                    Get-Content $logFile -Tail $Tail | ForEach-Object { Write-Host $_ }
                }
            }
        }
    }
}

exit $exitCode
