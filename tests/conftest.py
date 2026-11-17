"""Session-wide test setup: keep the engine's logger from slowing down the suite.

The module logger starts at the most verbose level, writing to the console and to a
file; formatting those lines with rich dominated the suite's run time (about 80%).
"""

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# Before src.config is imported (it opens the log file), so the suite's log files
# never land in the project's logs/ folder.
import src.logger as logger_module

logger_module._LOGS_DIR = Path(tempfile.mkdtemp(prefix="beam_calculator_test_logs_"))  # pyright: ignore[reportPrivateUsage]

from src.logger import LogLevel, set_log_level  # noqa: E402


@pytest.fixture(autouse=True, scope="session")
def _quiet_logger() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    """Silence the module logger for the whole run"""
    set_log_level(LogLevel.DISABLED)
    yield


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--fast",
        action="store_true",
        help="skip tests/drawing, the slowest and most memory-hungry directory",
    )


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool | None:
    """With --fast, do not even import the drawing tests"""
    if config.getoption("--fast") and collection_path.name == "drawing":
        return True
    return None


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """--fast also means no coverage, even though pytest.ini turns it on

    pytest-cov decides before this conftest is loaded (it reads the command line and
    addopts) and has already started measuring, so stop it and take it out.
    """
    if not config.getoption("--fast"):
        return
    plugin = config.pluginmanager.get_plugin("_cov")
    if plugin is None:
        return
    if plugin.cov_controller is not None:
        plugin.cov_controller.cov.stop()
    config.pluginmanager.unregister(plugin)
