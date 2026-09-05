# wx Dependency Closure — Platform Wheel Availability

**Date:** 2026-09-05
**wxPython version:** 4.3.1
**requires-python (project):** ==3.14.*

| Platform | Python 3.14 | wxPython wheel | Notes |
|---|---|---|---|
| Windows win_amd64 | YES | wxpython-4.3.1-cp314-cp314-win_amd64.whl | Verified on PyPI 2026-09-05 |
| Windows win32 | YES | wxpython-4.3.1-cp314-cp314-win32.whl | |
| macOS arm64 | YES | wxpython-4.3.1-cp314-cp314-macosx_11_0_arm64.whl | macOS 11+ |
| macOS x86_64 | YES | wxpython-4.3.1-cp314-cp314-macosx_10_15_x86_64.whl | |
| Linux x86_64 | YES (project declares 3.14) | NO manylinux wheel | Must build from source tar.gz; requires libgtk-3-dev, libwebkit2gtk-4.0, build essentials, SIP. CI must apt-install build deps or use prebuilt docker. |

Strategy:
- pyproject.toml keeps PySide6 as production dependency.
- wxPython added as optional extra [wx] -> installable via pip install -e .[wx] or pip install -r requirements-release.lock (which now includes wxPython).
- Windows/macOS CI can pip install wxPython directly (wheel).
- Linux CI must either compile from sdist (apt-get install libgtk-3-dev libwebkit2gtk-4.1-dev libgstreamer...) or document as BLOCKED with build-deps.
- Release packaging: Qt remains default; wx artifact uses same wx version.
