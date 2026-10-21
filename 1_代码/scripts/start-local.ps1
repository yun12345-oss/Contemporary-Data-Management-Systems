param([string]$MongoExecutable='mongod',[switch]$SeedDemo)
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $root
$py=Join-Path $root '.runtime\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $py)) { throw 'Run scripts/install.ps1 first.' }
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) { throw 'Build frontend first using pnpm run build.' }
New-Item -ItemType Directory -Path '.local\mongo-live' -Force | Out-Null
$mongoLog=Join-Path $root '.local\mongo-live.log'
$dbPath=Join-Path $root '.local\mongo-live'
# 先探测目标端口；已有实例需由 setup-local 检查其副本集配置。
& $py -c "import socket; s=socket.socket(); s.settimeout(1); code=s.connect_ex(('127.0.0.1',27019)); s.close(); raise SystemExit(0 if code==0 else 1)"
if ($LASTEXITCODE -ne 0) {
    $mongoArgs='--dbpath "'+$dbPath+'" --port 27019 --bind_ip 127.0.0.1 --replSet survey-rs --logpath "'+$mongoLog+'"'
    Start-Process -FilePath $MongoExecutable -ArgumentList $mongoArgs -WindowStyle Hidden -PassThru | Select-Object -ExpandProperty Id | Set-Content '.local\mongo.pid'
    Start-Sleep -Seconds 2
}
& $py scripts/setup-local.py
if ($LASTEXITCODE -ne 0) { throw 'MongoDB initialization failed. Check port 27019 and .local/mongo-live.log.' }
$env:PYTHONPATH=Join-Path $root 'backend'
if ($SeedDemo) {
    & $py backend/scripts/seed_demo.py
    if ($LASTEXITCODE -ne 0) { throw 'Demo import failed.' }
}
Write-Output 'Open http://127.0.0.1:8000 . Press Ctrl+C here to stop the web server.'
& $py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if ($LASTEXITCODE -ne 0) { throw 'Web server stopped with an error.' }
