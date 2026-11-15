"""The pavement files shipped in resources/examples/ stay loadable.

They are what end users open first (and the template is what they copy), so an
engine change that breaks one of them must fail here.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from src.config import APP_CONFIG, AppConfig
from src.persistency import load_pavement

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "resources" / "examples"
EXAMPLE_FILES = sorted(EXAMPLES_DIR.glob("*.yaml"))
TEMPLATE = EXAMPLES_DIR / "template.yaml"


@pytest.fixture(autouse=True)
def restore_app_config() -> Generator[None]:
    """Snapshot and restore APP_CONFIG, which load_pavement mutates in place."""
    snapshot = {f: getattr(APP_CONFIG, f) for f in AppConfig.__dataclass_fields__}
    yield
    for field, value in snapshot.items():
        setattr(APP_CONFIG, field, value)


def test_examples_folder_has_the_template_and_examples() -> None:
    assert TEMPLATE in EXAMPLE_FILES, "resources/examples/ should hold template.yaml"
    assert len(EXAMPLE_FILES) >= 2, "there should be examples besides the template"


@pytest.mark.parametrize("path", EXAMPLE_FILES, ids=lambda path: path.name)
def test_example_loads(path: Path) -> None:
    pavement = load_pavement(path)
    assert pavement.pillars, f"{path.name} should define pillars"
    assert pavement.beams, f"{path.name} should define beams"
    assert pavement.slabs, f"{path.name} should define slabs"


def test_template_resolves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # resolve() writes reports relative to the cwd: keep them out of the repo
    monkeypatch.chdir(tmp_path)
    pavement = load_pavement(TEMPLATE)
    pavement.resolve()
    assert all(beam.height > 0 for beam in pavement.beams.values()), (
        "every beam of the template should be dimensioned"
    )
