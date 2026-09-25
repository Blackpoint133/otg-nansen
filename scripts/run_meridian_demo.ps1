$ErrorActionPreference = 'Stop'

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $pythonCommand) {
    [Console]::Error.WriteLine('Python was not found. Install Python and try again.')
    exit 1
}

if ([string]::IsNullOrWhiteSpace($env:NANSEN_API_KEY)) {
    [Console]::Error.WriteLine('NANSEN_API_KEY is missing or empty in this PowerShell process.')
    exit 1
}

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$sourcePath = Join-Path $repositoryRoot 'src'
if ([string]::IsNullOrWhiteSpace($env:PYTHONPATH)) {
    $env:PYTHONPATH = $sourcePath
} else {
    $env:PYTHONPATH = "$sourcePath;$env:PYTHONPATH"
}

Write-Output 'http://127.0.0.1:8765/'
& $pythonCommand.Source -m otg_nansen.demo_app --serve 1>$null
exit $LASTEXITCODE
