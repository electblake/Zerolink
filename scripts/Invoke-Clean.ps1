[CmdletBinding()]
param(
    [string]$Prefix = (Split-Path -Parent $PSScriptRoot)
)
Write-Host "cleaning project build"
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$project_root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$fixedTargets = @(
    (Join-Path $project_root "build"),
    (Join-Path $project_root "dist"),
    (Join-Path $project_root ".pytest_cache"),
    (Join-Path $project_root ".mypy_cache"),
    (Join-Path $project_root ".ruff_cache"),
    (Join-Path $project_root ".tox"),
    (Join-Path $project_root ".nox"),
    (Join-Path $project_root ".coverage"),
    (Join-Path $project_root "dependencies" "venv")
)

foreach ($target in $fixedTargets) {
    $fullPath = Join-Path $Prefix $target
    if (Test-Path -LiteralPath $fullPath) {
        Write-Debug "Cleaning $fullPath"
        Remove-Item -LiteralPath $fullPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Get-ChildItem -Path $Prefix -Directory -Filter "*.egg-info" -Force -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Get-ChildItem -Path $Prefix -Directory -Filter "__pycache__" -Force -Recurse -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
