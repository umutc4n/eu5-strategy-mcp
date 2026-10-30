$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe') -or -not (Test-Path '.tools\rakaly.exe')) {
    throw 'Run .\install-windows.ps1 first.'
}
$env:EU5_RAKALY = (Resolve-Path '.tools\rakaly.exe').Path
$env:EU5_MCP_TRANSPORT = 'streamable-http'
$env:EU5_MCP_PORT = '8765'
Write-Host 'EU5 MCP starting on http://127.0.0.1:8765/mcp. Keep this window open.'
& .\.venv\Scripts\python.exe -m eu5_mcp
