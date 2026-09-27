"""Placeholder tests for src/structural_elements/support.py.

PillarSupport is a commented-out FIXME stub with no executable code yet. This
module imports support.py only so it appears in the coverage report: once real
PillarSupport code is added, its currently-absent lines will report as uncovered
(< 100%), flagging that real tests are still owed.
"""

from src.structural_elements import support


class TestSupportModule:
    """Import placeholder until PillarSupport is implemented."""

    def test_module_imports(self) -> None:
        assert support is not None, "support module should import cleanly"

    def test_pillar_support_not_yet_implemented(self) -> None:
        assert not hasattr(support, "PillarSupport"), (
            "PillarSupport is still a commented-out FIXME stub; when it is "
            "implemented, replace these placeholders with real tests"
        )
