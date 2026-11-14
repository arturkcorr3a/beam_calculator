# PyInstaller spec of the beam_calculator desktop app: one folder, no console.
# Build from the repository root: pyinstaller --noconfirm packaging/pyinstaller.spec
# (packaging/build_linux.sh wraps it and packs the folder).

from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 (SPECPATH is set by PyInstaller)
ICON = ROOT / "resources/logo/png/icon/app.ico"

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
    # Same relative path as in the repository: the code finds the logos
    # through __file__ (src/drawing/sheet.py, pavement_ui/.../theme/logo.py)
    datas=[(str(ROOT / "resources/logo/png"), "resources/logo/png")],
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
