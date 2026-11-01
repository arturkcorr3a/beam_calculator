from dataclasses import dataclass, field

from src.reinforcement.clamps import Clamps
from src.structural_elements.rebar import HookGeometry, Rebar


@dataclass
class Layer:
    """
    Represents a layer of reinforcement bars in a beam.
    """

    bars: list[Rebar]
    layer_index: int
    y_centroid_position: float = field(init=False)  # cm
    left_clamps: Clamps | None = field(default=None, init=False)
    right_clamps: Clamps | None = field(default=None, init=False)

    @property
    def area(self) -> float:
        """Returns the total area of the layer (cm²)."""
        return sum(bar.area_cm2 for bar in self.bars)

    def has_good_adherence(self, beam_height: float) -> bool:
        """
        Checks if the layer has good adherence based on the positioning inside the beam.

        Reference: ABNT NBR 6118 - Section 9.3.1
        """
        good_adherence_threshold = 30 if beam_height < 60 else beam_height - 30
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
        """Enable or disable the standard 90° hooks on one side of the layer

        Any hook geometry set before on that side is dropped.

        Args:
            left: Whether to set the left side; otherwise the right.
            enable: Whether the bars have hooks on that side.

        Raises:
            ValueError: If the layer has no bars.
        """
        if len(self.bars) == 0:
            raise ValueError("No bars in the layer to enable/disable hooks.")

        for bar in self.bars:
            if left:
                bar.left_hook_enabled = enable
                bar.left_hook_geometry = None
            else:
                bar.right_hook_enabled = enable
                bar.right_hook_geometry = None

    def set_frame_joint_hooks(self, left: bool, tip_length: float) -> None:
        """Hook the bars on one side as bent into a frame joint

        Each bar bends with its own frame-joint diameter, and every bar gets the same straight tip.

        Args:
            left: Whether to set the left side; otherwise the right.
            tip_length: Straight length after the curve (cm).

        Raises:
            ValueError: If the layer has no bars.

        References:
            ABNT NBR 6118:2026 — Section 18.2.2
        """
        self.set_hooks(left, True)
        for bar in self.bars:
            geometry = HookGeometry(
                pin_diameter=bar.steel.frame_joint_bend_diameter(bar.diameter_mm),
                tip_length=tip_length,
            )
            if left:
                bar.left_hook_geometry = geometry
            else:
                bar.right_hook_geometry = geometry

    def set_clamps(self, left: bool, clamps: Clamps | None) -> None:
        """Set the clamps that complete the anchorage on one side of the layer

        Args:
            left: Whether the clamps are on the left side; otherwise the right.
            clamps: Clamps to set, or None to remove them.
        """
        if left:
            self.left_clamps = clamps
        else:
            self.right_clamps = clamps

    def get_clamps(self, left: bool) -> Clamps | None:
        """Return the clamps on one side of the layer, or None if there are none

        Args:
            left: Whether to read the left side; otherwise the right.
        """
        return self.left_clamps if left else self.right_clamps

    def get_bar_diameters_for_print(self) -> str:
        """Returns a string representation of the bar diameters in the layer."""
        return ", ".join(f"{bar.diameter_mm}mm" for bar in self.bars)
