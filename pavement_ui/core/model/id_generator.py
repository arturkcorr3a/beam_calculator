"""Sequential element IDs (P1, V1, L1…) that are never reused in a session."""

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.model.pavement_records import ElementCounts


class IdGenerator:
    """Hand out the next ID of each element kind

    An ID is only consumed by ``commit`` (after a successful inclusion), so a
    refused inclusion does not skip a number. Numbers are never reused after a
    removal or after clearing the pavement [Manual §2.1].
    """

    def __init__(self) -> None:
        self._next: dict[ElementKind, int] = dict.fromkeys(ElementKind, 1)

    def peek(self, kind: ElementKind) -> str:
        """Return the next ID of a kind without consuming it (e.g. "P4")"""
        return f"{kind.prefix}{self._next[kind]}"

    def commit(self, kind: ElementKind) -> None:
        """Consume the ID returned by ``peek``"""
        self._next[kind] += 1

    def reset_after(self, counts: ElementCounts) -> None:
        """Restart the numbering right after the given counts

        Used by "new project" (all zero) and "open" (the file's elements are
        renumbered 1…n in file order).
        """
        self._next = {kind: counts.of(kind) + 1 for kind in ElementKind}
