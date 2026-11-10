"""Ports: what the core and the presentation need from the engine.

Implemented by the adapters in ``pavement_ui.core.engine`` and injected by
``pavement_ui.app``, so nothing else depends on the engine (docs/UI_SPEC.md §3).
Every method raising ``EngineRuleError`` passes on the engine's original text.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pavement_ui.core.model.isolated_beam_input import IsolatedBeamInput
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.model.records import (
    BeamRecord,
    PillarRecord,
    SlabRecord,
    WallRecord,
)
from pavement_ui.core.model.settings import ConfigValues, LogValues
from pavement_ui.core.options import EngineOptions
from pavement_ui.core.results.outcomes import DesignOutcome, IsolatedBeamOutcome
from pavement_ui.core.results.plan_geometry import PlanGeometry
from pavement_ui.core.results.vector_drawing import VectorDrawing


class Job[T](Protocol):
    """Self-contained engine work that may run in a worker thread"""

    def run(self) -> T: ...


class PavementEngine(Protocol):
    """Rules, validation, plan geometry and design of the pavement"""

    def options(self) -> EngineOptions: ...

    def check_pillar(self, record: PillarRecord) -> None:
        """Apply the engine's inclusion rules; raises EngineRuleError."""
        ...

    def check_beam(self, record: BeamRecord) -> None:
        """Apply the engine's inclusion rules; raises EngineRuleError."""
        ...

    def check_slab(self, record: SlabRecord) -> None:
        """Apply the engine's inclusion rules; raises EngineRuleError."""
        ...

    def validate(self, records: PavementRecords, config: ConfigValues) -> None:
        """Validate the structure; raises EngineRuleError on the first error."""
        ...

    def plan_geometry(self, records: PavementRecords) -> PlanGeometry: ...

    def make_design_job(
        self, records: PavementRecords, config: ConfigValues, name: str | None = None
    ) -> Job[DesignOutcome]:
        """Return the design job; name is the pavement's, for the sheets' title blocks."""
        ...

    def apply_log_settings(self, log: LogValues) -> None: ...


@dataclass(frozen=True, slots=True)
class LoadedProject:
    """Records and settings read from a project file"""

    records: PavementRecords
    config: ConfigValues


class ProjectStore(Protocol):
    """Project files; both methods raise PersistenceError"""

    def save(
        self, path: Path, records: PavementRecords, config: ConfigValues
    ) -> None: ...

    def open(self, path: Path) -> LoadedProject: ...


class DrawingExporter(Protocol):
    """Write the engine's drawings in CAD formats"""

    def write_dxf(self, drawing: VectorDrawing, path: Path) -> None:
        """Write the drawing to a DXF file (cm, one layer per drawing layer)

        Raises:
            OSError: If the file cannot be written.
        """
        ...


class IsolatedBeamEngine(Protocol):
    """The isolated beam calculator: a continuous beam on pillars"""

    def self_weight_kn_m(self, width_cm: float, height_cm: float) -> float:
        """Return the own-weight load of a b × h section (kN/m)."""
        ...

    def wall_load_kn_m(self, wall: WallRecord, height_m: float) -> float:
        """Return the load of a wall of the given height (kN/m)

        Raises:
            KeyError: If the masonry, thickness or coating is not tabulated.
        """
        ...

    def make_job(
        self, data: IsolatedBeamInput, config: ConfigValues, log: LogValues
    ) -> Job[IsolatedBeamOutcome]: ...
