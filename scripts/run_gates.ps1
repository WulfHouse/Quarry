# Wave 1/2 Gate Runner
# Usage: .\scripts\run_gates.ps1 [fast|full]
# Default: fast

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("fast", "full")]
    [string]$Gate = "fast"
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$toolsDir = Join-Path $repoRoot "tools"
$utilsDir = Join-Path $toolsDir "utils"
$runSafe = Join-Path $utilsDir "run_safe.ps1"

if ($Gate -eq "fast") {
    Write-Host "Running FAST gate..." -ForegroundColor Cyan
    & $runSafe -Cmd "python tools/testing/pytest.py forge/tests/middle/test_type_checker.py -v -m fast" -Head 50 -Tail 50
    exit $LASTEXITCODE
}
elseif ($Gate -eq "full") {
    Write-Host "Running FULL gate..." -ForegroundColor Cyan
    Write-Host "Step 1/2: Type checker tests..." -ForegroundColor Yellow
    & $runSafe -Cmd "python tools/testing/pytest.py forge/tests/middle/test_type_checker.py -v" -Head 100 -Tail 100
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAST gate failed!" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "Step 2/2: Dogfood build..." -ForegroundColor Yellow
    & $runSafe -Cmd "cd forge && python ../quarry/main.py build --dogfood" -Head 100 -Tail 100
    exit $LASTEXITCODE
}
