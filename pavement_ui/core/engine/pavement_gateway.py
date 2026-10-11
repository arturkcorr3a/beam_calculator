"""PavementGateway: the engine behind the PavementEngine port."""

from pavement_ui.core.engine import element_factory
from pavement_ui.core.engine.design_job import DesignJob
from pavement_ui.core.engine.log_configurator import apply_log_settings
from pavement_ui.core.engine.options_reader import read_options
from pavement_ui.core.engine.pavement_builder import assemble, build_pavement
from pavement_ui.core.engine.readers.plan_reader import read_plan
from pavement_ui.core.engine.rule_errors import engine_rules
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.model.records import BeamRecord, PillarRecord, SlabRecord
from pavement_ui.core.model.settings import ConfigValues, LogValues
from pavement_ui.core.options import EngineOptions
from pavement_ui.core.ports import Job
from pavement_ui.core.results.outcomes import DesignOutcome
from pavement_ui.core.results.plan_geometry import PlanGeometry
from src.logger import suppress_logging


class PavementGateway:
    """Apply the engine's rules, validation and plan resolution to records

    Inclusion checks and the plan are not part of a calculation, so they run
    with the calculation memorial silenced; validation is logged.
    """

    def __init__(self) -> None:
        self._log = LogValues()  # passed on to design jobs (they run in the worker)
        self._options: EngineOptions | None = None

    def options(self) -> EngineOptions:
        if self._options is None:
            with suppress_logging():
                self._options = read_options()
        return self._options

    def check_pillar(self, record: PillarRecord) -> None:
        with suppress_logging(), engine_rules():
            element_factory.pillar(record)

    def check_beam(self, record: BeamRecord) -> None:
        with suppress_logging(), engine_rules():
            element_factory.beam(record)

    def check_slab(self, record: SlabRecord) -> None:
        with suppress_logging(), engine_rules():
            element_factory.slab(record)

    def validate(self, records: PavementRecords, config: ConfigValues) -> None:
        with engine_rules():
            build_pavement(records, config).validate()

    def plan_geometry(self, records: PavementRecords) -> PlanGeometry:
        with suppress_logging():
            return read_plan(records, assemble(records))

    def make_design_job(
        self, records: PavementRecords, config: ConfigValues
    ) -> Job[DesignOutcome]:
        return DesignJob(records, config, self._log)

    def apply_log_settings(self, log: LogValues) -> None:
        self._log = log
        apply_log_settings(log)
