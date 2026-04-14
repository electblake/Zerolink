$env:DIST="dist\"
$env:PROG="zerolink"

# use get_program_version() in python from import zerolink/__main__.py
$version = python -c "from zerolink.__main__ import get_program_version; print(get_program_version())"

uv run pyinstaller --onefile zerolink/__main__.py --name $env:PROG --clean

$version_check = (& (Join-Path $env:DIST "${env:PROG}.exe") --version)

if ($version_check -ne "$env:PROG $version") {
    Write-Error "Version mismatch: expected $version but got $version_check"
    exit 1
}

Compress-Archive -Path (Join-Path $env:DIST "${env:PROG}.exe") -DestinationPath (Join-Path $env:DIST "zerolink-$version.zip") -Force

Write-Host "OK!"

# $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") | Out-Null # olds the terminal open indefinately
