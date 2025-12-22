# Validation script to check if commands use the wrapper
# This can be used to audit command usage

param(
    [Parameter(Mandatory=$false)]
    [string]$Path = "."
)

Write-Host "Checking for unsafe command patterns..." -ForegroundColor Cyan

$unsafePatterns = @(
    '\| Select-Object -First',
    '\| Select-Object -Last',
    '\| more',
    '\| Out-Host',
    '\| head',
    '\| tail'
)

$foundIssues = $false

# Exclude documentation and policy files (they show examples)
$excludeDirs = @('plans', 'node_modules', '.git', '.logs')
$excludeFiles = @(
    'DEVELOPER_COMMAND_POLICY.md',
    'CANCELLATION_PREVENTION.md',
    'validate_command_safety.ps1',
    'run_logged.ps1',
    'run_safe.ps1'
)

# Search PowerShell scripts (exclude docs and wrappers)
Get-ChildItem -Path $Path -Recurse -Include *.ps1 | Where-Object {
    $file = $_
    $relativePath = $file.FullName.Replace((Resolve-Path $Path).Path + '\', '')
    
    # Skip if in excluded directory
    $skip = $false
    foreach ($excludeDir in $excludeDirs) {
        if ($relativePath -like "$excludeDir*") {
            $skip = $true
            break
        }
    }
    
    # Skip if in excluded files list
    if (-not $skip) {
        foreach ($excludeFile in $excludeFiles) {
            if ($file.Name -eq $excludeFile) {
                $skip = $true
                break
            }
        }
    }
    
    -not $skip
} | ForEach-Object {
    $file = $_
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    
    if ($content) {
        foreach ($pattern in $unsafePatterns) {
            # Check if pattern appears in a context that suggests live piping
            # Look for patterns that aren't in comments or documentation context
            $regex = "(?<!`#.*?)(?<!#.*?)(?<!'.*?)$pattern"
            if ($content -match $regex) {
                # Additional check: is this in a comment or string?
                $lines = Get-Content $file.FullName
                $lineNum = 0
                foreach ($line in $lines) {
                    $lineNum++
                    if ($line -match $pattern) {
                        # Skip if it's clearly a comment or documentation
                        $trimmed = $line.Trim()
                        if ($trimmed -notmatch '^#|^//|^`#|FORBIDDEN|BAD|CORRECT|Example|Example|❌|✅') {
                            Write-Host "⚠️  UNSAFE PATTERN FOUND:" -ForegroundColor Yellow
                            Write-Host "   File: $($file.FullName):$lineNum" -ForegroundColor Yellow
                            Write-Host "   Pattern: $pattern" -ForegroundColor Yellow
                            Write-Host "   Line: $line" -ForegroundColor Gray
                            $foundIssues = $true
                        }
                    }
                }
            }
        }
    }
}

if (-not $foundIssues) {
    Write-Host "✅ No unsafe patterns found!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n❌ Found unsafe command patterns. Use tools/utils/run_logged.ps1 wrapper instead." -ForegroundColor Red
    Write-Host "See tools/DEVELOPER_COMMAND_POLICY.md for details." -ForegroundColor Red
    exit 1
}
