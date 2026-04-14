[CmdletBinding()]
param(
    [string]$Prefix = (Split-Path -Parent $PSScriptRoot),
    [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$project_root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$output_dir = Join-Path $project_root "dist"
$build_spec = Join-Path $project_root "zerolink.spec"
$python = Join-Path $project_root ".venv\Scripts\python.exe"

if ($Clean) {
    . (Join-Path $project_root "scripts" "Invoke-Clean.ps1")
}

if (-not (Test-Path -LiteralPath $build_spec -PathType Leaf)) {
    throw "Missing spec file: $build_spec"
}

Push-Location -LiteralPath $project_root
try {
    New-Item -ItemType Directory -Path $output_dir -Force | Out-Null

    Get-Process -Name "zerolink" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

    & $python -m pip install --upgrade pyinstaller build wheel
    if ($LASTEXITCODE -ne 0) {
        throw "pip install failed."
    }

    & $python -m PyInstaller --noconfirm --distpath $output_dir --workpath (Join-Path $project_root "build") $build_spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }

    & $python -m build --wheel --sdist --outdir $output_dir
    if ($LASTEXITCODE -ne 0) {
        throw "python -m build failed."
    }

    Write-Host "Build artifacts:"
    Get-ChildItem -LiteralPath $output_dir -File | Sort-Object Name | ForEach-Object {
        Write-Host " - $($_.Name)"
    }
} finally {
    Pop-Location
}
