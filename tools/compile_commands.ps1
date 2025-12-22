# Common compilation commands for Pyrite modules
# These commands use the safe wrapper to prevent early cancellation
#
# Usage:
#   .\tools\compile_commands.ps1
#   Compile-TypesModule
#   Compile-TokensModule
#   etc.

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$wrapperPath = Join-Path $repoRoot 'tools' 'utils' 'run_safe.ps1'

function Compile-TypesModule {
    <#
    .SYNOPSIS
    Compiles types.pyrite module using Stage1 compiler
    
    .DESCRIPTION
    Compiles the types.pyrite module to build/bootstrap/stage2/types.o
    Uses the safe wrapper to prevent early cancellation.
    #>
    $cmd = "cd `"$repoRoot`"; python -m src.compiler forge\src-pyrite\types.pyrite -o build\bootstrap\stage2\types 2>&1"
    & $wrapperPath -Cmd $cmd -Head 15 -Tail 15
}

function Compile-TokensModule {
    <#
    .SYNOPSIS
    Compiles tokens.pyrite module using Stage1 compiler
    
    .DESCRIPTION
    Compiles the tokens.pyrite module to build/bootstrap/stage2/tokens.o
    Uses the safe wrapper to prevent early cancellation.
    #>
    $cmd = "cd `"$repoRoot`"; python -m src.compiler forge\src-pyrite\tokens.pyrite -o build\bootstrap\stage2\tokens 2>&1"
    & $wrapperPath -Cmd $cmd -Head 15 -Tail 15
}

function Compile-SymbolTableModule {
    <#
    .SYNOPSIS
    Compiles symbol_table.pyrite module using Stage1 compiler
    
    .DESCRIPTION
    Compiles the symbol_table.pyrite module to build/bootstrap/stage2/symbol_table.o
    Uses the safe wrapper to prevent early cancellation.
    #>
    $cmd = "cd `"$repoRoot`"; python -m src.compiler forge\src-pyrite\symbol_table.pyrite -o build\bootstrap\stage2\symbol_table 2>&1"
    & $wrapperPath -Cmd $cmd -Head 15 -Tail 15
}

function Compile-ASTModule {
    <#
    .SYNOPSIS
    Compiles ast.pyrite module using Stage1 compiler
    
    .DESCRIPTION
    Compiles the ast.pyrite module to build/bootstrap/stage2/ast.o
    Uses the safe wrapper to prevent early cancellation.
    #>
    $cmd = "cd `"$repoRoot`"; python -m src.compiler forge\src-pyrite\ast.pyrite -o build\bootstrap\stage2\ast 2>&1"
    & $wrapperPath -Cmd $cmd -Head 15 -Tail 15
}

function Compile-DiagnosticsModule {
    <#
    .SYNOPSIS
    Compiles diagnostics.pyrite module using Stage1 compiler
    
    .DESCRIPTION
    Compiles the diagnostics.pyrite module to build/bootstrap/stage2/diagnostics.o
    Uses the safe wrapper to prevent early cancellation.
    #>
    $cmd = "cd `"$repoRoot`"; python -m src.compiler forge\src-pyrite\diagnostics.pyrite -o build\bootstrap\stage2\diagnostics 2>&1"
    & $wrapperPath -Cmd $cmd -Head 15 -Tail 15
}

function Compile-MainModule {
    <#
    .SYNOPSIS
    Compiles main.pyrite module using Stage1 compiler
    
    .DESCRIPTION
    Compiles the main.pyrite module to build/bootstrap/stage2/main
    Uses the safe wrapper to prevent early cancellation.
    #>
    $cmd = "cd `"$repoRoot`"; python -m src.compiler forge\src-pyrite\main.pyrite -o build\bootstrap\stage2\main 2>&1"
    & $wrapperPath -Cmd $cmd -Head 15 -Tail 15
}

# Export functions for use
Export-ModuleMember -Function Compile-TypesModule, Compile-TokensModule, Compile-SymbolTableModule, Compile-ASTModule, Compile-DiagnosticsModule, Compile-MainModule
