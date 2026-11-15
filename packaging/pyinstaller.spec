# PyInstaller spec of the beam_calculator desktop app: one folder, no console.
# Build from the repository root: pyinstaller --noconfirm packaging/pyinstaller.spec
# (packaging/build_linux.sh wraps it and packs the folder).

import os
import re
import subprocess
import sys
import sysconfig
from importlib.metadata import distribution
from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 (SPECPATH is set by PyInstaller)
ICON = ROOT / "resources/logo/png/icon/app.ico"
_LICENSE_NAME = re.compile(r"LICEN[CS]E|COPYING|NOTICE|AUTHORS", re.IGNORECASE)


def version_file() -> Path:
    """Write the version that pavement_ui/version.py reads into the build folder

    It is APP_VERSION, set by the build scripts from the release tag, or else
    what git describe says; without the tag's "v" (v0.2.0 is shown as 0.2.0).
    """
    version = os.environ.get("APP_VERSION") or subprocess.run(
        ["git", "describe", "--tags", "--always", "--dirty"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    path = Path(workpath) / "VERSION"  # noqa: F821 (workpath is set by PyInstaller)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version.removeprefix("v"), encoding="utf-8")
    return path


def _python_license() -> Path:
    """The interpreter's license: next to the stdlib (Linux) or in the prefix (Windows)"""
    for folder in (Path(sysconfig.get_path("stdlib")), Path(sys.base_prefix)):
        if (folder / "LICENSE.txt").is_file():
            return folder / "LICENSE.txt"
    raise SystemExit("Python's LICENSE.txt not found: the bundle must carry it")


def license_datas() -> list[tuple[str, str]]:
    """(file, bundle folder) of every license shipped in _internal/licenses/

    The app's own GPL-3.0, Python's, PySide6/Qt's LGPL-3.0 notice, and the
    license files of each package in requirements-app.txt (from its
    .dist-info, keeping their relative folders, as some share a file name).
    """
    datas = [
        (str(ROOT / "LICENSE"), "licenses/beam_calculator"),
        (str(_python_license()), "licenses/python"),
        (str(ROOT / "packaging/licenses/LGPL-3.0.txt"), "licenses/PySide6"),
        (str(ROOT / "packaging/licenses/PySide6-NOTICE.txt"), "licenses/PySide6"),
    ]
    requirements = (ROOT / "requirements-app.txt").read_text().splitlines()
    for name in (line.split("==")[0] for line in requirements if "==" in line):
        dist = distribution(name)
        for file in dist.files or []:
            in_dist_info = file.parts[0].endswith(".dist-info")
            if in_dist_info and _LICENSE_NAME.search(file.name):
                folder = Path("licenses", dist.name, *file.parts[1:-1])
                datas.append((str(file.locate()), folder.as_posix()))
    return datas


# Development tools and GUI toolkits the app never imports; some are pulled in
# only because they are installed next to it in the development venv
EXCLUDES = [
    "IPython",
    "ipykernel",
    "jupyter_client",
    "jupyter_core",
    "matplotlib.backends.backend_qt",
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_qtcairo",
    "matplotlib.backends.backend_tkagg",
    "matplotlib.backends.backend_tkcairo",
    "pandas",
    "pytest",
    "tkinter",
    "_tkinter",
]

a = Analysis(  # noqa: F821
    [str(ROOT / "pavement_ui/__main__.py")],
    pathex=[str(ROOT)],
    datas=[
        # Same relative path as in the repository: the code finds the logos
        # through __file__ (src/drawing/sheet.py, pavement_ui/.../theme/logo.py)
        (str(ROOT / "resources/logo/png"), "resources/logo/png"),
        (str(version_file()), "pavement_ui"),
        *license_datas(),
    ],
    # zoneinfo (sheet date) reads the time zones from tzdata when the system
    # has none, as on Windows; it is never imported, so name it here
    hiddenimports=["tzdata"],
    excludes=EXCLUDES,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="beam_calculator",
    console=False,
    upx=False,  # compressed binaries trip antivirus heuristics
    icon=str(ICON),
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    upx=False,
    name="beam_calculator",
)
