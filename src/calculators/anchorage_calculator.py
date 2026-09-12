# Calculations of necessary anchorage length

# Input: whatever is necessary

# Output: length in cm

from src.calculators.stirrup_calculator import StirrupCalculator


class AnchorageCalculator:
    def __init__(self, stirrup_calculator: StirrupCalculator):
        self.stirrup_calculator = stirrup_calculator

    @property
    def _moment_shift_length(self):
        return self.stirrup_calculator.calculate_moment_shift()
