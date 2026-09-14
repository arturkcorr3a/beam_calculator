from dataclasses import dataclass, field

from src.structural_elements.rebar import Rebar


@dataclass
class Layer:
    """
    Represents a layer of reinforcement bars in a beam.
    """

    bars: list[Rebar]
    layer_index: int
    y_centroid_position: float = field(init=False)  # cm

    @property
    def area(self) -> float:
        """Returns the total area of the layer (cm²)."""
        return sum(bar.area_cm2 for bar in self.bars)

    def has_good_adherence(self, beam_height: float) -> bool:
        """
        Checks if the layer has good adherence based on the positioning inside the beam.

        Reference: ABNT NBR 6118 - Section 9.3.1
        """
        if beam_height < 60:
            good_adherence_threshold = 30
        else:
            good_adherence_threshold = beam_height - 30
        return self.y_centroid_position <= good_adherence_threshold

    def set_anchorage_length(
        self, necessary_anchorage_length: float, left: bool
    ) -> None:
        if len(self.bars) == 0:
            raise ValueError("No bars in the layer to set anchorage length.")

        for bar in self.bars:
            if left:
                bar.left_length = necessary_anchorage_length
            else:
                bar.right_length = necessary_anchorage_length

    def set_hooks(self, left: bool, enable: bool) -> None:
        if len(self.bars) == 0:
            raise ValueError("No bars in the layer to enable/disable hooks.")

        for bar in self.bars:
            if left:
                bar.left_hook_enabled = enable
            else:
                bar.right_hook_enabled = enable
