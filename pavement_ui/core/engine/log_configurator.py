"""Apply the calculation memorial settings to the engine's logger."""

from pavement_ui.core.engine.keys import from_key, to_key
from pavement_ui.core.model.settings import LogValues
from src.config import APP_CONFIG
from src.logger import LogLevel, set_log_level


class LogConfigurator:
    """Change the engine logger level only when it actually changes

    The level is the only setting the UI exposes; the logger keeps its default
    output and its current log file.
    """

    def __init__(self) -> None:
        self._current = LogValues(level_key=to_key(APP_CONFIG.log_level))

    def apply(self, log: LogValues) -> None:
        """Set the logger level from log, if different from the current one"""
        if log == self._current:
            return
        level = from_key(LogLevel, log.level_key)
        APP_CONFIG.log_level = level
        set_log_level(level)
        self._current = log


_THIS_PROCESS = LogConfigurator()


def apply_log_settings(log: LogValues) -> None:
    """Configure this process's engine logger (the UI and the worker each have one)"""
    _THIS_PROCESS.apply(log)
