"""Errors for designed bars that cannot be detailed"""

from src.errors.base import BeamCalculatorError, beam_prefixed


class DetailingError(BeamCalculatorError, ValueError):
    """The designed bars cannot be detailed for construction"""


class BeamDetailingError(DetailingError):
    """A designed beam's bars cannot be detailed for construction

    Attributes:
        beam_id: Id of the beam, usually set by ``ContinuousBeam`` after the
            detailing steps raise; shown as a prefix of the message.
    """

    def __init__(self, message: str, *, beam_id: str | None = None) -> None:
        super().__init__(message)
        self.beam_id = beam_id

    def __str__(self) -> str:
        return beam_prefixed(self.beam_id, self.message)


class SpliceDiameterError(BeamDetailingError):
    """A bar run longer than a commercial bar is too thick to be lap spliced

    Attributes:
        run_length: Cut length of the run (cm).
        diameter_mm: Bar diameter (mm).
        max_diameter_mm: Largest diameter that may be lap spliced (mm).

    References:
        ABNT NBR 6118:2026 — Section 9.5.2
    """

    def __init__(
        self, *, run_length: float, diameter_mm: float, max_diameter_mm: float
    ) -> None:
        super().__init__(
            f"A {run_length:g} cm φ{diameter_mm:g} run needs a splice, but bars "
            f"above {max_diameter_mm:g} mm cannot be lap spliced."
        )
        self.run_length = run_length
        self.diameter_mm = diameter_mm
        self.max_diameter_mm = max_diameter_mm


class LapTooLongError(BeamDetailingError):
    """The lap of a bar run does not fit in a commercial bar

    Attributes:
        lap_length: Lap length (cm).
        diameter_mm: Bar diameter (mm).
        max_bar_length: Commercial bar length (cm).
        skin: Whether the bars are skin reinforcement.

    References:
        ABNT NBR 6118:2026 — Sections 9.5.2.2 and 9.5.2.3
        ABNT NBR 7480:2024 — Section 4.5.1
    """

    def __init__(
        self,
        *,
        lap_length: float,
        diameter_mm: float,
        max_bar_length: float,
        skin: bool = False,
    ) -> None:
        bars = "skin bars" if skin else "bars"
        super().__init__(
            f"A {lap_length:g} cm lap of φ{diameter_mm:g} {bars} does not fit in a "
            f"{max_bar_length:g} cm bar."
        )
        self.lap_length = lap_length
        self.diameter_mm = diameter_mm
        self.max_bar_length = max_bar_length
        self.skin = skin


class SplicePositionError(BeamDetailingError):
    """No splice position in a window keeps the bars spliced in one section within the limit

    Attributes:
        quantity: Bars in the run.
        diameter_mm: Bar diameter (mm).
        window_start: Start of the window searched (cm).
        window_end: End of the window searched (cm).

    References:
        ABNT NBR 6118:2026 — Section 9.5.2.1, Table 9.3
    """

    def __init__(
        self,
        *,
        quantity: int,
        diameter_mm: float,
        window_start: float,
        window_end: float,
    ) -> None:
        super().__init__(
            f"No splice position for {quantity}φ{diameter_mm:g} between "
            f"{window_start:g} and {window_end:g} cm keeps the bars spliced in one "
            "section within Table 9.3."
        )
        self.quantity = quantity
        self.diameter_mm = diameter_mm
        self.window_start = window_start
        self.window_end = window_end


class StirrupSpacingTooSmallError(BeamDetailingError):
    """A stirrup spacing rounds down below the minimum spacing

    Attributes:
        spacing: Rounded spacing (cm).
        min_spacing: Minimum spacing (cm).

    References:
        ABNT NBR 6118:2026 — Section 18.3.3.2
    """

    def __init__(self, *, spacing: float, min_spacing: float) -> None:
        super().__init__(
            f"Stirrup spacing rounds down to {spacing:g} cm, below the minimum of "
            f"{min_spacing:g} cm."
        )
        self.spacing = spacing
        self.min_spacing = min_spacing


class StirrupBendUndefinedError(BeamDetailingError):
    """The norm gives no bend diameter for the stirrup bar (CA-60 above 10 mm)

    Attributes:
        diameter_mm: Stirrup bar diameter (mm).

    References:
        ABNT NBR 6118:2026 — Section 9.4.6.1, Table 9.2
    """

    def __init__(self, *, diameter_mm: float) -> None:
        super().__init__(
            f"No stirrup bend diameter for CA-60 bars with {diameter_mm} mm "
            "(φ_t > 10 mm)."
        )
        self.diameter_mm = diameter_mm
