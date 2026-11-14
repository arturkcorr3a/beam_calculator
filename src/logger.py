from __future__ import annotations

import inspect
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import IO, TypeVar

import platformdirs
from rich.console import Console
from rich.markup import escape


class LogLevel(IntEnum):
    PROPERTY = 1
    OPERATION = 2
    ITERATION = 3
    ELEMENT = 4
    INTERACTION = 5
    GENERAL = 6
    DISABLED = 7


class LogOutput(StrEnum):
    CONSOLE = "console"
    FILE = "file"
    BOTH = "both"


_LEVEL_STYLES: dict[LogLevel, str] = {
    LogLevel.PROPERTY: "dim",
    LogLevel.OPERATION: "cyan",
    LogLevel.ITERATION: "blue",
    LogLevel.ELEMENT: "green",
    LogLevel.INTERACTION: "yellow",
    LogLevel.GENERAL: "bold white",
}


def default_logs_dir() -> Path:
    """Folder of the log files: the user's log folder when packaged, else logs/

    The packaged app's install folder is read-only, so its logs go to the
    system's per-user log folder.
    """
    if getattr(sys, "frozen", False):  # set by PyInstaller
        return Path(platformdirs.user_log_dir("PavementDesigner", appauthor=False))
    return Path(__file__).parent.parent / "logs"


_LOGS_DIR = default_logs_dir()


class BeamLogger:
    def __init__(self, level: LogLevel, output: LogOutput) -> None:
        self._level = level
        self._output = output
        self._console = Console(highlight=False)
        self._file_console: Console | None = None
        self._log_file: IO[str] | None = None

        if output in (LogOutput.FILE, LogOutput.BOTH):
            self._open_log_file()

    def _open_log_file(self) -> None:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%dT%H-%M-%S")
        log_path = _LOGS_DIR / f"beam_calculator_{timestamp}.log"
        self._log_file = open(log_path, "w", encoding="utf-8")  # noqa: SIM115
        self._file_console = Console(
            file=self._log_file,
            no_color=True,
            highlight=False,
        )

    def configure(self, level: LogLevel, output: LogOutput) -> None:
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None
            self._file_console = None
        self._level = level
        self._output = output
        if output in (LogOutput.FILE, LogOutput.BOTH):
            self._open_log_file()

    def set_level(self, level: LogLevel) -> None:
        """Change the level threshold, keeping the current output and log file

        Unlike ``configure``, the open log file (if any) is neither closed nor
        replaced, so no new file is created.
        """
        self._level = level

    @contextmanager
    def suppressed(self) -> Generator[None]:
        """Silence every message inside the context, without reopening the log file

        Used for engine work that is not part of a calculation (e.g. a GUI
        checking or drawing elements), so it stays out of the memorial.
        """
        previous_level = self._level
        self._level = LogLevel.DISABLED
        try:
            yield
        finally:
            self._level = previous_level

    def __del__(self) -> None:
        if self._log_file is not None:
            self._log_file.close()

    def _log(self, level: LogLevel, message: str, label: str | None) -> None:
        if level >= LogLevel.DISABLED or self._level > level:
            return

        style = _LEVEL_STYLES[level]
        indent = "  " * (LogLevel.GENERAL - level)

        if label:
            tag_name = label
        else:
            frame = inspect.currentframe()
            # _log <- log_property/log_element/etc. <- caller
            caller = frame.f_back.f_back if frame and frame.f_back else None
            if caller:
                caller_self = caller.f_locals.get("self")
                if caller_self is not None and hasattr(caller_self, "_log_label"):
                    tag_name = caller_self._log_label
                else:
                    qualname = caller.f_code.co_qualname
                    if "." in qualname:
                        class_name = qualname.rsplit(".", 1)[0]
                        caller_cls = caller.f_globals.get(class_name)
                        lbl = (
                            getattr(caller_cls, "_log_label", None)
                            if caller_cls is not None
                            else None
                        )
                        tag_name = lbl if isinstance(lbl, str) else qualname
                    else:
                        tag_name = qualname
            else:
                tag_name = level.name

        line = f"{indent}[{style}]{escape(f'[{level.name} | {tag_name}]')}[/{style}] {escape(message)}"

        if self._output in (LogOutput.CONSOLE, LogOutput.BOTH):
            self._console.print(line)
        if self._output in (LogOutput.FILE, LogOutput.BOTH) and self._file_console:
            self._file_console.print(line)

    def log_property(self, message: str, label: str | None = None) -> None:
        self._log(LogLevel.PROPERTY, message, label)

    def log_operation(self, message: str, label: str | None = None) -> None:
        self._log(LogLevel.OPERATION, message, label)

    def log_iteration(self, message: str, label: str | None = None) -> None:
        self._log(LogLevel.ITERATION, message, label)

    def log_element(self, message: str, label: str | None = None) -> None:
        self._log(LogLevel.ELEMENT, message, label)

    def log_interaction(self, message: str, label: str | None = None) -> None:
        self._log(LogLevel.INTERACTION, message, label)

    def log_general(self, message: str, label: str | None = None) -> None:
        self._log(LogLevel.GENERAL, message, label)


_ClassT = TypeVar("_ClassT", bound=type)


def logger_label(label: str) -> Callable[[_ClassT], _ClassT]:
    """Class decorator that sets a default log label, resolved against each instance.

    Static:  @logger_label("Section Properties")
    Dynamic: @logger_label("Concrete {name}") — {attr} placeholders resolved via getattr.
    """

    def decorator(cls: _ClassT) -> _ClassT:
        if "{" in label:

            def _resolve(instance: object, _l: str = label) -> str:
                class _Proxy(dict[str, str]):
                    def __missing__(self, key: str) -> str:
                        return str(getattr(instance, key, f"{{{key}}}"))

                return _l.format_map(_Proxy())

            cls._log_label = property(_resolve)
        else:
            cls._log_label = (
                label  # plain string — accessible from static methods via class lookup
            )
        return cls

    return decorator


# Console-only until src.config applies APP_CONFIG's level and output; the
# logger must not import src.config, which depends on it (circular import).
_logger = BeamLogger(LogLevel.PROPERTY, LogOutput.CONSOLE)

log_property = _logger.log_property
log_operation = _logger.log_operation
log_iteration = _logger.log_iteration
log_element = _logger.log_element
log_interaction = _logger.log_interaction
log_general = _logger.log_general
configure_logger = _logger.configure
set_log_level = _logger.set_level
suppress_logging = _logger.suppressed
# loggerlabel is a plain function — already importable at module level
