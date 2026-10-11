"""The pavement design job: self-contained, so it can run in a worker thread."""

import traceback
from dataclasses import dataclass

from pavement_ui.core.engine.pavement_builder import build_pavement
from pavement_ui.core.engine.readers import pavement_reader
from pavement_ui.core.engine.rule_errors import rule_message
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.model.settings import ConfigValues
from pavement_ui.core.results.outcomes import (
    DesignOutcome,
    RuleFailure,
    UnexpectedFailure,
)


@dataclass(frozen=True, slots=True)
class DesignJob:
    """Dimension the pavement described by immutable copies of the records

    Shares no object with the UI. The engine's global APP_CONFIG and logger are
    serialized by the caller (one engine job at a time, docs/UI_SPEC.md §3).
    """

    records: PavementRecords
    config: ConfigValues

    def run(self) -> DesignOutcome:
        """Build a fresh pavement, resolve it and read the results

        Returns:
            DesignSuccess, RuleFailure (engine rule, original text) or
            UnexpectedFailure (any other error, with traceback).
        """
        try:
            pavement = build_pavement(self.records, self.config)
            pavement.resolve()
            # read inside the job: the cover depends on APP_CONFIG
            return pavement_reader.read(pavement)
        except (ValueError, KeyError) as error:
            return RuleFailure(rule_message(error))
        except Exception as error:  # noqa: BLE001 — every other failure is reported, not raised
            return UnexpectedFailure(str(error), traceback.format_exc())
