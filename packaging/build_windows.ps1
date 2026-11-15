# Build the Windows app folder (dist\beam_calculator\) and its installer
# (dist\beam_calculator-Setup-<version>.exe). Needs Inno Setup 6.3 or later.
# Usage, from any folder, with the project's venv active:
#   packaging\build_windows.ps1 [-Version 0.1.0]      (default: git describe)
param([string]$Version = "")
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")
if (-not $Version) { $Version = git describe --tags --always --dirty }
$Version = $Version -replace "^v", ""

# Inno Setup does not add itself to PATH; look in its default folders too
$iscc = Get-Command iscc -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $iscc) {
    $iscc = @(
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) { throw "ISCC.exe not found: install Inno Setup (https://jrsoftware.org/isinfo.php)" }

# The spec writes it into the app, for its About window
$env:APP_VERSION = $Version
# Native commands do not stop the script on failure: check each exit code
python -m PyInstaller --noconfirm --clean packaging/pyinstaller.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
# GPL-3.0 at the top, where it is seen; the bundled packages' are in _internal\licenses\
Copy-Item LICENSE dist\beam_calculator\

& $iscc "/DAppVersion=$Version" packaging\windows\beam_calculator.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
Write-Output "dist\beam_calculator-Setup-$Version.exe"
