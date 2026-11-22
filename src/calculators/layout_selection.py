from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from src.errors import EnginePreconditionError

type LayerDiameters = tuple[tuple[float, ...], ...]  # bar diameters (mm) per layer
type LayoutSignature = tuple[LayerDiameters, LayerDiameters]  # tensioned, compressed


@dataclass(frozen=True)
class LayoutPass:
    """One pass of the effective-depth iteration: the bars chosen and what they were chosen for.

    Attributes:
        signature: Bar diameters (mm) per layer of the tensioned and compressed
            reinforcements; identifies the layout.
        tensioned_required: Tensioned area the layout was chosen for (cm²).
        compressed_required: Compressed area the layout was chosen for (cm²); 0 when
            singly reinforced.
        tensioned_provided: Chosen tensioned area (cm²).
        compressed_provided: Chosen compressed area (cm²); 0 when singly reinforced.
    """

    signature: LayoutSignature
    tensioned_required: float
    compressed_required: float
    tensioned_provided: float
    compressed_provided: float

    @property
    def total_provided(self) -> float:
        """Chosen tensioned + compressed area (cm²)."""
        return self.tensioned_provided + self.compressed_provided

    def describe(self) -> str:
        """Describe the layout as bar counts, e.g. ``3x16mm`` or ``2x20mm + 2x10mm (compressed)``"""
        tensioned, compressed = self.signature
        description = _count_bars(tensioned)
        if compressed:
            description += f" + {_count_bars(compressed)} (compressed)"
        return description


def _count_bars(layers: LayerDiameters) -> str:
    """Format the bars of a reinforcement as counts per diameter, largest first"""
    counter = Counter(int(diameter) for layer in layers for diameter in layer)
    return ", ".join(
        f"{count}x{diameter}mm"
        for diameter, count in sorted(counter.items(), reverse=True)
    )


def select_layout(
    passes: Sequence[LayoutPass], final_requirement: tuple[float, float]
) -> tuple[LayoutPass, bool]:
    """Pick the layout to keep when the effective-depth iteration does not converge

    A pass is safe when its chosen areas cover the areas required at its own
    effective depth. Pass i's own-d requirement is what pass i + 1 was chosen
    for; the last pass's is ``final_requirement``. The cheapest safe pass is
    kept; if none is safe, the one with the largest chosen area (the most
    conservative) is kept instead.

    Args:
        passes: Consecutive passes to choose from (non-empty).
        final_requirement: Tensioned and compressed areas (cm²) required at the
            last pass's own effective depth.

    Returns:
        The kept pass, and whether it is safe.

    Raises:
        EnginePreconditionError: If ``passes`` is empty.
    """
    if not passes:
        raise EnginePreconditionError("At least one pass is needed to select a layout.")

    own_requirements = [
        (following.tensioned_required, following.compressed_required)
        for following in passes[1:]
    ] + [final_requirement]
    safe = [
        layout_pass
        for layout_pass, (tensioned, compressed) in zip(
            passes, own_requirements, strict=True
        )
        if layout_pass.tensioned_provided >= tensioned
        and layout_pass.compressed_provided >= compressed
    ]
    if safe:
        return min(safe, key=lambda layout_pass: layout_pass.total_provided), True
    return max(passes, key=lambda layout_pass: layout_pass.total_provided), False
