"""YamlProjectStore: project files through the engine's own persistence."""

from pathlib import Path

import yaml

from pavement_ui.core.engine import config_mapper
from pavement_ui.core.engine.pavement_builder import build_pavement
from pavement_ui.core.engine.records_from_pavement import records_from
from pavement_ui.core.engine.rule_errors import rule_message
from pavement_ui.core.errors import PersistenceError, PersistenceErrorKind
from pavement_ui.core.model.pavement_records import PavementRecords
from pavement_ui.core.model.settings import ConfigValues
from pavement_ui.core.ports import LoadedProject
from src.logger import suppress_logging
from src.persistency import load_pavement, save_pavement


def _yaml_detail(error: yaml.YAMLError) -> str:
    """The 1-based line of a YAML error, when the parser reports one."""
    mark = getattr(error, "problem_mark", None)
    line = getattr(mark, "line", None)
    return str(line + 1) if isinstance(line, int) else "?"


class YamlProjectStore:
    """Save and open ``.yaml`` project files in the engine's format

    The engine's loader writes the file's settings into APP_CONFIG; opening
    always restores the previous settings and returns the file's ones instead,
    since the session owns the settings.
    """

    def save(self, path: Path, records: PavementRecords, config: ConfigValues) -> None:
        """Write records and settings to path

        Raises:
            PersistenceError: If the file cannot be written.
        """
        try:
            with suppress_logging():
                save_pavement(build_pavement(records, config), path)
        except OSError as error:
            raise PersistenceError(
                PersistenceErrorKind.WRITE_FAILED, str(error)
            ) from error

    def open(self, path: Path) -> LoadedProject:
        """Read records and settings from path

        Raises:
            PersistenceError: If the file is missing, is not YAML, or its content
                is not a valid pavement.
        """
        saved = config_mapper.snapshot()
        try:
            with suppress_logging():
                pavement = load_pavement(path)
                return LoadedProject(records_from(pavement), config_mapper.read())
        except FileNotFoundError as error:
            raise PersistenceError(PersistenceErrorKind.NOT_FOUND, str(path)) from error
        except yaml.YAMLError as error:
            raise PersistenceError(
                PersistenceErrorKind.INVALID_YAML, _yaml_detail(error)
            ) from error
        except (ValueError, KeyError) as error:
            raise PersistenceError(
                PersistenceErrorKind.INVALID_CONTENT, rule_message(error)
            ) from error
        except TypeError as error:  # e.g. an empty file
            raise PersistenceError(
                PersistenceErrorKind.INVALID_CONTENT, str(error)
            ) from error
        finally:
            config_mapper.restore(saved)
