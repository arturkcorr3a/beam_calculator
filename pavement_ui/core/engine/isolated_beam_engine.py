"""IsolatedBeamCalculator: the engine behind the IsolatedBeamEngine port."""

import traceback
from dataclasses import dataclass

from pavement_ui.core.engine import config_mapper, element_factory
from pavement_ui.core.engine.keys import cm_from_m
from pavement_ui.core.engine.log_configurator import apply_log_settings
from pavement_ui.core.engine.readers.beam_reader import read_beam
from pavement_ui.core.engine.readers.materials_reader import read_materials
from pavement_ui.core.engine.readers.quantities_reader import read_beam_quantity
from pavement_ui.core.model import isolated_beam_input as model
from pavement_ui.core.model.records import WallRecord
from pavement_ui.core.model.settings import ConfigValues, LogValues
from pavement_ui.core.ports import Job
from pavement_ui.core.results.outcomes import (
    IsolatedBeamOutcome,
    IsolatedBeamSuccess,
    IsolatedInvalidInput,
    IsolatedNotVerified,
    UnexpectedFailure,
)
from src.calculators import isolated_beam as engine
from src.loading.linear_loads import LinearLoads
from src.pavement_elements.continuous_beam import ContinuousBeam
from src.pavement_elements.pillar import Pillar

_CM2_PER_M2 = 10_000.0


def _load(load: model.IsolatedLoadInput) -> engine.IsolatedLoad:
    match load:
        case model.OwnWeightLoad():
            return engine.OwnWeightLoad(load.span_index)
        case model.WallLoad():
            return engine.WallLoad(
                element_factory.wall(load.wall), load.height_m, load.span_index
            )
        case model.CustomLoad():
            return engine.CustomLoad(
                load.label,
                load.value_kn_m,
                load.variable,
                load.psi_2,
                load.span_index,
            )


def _build(data: model.IsolatedBeamInput) -> tuple[ContinuousBeam, dict[str, Pillar]]:
    """Build the loaded beam on its pillars

    Raises:
        ValueError, KeyError: If the engine refuses the inputs.
    """
    return engine.build_isolated_beam(
        [cm_from_m(length) for length in data.span_lengths_m],
        data.width_cm,
        data.height_cm,
        [engine.IsolatedPillar(p.width_cm, p.depth_cm, p.pinned) for p in data.pillars],
        [_load(load) for load in data.loads],
    )


@dataclass(frozen=True, slots=True)
class IsolatedBeamJob:
    """Dimension and detail one isolated beam; self-contained for a worker process"""

    data: model.IsolatedBeamInput
    config: ConfigValues
    log: LogValues = LogValues()

    def run(self) -> IsolatedBeamOutcome:
        """Apply the settings, then build, dimension, detail and read the beam

        Returns:
            Success; IsolatedInvalidInput if the engine refuses the inputs;
            IsolatedNotVerified if the beam cannot be dimensioned or detailed;
            UnexpectedFailure.
        """
        try:
            apply_log_settings(self.log)  # this runs in the engine's worker process
            config_mapper.apply(self.config)
            try:
                beam, pillars = _build(self.data)
            except (ValueError, KeyError) as error:
                return IsolatedInvalidInput(str(error))
            try:
                beam.dimension(pillars)
                detailing = engine.detail_isolated_beam(beam)
            except ValueError as error:
                return IsolatedNotVerified(str(error))
            # read inside the job: the cover and the sheet's notes read APP_CONFIG
            return IsolatedBeamSuccess(
                read_beam(beam, pillars),
                read_materials(),
                read_beam_quantity(detailing),
            )
        except Exception as error:  # noqa: BLE001 — every other failure is reported
            return UnexpectedFailure(str(error), traceback.format_exc())


class IsolatedBeamCalculator:
    """Dimension isolated beams and compute their live loads"""

    def self_weight_kn_m(self, width_cm: float, height_cm: float) -> float:
        return LinearLoads.get_concrete_element_own_weight(
            width_cm * height_cm / _CM2_PER_M2
        )

    def wall_load_kn_m(self, wall: WallRecord, height_m: float) -> float:
        return LinearLoads.get_wall_load(
            *element_factory.wall(wall).get_parameters_for_load(), height_m
        )

    def make_job(
        self, data: model.IsolatedBeamInput, config: ConfigValues, log: LogValues
    ) -> Job[IsolatedBeamOutcome]:
        return IsolatedBeamJob(data, config, log)
