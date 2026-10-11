"""Apply the calculation memorial settings to the engine's logger."""

from pavement_ui.core.engine.keys import from_key, to_key
from pavement_ui.core.model.settings import LogValues
from src.config import APP_CONFIG
from src.logger import LogLevel, LogOutput, configure_logger


class LogConfigurator:
    """Reconfigure the engine logger only when its settings actually change

    Each ``configure_logger`` call opens a new log file, so repeated calls with
    the same settings are skipped.
    """

    def __init__(self) -> None:
        self._current = LogValues(
            level_key=to_key(APP_CONFIG.log_level),
            output_key=to_key(APP_CONFIG.log_output),
        )

    def apply(self, log: LogValues) -> None:
        """Configure the logger with log, if different from the current settings"""
        if log == self._current:
            return
        level = from_key(LogLevel, log.level_key)
        output = from_key(LogOutput, log.output_key)
        APP_CONFIG.log_level = level
        APP_CONFIG.log_output = output
        configure_logger(level, output)
        self._current = log
