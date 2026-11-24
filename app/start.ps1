param([int]$Port = 8765)
$portraitRepo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$portraitPython = Join-Path $portraitRepo '.venv311/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $portraitPython)) { throw 'Missing existing .venv311 interpreter.' }
Push-Location -LiteralPath $portraitRepo
try {
    & $portraitPython -X utf8 -B -m app.server --port $Port
    if ($LASTEXITCODE -ne 0) { throw "Web application exited with code $LASTEXITCODE" }
} finally { Pop-Location }
