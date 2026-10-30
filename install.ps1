$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$InstallRoot = Join-Path $env:LOCALAPPDATA "yt-tr"
$VenvDir = Join-Path $InstallRoot "venv"
$Python = Get-Command py -ErrorAction SilentlyContinue
if ($Python) {
    $PythonCommand = "py"
    $PythonArgs = @("-3")
} else {
    $Python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $Python) {
        throw "Python 3 was not found. Install it from https://www.python.org/downloads/windows/ and run this installer again."
    }
    $PythonCommand = $Python.Source
    $PythonArgs = @()
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
& $PythonCommand @PythonArgs -m venv $VenvDir
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $RepoDir "requirements.txt")
Copy-Item (Join-Path $RepoDir "yt-tr.py") (Join-Path $InstallRoot "yt-tr.py") -Force

$UserBin = Join-Path $env:USERPROFILE "bin"
New-Item -ItemType Directory -Force -Path $UserBin | Out-Null
$Launcher = Join-Path $UserBin "yt-tr.cmd"
$LauncherContent = @"
@echo off
"$VenvPython" "$InstallRoot\yt-tr.py" %*
"@
$LauncherContent | Set-Content -Path $Launcher -Encoding ASCII

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
$PathEntries = @($UserPath -split ";" | Where-Object { $_ })
if ($PathEntries -notcontains $UserBin) {
    [Environment]::SetEnvironmentVariable("Path", (($PathEntries + $UserBin) -join ";"), "User")
}

Write-Host "Installed yt-tr to $Launcher"
Write-Host "Open a new terminal for the PATH change to take effect."
