"""Shared helpers for the drawing tests."""

from collections.abc import Sequence
from math import isclose
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from ezdxf import filemanagement
from ezdxf.document import Drawing as DxfDocument

from src.detailing.bar_schedule import build_schedule
from src.detailing.detailing_beam import DetailingBeam
from src.detailing.quantities import build_quantities
from src.pavement_elements.pavement import Pavement


def close(
    actual: float | Sequence[float],
    expected: float | Sequence[float],
    tol: float = 1e-6,
) -> bool:
    """Return whether two numbers, or two sequences of numbers, match within tol"""
    if isinstance(actual, (int, float)) or isinstance(expected, (int, float)):
        if not isinstance(actual, (int, float)) or not isinstance(
            expected, (int, float)
        ):
            return False
        return isclose(actual, expected, abs_tol=tol)
    return len(actual) == len(expected) and all(
        isclose(a, e, abs_tol=tol) for a, e in zip(actual, expected, strict=True)
    )


def detailings(pavement: Pavement) -> list[DetailingBeam]:
    """Return the detailing of every beam of a resolved pavement, in pavement order"""
    return [
        beam.detailing for beam in pavement.beams.values() if beam.detailing is not None
    ]


def read_dxf(path: Path) -> DxfDocument:
    """Read a DXF file (typed wrapper: ezdxf leaves the path parameter partly unknown)"""
    return filemanagement.readfile(path)  # pyright: ignore[reportUnknownMemberType]


def fake_pavement(*beams: DetailingBeam) -> Pavement:
    """Return a stand-in pavement holding detailed beams, in order"""
    holders = {
        beam.beam_id: SimpleNamespace(id=beam.beam_id, detailing=beam) for beam in beams
    }

    def detailed() -> list[DetailingBeam]:
        return [
            holder.detailing
            for holder in holders.values()
            if holder.detailing is not None
        ]

    return cast(
        Pavement,
        SimpleNamespace(
            beams=holders,
            bar_schedule=lambda: build_schedule(detailed()),
            quantities=lambda: build_quantities(detailed()),
        ),
    )
