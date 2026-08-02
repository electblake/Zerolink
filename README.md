# Zerolink

Zerolink moves files from a download folder into a canonical storage folder with
[`rclone`](https://rclone.org/), replaces the download folder with a directory
symlink, and then points that symlink at the canonical folder.

Zerolink is a Windows command. The packaged `zerolink.exe` can also install a
File Explorer context-menu entry and run interactively when given a single
folder.

## Install the packaged app

Download [`zerolink-v0.10.1-windows-x64.exe`](https://github.com/electblake/zerolink/releases/download/v0.10.1/zerolink-v0.10.1-windows-x64.exe)
from the [latest GitHub release](https://github.com/electblake/zerolink/releases/latest),
rename it to `zerolink.exe`, and place it in a permanent location. The File
Explorer entry records this exact path, so do not move the executable after
installing the entry.

```powershell
$installDir = Join-Path $env:LOCALAPPDATA "Programs\Zerolink"
New-Item -ItemType Directory -Path $installDir -Force
Copy-Item ".\zerolink.exe" (Join-Path $installDir "zerolink.exe")
```

Zerolink invokes `rclone` when the input folder contains files. Install
`rclone`, and make sure `rclone.exe` is available on `PATH`.

### File Explorer mode

Install **Run Zerolink** in the right-click menu for folders:

```powershell
& "$env:LOCALAPPDATA\Programs\Zerolink\zerolink.exe" --install-menu
```

Right-click an existing download folder in File Explorer, select **Run
Zerolink**, and enter its canonical storage path when prompted. The menu entry
is installed for the current Windows user and does not require an elevated
terminal.

Remove the entry with:

```powershell
& "$env:LOCALAPPDATA\Programs\Zerolink\zerolink.exe" --uninstall-menu
```

### GUI (interactive) mode

Launch the packaged app with one existing input folder. Zerolink will prompt
for the canonical path and for confirmation before moving files or replacing
the input folder:

```powershell
& "$env:LOCALAPPDATA\Programs\Zerolink\zerolink.exe" "C:\Downloads\Example"
```

You can also drag an existing folder onto `zerolink.exe`; Windows supplies that
folder as the single argument and the same interactive prompts appear.

## Command-line usage

Supply both paths to run directly:

```powershell
zerolink "D:\Media\Example" "C:\Downloads\Example"
```

The first argument is the canonical location where the real files will live.
The second is the existing input folder that will be moved and replaced by a
symlink.

### `--help`

```console
> zerolink --help
usage: zerolink [-h] [--install-menu] [--uninstall-menu] [--version]
                [canon] [input]

Link landing zone download folders to inbox folders.

positional arguments:
  canon             Canonical path to actual files storage location.
  input             Path to new download input files. Will be symlinked to
                    canonical location.

optional arguments:
  -h, --help        show this help message and exit
  --install-menu    Install the File Explorer context-menu entry.
  --uninstall-menu  Remove the File Explorer context-menu entry.
  --version         Show version info and exit
```

### `--version`

```console
> zerolink --version
zerolink 0.10.1
```
