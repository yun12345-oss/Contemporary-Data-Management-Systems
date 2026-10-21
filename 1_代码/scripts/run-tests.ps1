$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath (Join-Path $root 'backend')
& (Join-Path $root '.runtime\Scripts\python.exe') -m pytest -q --junitxml=../artifacts/test-results.xml
if ($LASTEXITCODE -ne 0) { throw 'Tests failed. MongoDB replica set must be running on port 27019.' }
