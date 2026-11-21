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
