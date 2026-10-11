"""ProjectSession: the use cases of the main window (docs/UI_SPEC.md §6.8)."""

from pathlib import Path

from pavement_ui.core.errors import EngineRuleError, SessionBusyError
from pavement_ui.core.events import EventBus, SessionEvent
from pavement_ui.core.model.element_kind import ElementKind
from pavement_ui.core.model.id_generator import IdGenerator
from pavement_ui.core.model.id_parsing import parse_id_list
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.model.records import (
    BeamRecord,
    PillarRecord,
    SlabRecord,
    WallRecord,
)
from pavement_ui.core.model.settings import ConfigValues, LogValues
from pavement_ui.core.options import EngineOptions
from pavement_ui.core.ports import Job, PavementEngine, ProjectStore
from pavement_ui.core.results.outcomes import DesignOutcome, DesignSuccess
from pavement_ui.core.results.plan_geometry import PlanGeometry
from pavement_ui.core.state import DesignState, ValidationState, ValidationStatus

_ALL_EVENTS_BUT_START = tuple(
    e for e in SessionEvent if e is not SessionEvent.DESIGN_STARTED
)


class ProjectSession:
    """Owns what the user registered and runs every operation on it

    State is read through the attributes; every change publishes events on the
    bus. Rules and calculations are the engine's; ``EngineRuleError`` and
    ``PersistenceError`` propagate to the caller. While a design runs, every
    change raises ``SessionBusyError``.
    """

    def __init__(
        self,
        engine: PavementEngine,
        store: ProjectStore,
        bus: EventBus,
        ids: IdGenerator | None = None,
    ) -> None:
        self._engine = engine
        self._store = store
        self._bus = bus
        self._ids = ids or IdGenerator()
        self.records = PavementRecords()
        self.config = ConfigValues()
        self.log = LogValues()
        self.validation = ValidationState()
        self.design = DesignState()
        self.current_path: Path | None = None
        self.options: EngineOptions = engine.options()

    @property
    def last_success(self) -> DesignSuccess | None:
        """Results of the last design, if it succeeded"""
        outcome = self.design.last_outcome
        return outcome if isinstance(outcome, DesignSuccess) else None

    # --- Editing ---------------------------------------------------------------

    def add_pillar(
        self, x_m: float, y_m: float, width_cm: float, depth_cm: float
    ) -> PillarRecord:
        """Register a pillar with the next ID; raises EngineRuleError if refused"""
        self._ensure_idle()
        record = PillarRecord(
            self._ids.peek(ElementKind.PILLAR), x_m, y_m, width_cm, depth_cm
        )
        self._engine.check_pillar(record)
        self._commit(ElementKind.PILLAR, self.records.with_pillar(record))
        return record

    def add_beam(
        self,
        pillar_ids_text: str,
        reference_text: str,
        width_cm: float,
        alignment_key: str,
        wall: WallRecord,
    ) -> BeamRecord:
        """Register a beam with the next ID; raises EngineRuleError if refused

        Args:
            pillar_ids_text: Pillar IDs as typed (see ``parse_id_list``).
            reference_text: Reference pillar ID as typed.
            width_cm: Beam width bw (cm).
        """
        self._ensure_idle()
        record = BeamRecord(
            self._ids.peek(ElementKind.BEAM),
            parse_id_list(pillar_ids_text),
            reference_text.strip().upper(),
            width_cm,
            alignment_key,
            wall,
        )
        self._engine.check_beam(record)
        self._commit(ElementKind.BEAM, self.records.with_beam(record))
        return record

    def add_slab(
        self, corner_ids_text: str, usage_key: str, lowered_cm: int
    ) -> SlabRecord:
        """Register a slab with the next ID; raises EngineRuleError if refused

        Args:
            corner_ids_text: Corner pillar IDs as typed (see ``parse_id_list``).
            lowered_cm: Lowering below the floor level (cm).
        """
        self._ensure_idle()
        record = SlabRecord(
            self._ids.peek(ElementKind.SLAB),
            parse_id_list(corner_ids_text),
            usage_key,
            lowered_cm,
        )
        self._engine.check_slab(record)
        self._commit(ElementKind.SLAB, self.records.with_slab(record))
        return record

    def remove(self, kind: ElementKind, element_id: str) -> None:
        """Remove one element; its dependents are kept [Manual]"""
        self._ensure_idle()
        match kind:
            case ElementKind.PILLAR:
                records = self.records.without_pillar(element_id)
            case ElementKind.BEAM:
                records = self.records.without_beam(element_id)
            case ElementKind.SLAB:
                records = self.records.without_slab(element_id)
        self._set_records(records)

    def clear_pavement(self) -> None:
        """Remove every element; settings and the ID numbering are kept"""
        self._ensure_idle()
        self._set_records(PavementRecords())

    # --- Settings ---------------------------------------------------------------

    def update_config(self, config: ConfigValues, log: LogValues) -> None:
        """Replace the settings and apply the log settings to the engine"""
        self._ensure_idle()
        self.config = config
        self.log = log
        self._engine.apply_log_settings(log)
        self._bus.publish(SessionEvent.CONFIG_CHANGED)

    # --- Engine queries ---------------------------------------------------------

    def plan_geometry(self) -> PlanGeometry:
        """Return the plan of the current records, resolved by the engine"""
        return self._engine.plan_geometry(self.records)

    def validate(self) -> ValidationState:
        """Validate the structure with the engine (first error only)"""
        self._ensure_idle()
        try:
            self._engine.validate(self.records, self.config)
        except EngineRuleError as error:
            self.validation = ValidationState(ValidationStatus.INVALID, error.message)
        else:
            self.validation = ValidationState(ValidationStatus.VALID)
        self._bus.publish(SessionEvent.VALIDATION_CHANGED)
        return self.validation

    # --- Design -----------------------------------------------------------------

    def begin_design(self) -> Job[DesignOutcome] | None:
        """Validate and, if valid, mark the design as running

        Returns:
            The job to run (possibly in a worker), or None if the structure is invalid.
        """
        if self.validate().status is not ValidationStatus.VALID:
            return None
        job = self._engine.make_design_job(self.records, self.config)
        self.design = DesignState(running=True, last_outcome=self.design.last_outcome)
        self._bus.publish(SessionEvent.DESIGN_STARTED)
        return job

    def finish_design(self, outcome: DesignOutcome) -> None:
        """Store the outcome of the running design"""
        self.design = DesignState(running=False, last_outcome=outcome)
        self._bus.publish(SessionEvent.DESIGN_FINISHED)

    # --- Project files ----------------------------------------------------------

    def new_project(self) -> None:
        """Start over: no elements, default settings, no file, new numbering"""
        self._ensure_idle()
        self._replace_project(PavementRecords(), ConfigValues(), None)

    def open(self, path: Path) -> None:
        """Replace everything with a project file; raises PersistenceError"""
        self._ensure_idle()
        loaded = self._store.open(path)
        self._replace_project(loaded.records, loaded.config, path)

    def check_before_save(self) -> str | None:
        """Validate before saving

        Returns:
            The engine's first error if the structure is invalid (a file with
            references to removed elements cannot be reopened), else None.
        """
        state = self.validate()
        return state.message if state.status is ValidationStatus.INVALID else None

    def save(self, path: Path | None = None) -> Path:
        """Save to path, or to the current file; raises PersistenceError

        Raises:
            ValueError: If no path is given and the project was never saved.
        """
        self._ensure_idle()
        target = path or self.current_path
        if target is None:
            raise ValueError("No file to save to; a path is required.")
        self._store.save(target, self.records, self.config)
        self.current_path = target
        self._bus.publish(SessionEvent.FILE_CHANGED)
        return target

    # --- Internals --------------------------------------------------------------

    def _ensure_idle(self) -> None:
        if self.design.running:
            raise SessionBusyError("A design is running.")

    def _commit(self, kind: ElementKind, records: PavementRecords) -> None:
        self._ids.commit(kind)
        self._set_records(records)

    def _set_records(self, records: PavementRecords) -> None:
        self.records = records
        self.validation = ValidationState()
        self._bus.publish(SessionEvent.RECORDS_CHANGED)
        self._bus.publish(SessionEvent.VALIDATION_CHANGED)

    def _replace_project(
        self, records: PavementRecords, config: ConfigValues, path: Path | None
    ) -> None:
        self.records = records
        self.config = config
        self.current_path = path
        self.validation = ValidationState()
        self.design = DesignState()
        self._ids.reset_after(records.counts())
        for event in _ALL_EVENTS_BUT_START:
            self._bus.publish(event)
