param([string]$PackageManager='pnpm')
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
if ($PackageManager -eq 'pnpm' -and -not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
    $bundled=Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'
    if (Test-Path -LiteralPath $bundled) { $PackageManager=$bundled }
}
Push-Location (Join-Path $root 'frontend')
try {
    & $PackageManager run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally { Pop-Location }
