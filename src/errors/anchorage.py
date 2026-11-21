"""Errors for beam bars that cannot be anchored"""

from src.errors.design import BeamDesignError


class AnchorageError(BeamDesignError):
    """The bars of a layer cannot be anchored"""


class AnchorageLengthError(AnchorageError):
    """The room left for the anchorage is shorter than the required length

    Attributes:
        available_length: Room for the anchorage (cm).
        required_length: Length the anchorage needs (cm).

    References:
        ABNT NBR 6118:2026 — Sections 9.4.2.5 and 18.3.2.4.1
    """

    def __init__(
        self, message: str, *, available_length: float, required_length: float
    ) -> None:
        super().__init__(message)
        self.available_length = available_length
        self.required_length = required_length


class HookDoesNotFitError(AnchorageError):
    """The layer's hooks are taller than the room in the section height

    Attributes:
        hook_height: Height of the tallest hook (cm).
        room: Room between the bars' axis and the opposite face's covering (cm).

    References:
        ABNT NBR 6118:2026 — Section 9.4.2.3
    """

    def __init__(self, *, hook_height: float, room: float) -> None:
        super().__init__(
            "Hooks do not fit in the section height. "
            f"Hook height: {hook_height:.2f} cm, Room: {room:.2f} cm."
        )
        self.hook_height = hook_height
        self.room = room


class ClampsDoNotFitError(AnchorageError):
    """No clamp arrangement with the required area fits in the section

    Attributes:
        required_area: Required clamp steel area (cm²).
    """

    # PAPER

    def __init__(self, *, required_area: float) -> None:
        super().__init__(
            f"No clamp arrangement fits in the section for {required_area:.2f} cm^2."
        )
        self.required_area = required_area


class SupportBarsShortError(AnchorageError):
    """The bars carried to a support are below the share of the span's area

    Attributes:
        support_index: Index of the support.
        carried_area: Area of the bars that reach the support (cm²).
        share: Share of the span's area the support needs.
        required_area: Area the support needs (cm²).

    References:
        ABNT NBR 6118:2026 — Section 18.3.2.4-c
    """

    def __init__(
        self,
        *,
        support_index: int,
        carried_area: float,
        share: float,
        required_area: float,
    ) -> None:
        super().__init__(
            f"Bars carried to support {support_index} ({carried_area:.3f} cm²) are "
            f"below {share:.3f} of the span's area ({required_area:.3f} cm²)."
        )
        self.support_index = support_index
        self.carried_area = carried_area
        self.share = share
        self.required_area = required_area
