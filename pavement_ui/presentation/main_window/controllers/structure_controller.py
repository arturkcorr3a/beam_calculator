"""Flows of the Cálculo menu: validate the structure, design it in the background (F7, F8)."""

from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from pavement_ui.core.results.outcomes import (
    DesignOutcome,
    DesignSuccess,
    RuleFailure,
    UnexpectedFailure,
)
from pavement_ui.core.session import ProjectSession
from pavement_ui.core.state import ValidationStatus
from pavement_ui.presentation.dialogs import messages
from pavement_ui.presentation.execution.engine_executor import EngineExecutor


class StructureController:
    """Runs actValidate and actDesign

    While a design runs, the executor reports busy: the window shows its busy
    overlay and disables editing.

    Args:
        on_success: Called on the UI thread with the results of a successful design.
    """

    def __init__(
        self,
        session: ProjectSession,
        executor: EngineExecutor,
        window: QWidget,
        on_success: Callable[[DesignSuccess], None],
    ) -> None:
        self._session = session
        self._executor = executor
        self._window = window
        self._on_success = on_success

    def validate(self) -> None:
        """Validate with the engine and report the first error, or that it is valid"""
        state = self._session.validate()
        if state.status is ValidationStatus.VALID:
            messages.show_validation_ok(self._window)
        else:
            messages.show_validation_error(self._window, state.message or "")

    def design(self) -> None:
        """Validate, then dimension the pavement in the engine's worker process"""
        job = self._session.begin_design()
        if job is None:
            message = self._session.validation.message or ""
            messages.show_validation_error(self._window, message)
            return
        self._executor.submit(job, self._on_done, self._on_error)

    def _on_done(self, outcome: DesignOutcome) -> None:
        self._session.finish_design(outcome)
        match outcome:
            case DesignSuccess():
                self._on_success(outcome)
            case RuleFailure(message=message):
                messages.show_design_rule_error(self._window, message)
            case UnexpectedFailure():
                messages.show_design_unexpected(self._window, outcome)

    def _on_error(self, message: str, details: str) -> None:
        """The worker could not run the job (e.g. it crashed): an unexpected failure"""
        self._on_done(UnexpectedFailure(message, details))
