"""Assemble a fresh engine Pavement from the records."""

from pavement_ui.core.engine import config_mapper, element_factory
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.model.settings import ConfigValues
from src.pavement_elements.pavement import Pavement


def assemble(records: PavementRecords) -> Pavement:
    """Build a new, unresolved pavement from the records, in registration order

    A new pavement is built for every operation: the engine has no removal and
    keeps resolved state on its elements (docs/UI_SPEC.md §3, decision 1).

    Raises:
        ValueError: If the engine refuses a record (inclusion rules).
    """
    pavement = Pavement()
    for record in records.pillars:
        pavement.add_pillar(element_factory.pillar(record))
    for record in records.beams:
        pavement.add_beam(element_factory.beam(record))
    for record in records.slabs:
        pavement.add_slab(element_factory.slab(record))
    return pavement


def build_pavement(records: PavementRecords, config: ConfigValues) -> Pavement:
    """Apply the settings to the engine, then ``assemble`` the records

    Raises:
        ValueError: If the engine refuses a record (inclusion rules).
    """
    config_mapper.apply(config)
    return assemble(records)
