"""Errors for elements that cannot be designed"""

from src.errors.base import BeamCalculatorError, beam_prefixed


class DesignError(BeamCalculatorError, ValueError):
    """The element cannot be designed as it is; a larger section or a stronger concrete may solve it"""


class BeamDesignError(DesignError):
    """A beam cannot be designed as it is

    Attributes:
        beam_id: Id of the beam, usually set by ``ContinuousBeam`` after the
            calculators raise; shown as a prefix of the message.
    """

    def __init__(self, message: str, *, beam_id: str | None = None) -> None:
        super().__init__(message)
        self.beam_id = beam_id

    def __str__(self) -> str:
        return beam_prefixed(self.beam_id, self.message)


class SlabDesignError(DesignError):
    """A slab cannot be designed as it is

    Attributes:
        slab_id: Id of the slab; the message already names it.
    """

    def __init__(self, message: str, *, slab_id: str) -> None:
        super().__init__(message)
        self.slab_id = slab_id
