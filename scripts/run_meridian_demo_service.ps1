$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$environmentFile = Join-Path $repositoryRoot '.env'
if (!(Test-Path -LiteralPath $environmentFile -PathType Leaf)) {
    [Console]::Error.WriteLine('The protected server environment file is unavailable.')
    exit 1
}

$apiKey = $null
foreach ($line in [System.IO.File]::ReadAllLines($environmentFile)) {
    if ($line -match '^\s*(?:export\s+)?NANSEN_API_KEY\s*=\s*(.*)$') {
        $apiKey = $Matches[1].Trim()
    }
}
if ($apiKey -and $apiKey.Length -ge 2) {
    if (($apiKey.StartsWith('"') -and $apiKey.EndsWith('"')) -or
        ($apiKey.StartsWith("'") -and $apiKey.EndsWith("'"))) {
        $apiKey = $apiKey.Substring(1, $apiKey.Length - 2)
    }
}
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    [Console]::Error.WriteLine('NANSEN_API_KEY is missing from the protected server environment.')
    exit 1
}

$python = 'C:\VAMBAM\Projects\OTG\.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python -PathType Leaf)) {
    [Console]::Error.WriteLine('The configured OTG Python runtime is unavailable.')
    exit 1
}

$env:NANSEN_API_KEY = $apiKey
$env:PYTHONPATH = Join-Path $repositoryRoot 'src'
& $python -m otg_nansen.demo_app --serve --host 127.0.0.1 --port 8765
exit $LASTEXITCODE
