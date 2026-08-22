param(
    [Parameter(Mandatory = $true)]
    [string]$Version,
    [switch]$Offline,
    [string]$LinuxImage = "hpc-client-gui-linux-build:24.04"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker is required for the Linux release build."
}

$cacheRoot = Join-Path $Root ".cache/release"
foreach ($path in @("pip", "flatpak", "appimagetool")) {
    New-Item -ItemType Directory -Force (Join-Path $cacheRoot $path) | Out-Null
}

$image = docker images -q $LinuxImage
if (-not $image) {
    if ($Offline) { throw "Linux build image '$LinuxImage' is not cached." }
    docker build -t $LinuxImage -f build/linux/Dockerfile .
}

$offlineValue = if ($Offline) { "1" } else { "0" }
$linuxCommand = @'
set -eu
if [ ! -x /cache/appimagetool/appimagetool-x86_64.AppImage ]; then
  if [ "$RELEASE_OFFLINE" = "1" ]; then echo "AppImage tool is not cached" >&2; exit 2; fi
  wget --tries=6 --retry-connrefused --waitretry=5 --timeout=30 \
    -O /cache/appimagetool/appimagetool-x86_64.AppImage \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x /cache/appimagetool/appimagetool-x86_64.AppImage
fi
if [ ! -x /cache/venv/bin/python ]; then python3 -m venv /cache/venv; fi
/cache/venv/bin/pip install -r requirements-release.lock
/cache/venv/bin/pip install -e . --no-deps
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
if [ "$RELEASE_OFFLINE" = "1" ]; then
  flatpak info org.freedesktop.Platform//24.08 >/dev/null 2>&1 || { echo "Flatpak runtime is not cached" >&2; exit 2; }
  flatpak info org.freedesktop.Sdk//24.08 >/dev/null 2>&1 || { echo "Flatpak SDK is not cached" >&2; exit 2; }
else
  flatpak install -y flathub org.freedesktop.Platform//24.08 org.freedesktop.Sdk//24.08
fi
/cache/venv/bin/pyinstaller -y --clean build/linux/hpc-client-gui-linux.spec
cd /tmp
/cache/appimagetool/appimagetool-x86_64.AppImage --appimage-extract >/dev/null
cd /work
export APPIMAGETOOL=/tmp/squashfs-root/AppRun
/cache/venv/bin/python scripts/release_linux.py --version "$RELEASE_VERSION" --execute
'@

docker run --rm --privileged `
    -e "RELEASE_VERSION=$Version" `
    -e "RELEASE_OFFLINE=$offlineValue" `
    -v "${Root}:/work" `
    -v "${cacheRoot}/pip:/root/.cache/pip" `
    -v "${cacheRoot}/flatpak:/var/lib/flatpak" `
    -v "${cacheRoot}:/cache" `
    -w /work $LinuxImage bash -lc $linuxCommand

pyinstaller -y --clean build/windows/hpc-client-gui.spec
pyinstaller -y --clean build/windows/hpc-client-cli.spec
powershell -NoProfile -File scripts/package_release.ps1 -Version $Version

Write-Host "Release complete: dist/releases/v$Version"
