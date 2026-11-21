"""Element IDs (P1, V1, L1…): the lowest number not in use is handed out next."""

from itertools import count

from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.model.pavement_records import PavementRecords


def next_id(kind: ElementKind, records: PavementRecords) -> str:
    """Return the smallest unused ID of a kind (e.g. "P2" after removing P2)

    Numbers freed by a removal or by clearing the pavement are reused, so the
    ID depends only on the current records.
    """
    used = records.ids_of(kind)
    return next(
        element_id for n in count(1) if (element_id := f"{kind.prefix}{n}") not in used
    )
