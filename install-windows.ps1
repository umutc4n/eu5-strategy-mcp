$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Install Python 3.11+ from python.org, then retry.'
}
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    & py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
}
& .\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -e .
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies failed.' }

New-Item -ItemType Directory -Force -Path '.tools' | Out-Null
$rakaly = Join-Path $PSScriptRoot '.tools\rakaly.exe'
if (-not (Test-Path $rakaly)) {
    $release = Invoke-RestMethod 'https://api.github.com/repos/rakaly/cli/releases/latest'
    $asset = $release.assets | Where-Object { $_.name -match 'x86_64-pc-windows-msvc\.zip$' } | Select-Object -First 1
    if (-not $asset -or -not ($asset.digest -match '^sha256:[a-fA-F0-9]{64}$')) {
        throw 'Release asset or digest missing. Refusing unverified download.'
    }
    $archive = Join-Path $env:TEMP 'eu5-rakaly-windows.zip'
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archive
    if ((Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $asset.digest.Substring(7).ToLowerInvariant()) {
        throw 'Rakaly checksum mismatch.'
    }
    $extract = Join-Path $env:TEMP 'eu5-rakaly-extract'
    New-Item -ItemType Directory -Force -Path $extract | Out-Null
    Expand-Archive -Path $archive -DestinationPath $extract -Force
    $binary = Get-ChildItem -Path $extract -Filter 'rakaly.exe' -Recurse | Select-Object -First 1
    if (-not $binary) { throw 'Rakaly executable missing from release.' }
    Copy-Item $binary.FullName $rakaly
}
Write-Host 'Installed. Run: .\start-windows.ps1'
