param([string]$PythonExecutable='python',[string]$PackageManager='pnpm')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if ($PackageManager -eq 'pnpm' -and -not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    $bundled=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'
    if (Test-Path -LiteralPath $bundled) { $PackageManager=$bundled }
}
Set-Location -LiteralPath $root
if (-not (Test-Path -LiteralPath '.runtime\Scripts\python.exe')) {
    & $PythonExecutable -m venv .runtime
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create Python environment. Use Python 3.11 or 3.12 with pip.' }
}
& '.\.runtime\Scripts\python.exe' -m pip install -r backend/requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Locked backend dependency installation failed.' }
& '.\.runtime\Scripts\python.exe' -m pip install --no-deps -e './backend[test]'
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }
Push-Location frontend
try {
    & $PackageManager install --frozen-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    & $PackageManager run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
if (-not (Test-Path -LiteralPath '.env')) {
    & '.\.runtime\Scripts\python.exe' -c "from pathlib import Path; import secrets; Path('.env').write_text('MONGO_URI=mongodb://127.0.0.1:27019/?replicaSet=survey-rs\nMONGO_DB=survey_lab\nSECRET_KEY='+secrets.token_urlsafe(48)+'\nCOOKIE_SECURE=false\n',encoding='utf-8')"
    if ($LASTEXITCODE -ne 0) { throw 'Local configuration initialization failed.' }
}
Write-Output 'Installation complete. Run scripts/start-local.ps1 next.'
