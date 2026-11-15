"""The app's version, written next to this module when the app is packaged."""

from pathlib import Path

# packaging/pyinstaller.spec writes it from the release tag (e.g. "0.2.0")
_VERSION_FILE = Path(__file__).with_name("VERSION")
DEVELOPMENT: str = "desenvolvimento"


def app_version() -> str:
    """Version of the packaged app, or DEVELOPMENT when run from the source code"""
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip() or DEVELOPMENT
    except OSError:
        return DEVELOPMENT
