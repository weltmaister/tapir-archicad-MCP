param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ProjectRoot = Split-Path -Parent $RepoRoot
$WorkspaceRoot = Join-Path $ProjectRoot "archicad-mcp"
$VenvPython = Join-Path $ProjectRoot "archicad-mcp\.venv\Scripts\python.exe"
$ModelOutput = Join-Path $RepoRoot "build_support\models\all-MiniLM-L6-v2"
$SpecPath = Join-Path $RepoRoot "packaging\tapir_archicad_mcp.spec"
$TraySpecPath = Join-Path $RepoRoot "packaging\tapir_archicad_mcp_tray.spec"
$RepoBuildRoot = Join-Path $RepoRoot "build"
$RepoDistRoot = Join-Path $RepoRoot "dist"
$WorkspaceDistBundle = Join-Path $WorkspaceRoot "dist\tapir-archicad-mcp"
$RepoDistBundle = Join-Path $RepoDistRoot "tapir-archicad-mcp"
$RepoTrayExe = Join-Path $RepoDistRoot "tapir-archicad-mcp-tray.exe"
$RepoTrayInBundle = Join-Path $RepoDistBundle "tapir-archicad-mcp-tray.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Expected Python interpreter not found at $VenvPython"
}

if ($Clean) {
    Remove-Item -Recurse -Force $RepoBuildRoot, $RepoDistRoot, $WorkspaceDistBundle -ErrorAction SilentlyContinue
}

& $VenvPython (Join-Path $RepoRoot "scripts\export_sentence_model.py") --output-dir $ModelOutput
if ($LASTEXITCODE -ne 0) {
    throw "Model export failed with exit code $LASTEXITCODE"
}

& $VenvPython -m PyInstaller --noconfirm --clean --workpath $RepoBuildRoot --distpath $RepoDistRoot $SpecPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

& $VenvPython -m PyInstaller --noconfirm --clean --workpath $RepoBuildRoot --distpath $RepoDistRoot $TraySpecPath
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller tray build failed with exit code $LASTEXITCODE"
}

if (-not (Test-Path $RepoDistBundle)) {
    throw "Expected bundled executable directory not found at $RepoDistBundle"
}
if (-not (Test-Path $RepoTrayExe)) {
    throw "Expected tray executable not found at $RepoTrayExe"
}

Copy-Item -Force $RepoTrayExe $RepoTrayInBundle

Remove-Item -Recurse -Force $WorkspaceDistBundle -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path (Split-Path -Parent $WorkspaceDistBundle) -Force | Out-Null
Copy-Item -Recurse -Force $RepoDistBundle $WorkspaceDistBundle

Write-Host ""
Write-Host "Build completed. Executable output:"
Write-Host "  Canonical upstream bundle: $(Join-Path $RepoDistBundle 'tapir-archicad-mcp.exe')"
Write-Host "  Tray companion:            $RepoTrayInBundle"
Write-Host "  Workspace copy:           $(Join-Path $WorkspaceDistBundle 'tapir-archicad-mcp.exe')"
