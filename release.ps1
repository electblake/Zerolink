[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$project_root = $PSScriptRoot
$dist_dir = Join-Path $project_root "dist"
$version = uv run python -c "from zerolink import __version__; print(__version__)"
$tag = "v$version"
$platform = "windows"
$architecture = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString().ToLowerInvariant()
$program = "zerolink"
$asset_name = "$program-$tag-$platform-$architecture.exe"
$asset_path = Join-Path $dist_dir $asset_name

Set-Location -LiteralPath $project_root

uv run pyinstaller --onefile zerolink/__main__.py --name $program --clean --noconfirm --distpath $dist_dir --workpath (Join-Path $project_root "build") --specpath (Join-Path $project_root "build")
Move-Item -LiteralPath (Join-Path $dist_dir "$program.exe") -Destination $asset_path -Force

& $asset_path --version

$commit = git rev-parse HEAD
gh release create $tag $asset_path --target $commit --title "$program $tag" --notes-file (Join-Path $project_root "CHANGELOG.md") --latest
