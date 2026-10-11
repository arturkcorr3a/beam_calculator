"""IsolatedBeamCalculator: the engine behind the IsolatedBeamEngine port."""

import traceback
from dataclasses import dataclass, replace

from pavement_ui.core.engine import config_mapper
from pavement_ui.core.engine.keys import cm_from_m, from_key, m_from_cm
from pavement_ui.core.engine.log_configurator import apply_log_settings
from pavement_ui.core.engine.readers.design_point_reader import read_point
from pavement_ui.core.engine.readers.diagram_sampler import sample
from pavement_ui.core.engine.readers.reinforcement_reader import read_stirrup
from pavement_ui.core.model.isolated_beam_input import IsolatedBeamInput
from pavement_ui.core.model.settings import ConfigValues, LogValues
from pavement_ui.core.ports import Job
from pavement_ui.core.results.beam_result import BeamResult, SpanResult, SupportMark
from pavement_ui.core.results.outcomes import (
    IsolatedBeamOutcome,
    IsolatedBeamSuccess,
    IsolatedInvalidInput,
    IsolatedNotVerified,
    UnexpectedFailure,
)
from src.calculators.simply_supported_beam import (
    SimplySupportedBeamDesign,
    design_simply_supported_beam,
)
from src.loading.linear_loads import LinearLoads
from src.properties.concrete import Concrete
from src.properties.steel import Steel
from src.structural_elements.rectangular_beam import RectangularBeam

_CM2_PER_M2 = 10_000.0
_SUPPORT_LABELS = ("A", "B")  # symbols of the two supports, like pillar IDs


def _result(design: SimplySupportedBeamDesign) -> BeamResult:
    """Read the facade's result into the same model as a pavement beam."""
    section = design.section
    length_m = m_from_cm(section.length)
    supports = (
        SupportMark(0.0, _SUPPORT_LABELS[0]),
        SupportMark(length_m, _SUPPORT_LABELS[1]),
    )
    span = SpanResult(
        index=1,
        start_label=_SUPPORT_LABELS[0],
        end_label=_SUPPORT_LABELS[1],
        length_m=length_m,
        effective_length_m=length_m,
        start_m=0.0,
        end_m=length_m,
        g_kn_m=design.self_weight,
        q_kn_m=0.0,
        vk_kn=design.characteristic_shear_force,
        vsd_kn=design.stirrups.calculator.design_shear_force,
        stirrup=read_stirrup(design.stirrups),
    )
    moment, shear = sample(design.analysis, (0.0, section.length))
    return BeamResult(
        beam_id="",
        width_cm=section.width,
        height_cm=section.height,
        cover_cm=RectangularBeam.nominal_covering,
        supports=supports,
        spans=(span,),
        points=(read_point(design.calculator, supports),),
        moment=moment,
        shear=shear,
    )


@dataclass(frozen=True, slots=True)
class IsolatedBeamJob:
    """Dimension one simply supported beam; self-contained for a worker thread"""

    data: IsolatedBeamInput
    config: ConfigValues
    log: LogValues = LogValues()

    def run(self) -> IsolatedBeamOutcome:
        """Apply the settings (with the window's concrete) and dimension the beam

        Returns:
            Success; IsolatedInvalidInput if the engine refuses the section;
            IsolatedNotVerified if it cannot be dimensioned; UnexpectedFailure.
        """
        try:
            apply_log_settings(self.log)  # this runs in the engine's worker process
            # the cover reads APP_CONFIG.pavement_concrete (bug M2)
            config_mapper.apply(
                replace(self.config, concrete_key=self.data.concrete_key)
            )
            try:
                section = RectangularBeam(
                    cm_from_m(self.data.length_m),
                    self.data.width_cm,
                    self.data.height_cm,
                    from_key(Concrete, self.data.concrete_key),
                    from_key(Steel, self.config.steel_key),
                )
            except ValueError as error:
                return IsolatedInvalidInput(str(error))
            try:
                design = design_simply_supported_beam(section)
            except ValueError as error:
                return IsolatedNotVerified(str(error))
            return IsolatedBeamSuccess(_result(design), design.self_weight)
        except Exception as error:  # noqa: BLE001 — every other failure is reported
            return UnexpectedFailure(str(error), traceback.format_exc())


class IsolatedBeamCalculator:
    """Dimension isolated beams and compute their own weight"""

    def self_weight_kn_m(self, width_cm: float, height_cm: float) -> float:
        return LinearLoads.get_concrete_element_own_weight(
            width_cm * height_cm / _CM2_PER_M2
        )

    def make_job(
        self, data: IsolatedBeamInput, config: ConfigValues, log: LogValues
    ) -> Job[IsolatedBeamOutcome]:
        return IsolatedBeamJob(data, config, log)
