param(
    [string]$Image = 'cfd_final_00001.png',
    [int]$TopK = 5
)
$fusionRepo = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$fusionPython = Join-Path $fusionRepo '.venv311/Scripts/python.exe'
Push-Location -LiteralPath $fusionRepo
try {
    & $fusionPython -X utf8 -B -m database.four_feature search --image $Image --top-k $TopK --no-save
    if ($LASTEXITCODE -ne 0) { throw "SQLite fusion demo failed: $LASTEXITCODE" }
} finally {
    Pop-Location
}
