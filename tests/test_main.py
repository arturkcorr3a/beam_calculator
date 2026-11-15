"""Unit tests for the command-line runner (src.main)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import src.main as runner
from src.config import APP_CONFIG
from src.drawing.api import DrawingError
from src.examples.simple_example import SimpleExample
from src.logger import LogLevel, LogOutput


class _Recorder:
    """Callable that records the positional arguments of every call"""

    def __init__(self, result: object = None) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.keywords: list[dict[str, object]] = []
        self._result = result

    def __call__(self, *args: object, **kwargs: object) -> object:
        self.calls.append(args)
        self.keywords.append(kwargs)
        return self._result


def _module_with(name: str, **members: object) -> ModuleType:
    """Build a throwaway module holding the given members"""
    module = ModuleType(name)
    for key, value in members.items():
        setattr(module, key, value)
    return module


def _example_class(module_name: str, log: list[str]) -> type[SimpleExample]:
    """Create a SimpleExample subclass that pretends to live in module_name"""

    class _Example(SimpleExample):
        def run(self) -> None:
            log.append("ran")

    _Example.__module__ = module_name
    return _Example


@pytest.fixture
def pavements_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the runner's pavement folder at a temp dir holding one YAML file"""
    (tmp_path / "demo.yaml").write_text("", encoding="utf-8")
    monkeypatch.setattr(runner, "PAVEMENTS_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def logger_calls(monkeypatch: pytest.MonkeyPatch) -> _Recorder:
    """Replace configure_logger and keep APP_CONFIG's log fields isolated"""
    recorder = _Recorder()
    monkeypatch.setattr(runner, "configure_logger", recorder)
    monkeypatch.setattr(APP_CONFIG, "log_level", APP_CONFIG.log_level)
    monkeypatch.setattr(APP_CONFIG, "log_output", APP_CONFIG.log_output)
    return recorder


class TestBuildParser:
    """Tests for the runner's argument parsing."""

    def test_example_and_load_are_exclusive(self) -> None:
        with pytest.raises(SystemExit):
            runner.build_parser().parse_args(["--example", "a", "--load", "b"])

    def test_example_or_load_is_required(self) -> None:
        with pytest.raises(SystemExit):
            runner.build_parser().parse_args(["--log-level", "general"])

    def test_log_flags_are_case_insensitive(self) -> None:
        args = runner.build_parser().parse_args(
            ["--load", "x", "--log-level", "general", "--log-output", "CONSOLE"]
        )
        assert args.log_level == "GENERAL", "Log level should be upper-cased"
        assert args.log_output == "console", "Log output should be lower-cased"

    def test_log_flags_default_to_none(self) -> None:
        args = runner.build_parser().parse_args(["--example", "x"])
        assert args.log_level is None, "Omitted log level should stay None"
        assert args.log_output is None, "Omitted log output should stay None"

    def test_invalid_log_level_is_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner.build_parser().parse_args(["--load", "x", "--log-level", "loud"])


class TestResolvePavement:
    """Tests for mapping --load values to files in resources/examples/."""

    def test_adds_yaml_extension(self, pavements_dir: Path) -> None:
        assert runner.resolve_pavement("demo") == pavements_dir / "demo.yaml", (
            "A bare name should get the .yaml extension"
        )

    def test_keeps_yaml_extension(self, pavements_dir: Path) -> None:
        assert runner.resolve_pavement("demo.yaml") == pavements_dir / "demo.yaml", (
            "A name with .yaml should be used as-is"
        )


class TestAvailableExamples:
    """Tests for listing the example modules."""

    def test_excludes_interface_module(self) -> None:
        examples = runner.available_examples()
        assert "simple_example" not in examples, "The interface is not an example"
        assert "t_concreto2" in examples, "Real examples should be listed"


class TestFindExample:
    """Tests for discovering the SimpleExample subclass of a module."""

    def test_returns_instance_of_defined_subclass(self) -> None:
        log: list[str] = []
        cls = _example_class("fake_example", log)
        example = runner.find_example(_module_with("fake_example", Demo=cls))
        assert isinstance(example, cls), "Should instantiate the module's subclass"

    def test_ignores_imported_subclass(self) -> None:
        imported = _example_class("elsewhere", [])
        own = _example_class("fake_example", [])
        module = _module_with("fake_example", Imported=imported, Own=own)
        assert isinstance(runner.find_example(module), own), (
            "Subclasses defined in other modules should be ignored"
        )

    def test_rejects_module_without_subclass(self) -> None:
        module = _module_with("fake_example", SimpleExample=SimpleExample)
        with pytest.raises(ValueError, match="exactly one"):
            runner.find_example(module)

    def test_rejects_module_with_two_subclasses(self) -> None:
        module = _module_with(
            "fake_example",
            First=_example_class("fake_example", []),
            Second=_example_class("fake_example", []),
        )
        with pytest.raises(ValueError, match="exactly one"):
            runner.find_example(module)


class TestMain:
    """Tests for the runner's end-to-end dispatch."""

    def test_load_resolves_pavement_with_log_flags(
        self,
        pavements_dir: Path,
        logger_calls: _Recorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        resolved: list[bool] = []
        pavement = SimpleNamespace(resolve=lambda: resolved.append(True))
        loader = _Recorder(pavement)
        monkeypatch.setattr(runner, "load_pavement", loader)

        runner.main(
            ["--load", "demo", "--log-level", "general", "--log-output", "console"]
        )

        assert loader.calls == [(pavements_dir / "demo.yaml",)], "Should load demo.yaml"
        assert resolved == [True], "The loaded pavement should be resolved"
        assert APP_CONFIG.log_level == LogLevel.GENERAL, "Level should be applied"
        assert APP_CONFIG.log_output == LogOutput.CONSOLE, "Output should be applied"
        assert logger_calls.calls == [(LogLevel.GENERAL, LogOutput.CONSOLE)], (
            "The logger should be reconfigured with the flags"
        )

    def test_load_without_flags_keeps_log_defaults(
        self,
        pavements_dir: Path,
        logger_calls: _Recorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            runner, "load_pavement", _Recorder(SimpleNamespace(resolve=lambda: None))
        )
        level, output = APP_CONFIG.log_level, APP_CONFIG.log_output

        runner.main(["--load", "demo.yaml"])

        assert logger_calls.calls == [(level, output)], (
            "Omitted flags should keep the APP_CONFIG log settings"
        )

    def test_missing_pavement_file_exits(
        self, pavements_dir: Path, logger_calls: _Recorder
    ) -> None:
        with pytest.raises(SystemExit):
            runner.main(["--load", "nope"])
        assert logger_calls.calls == [], "Nothing should run on a bad path"

    def test_example_runs_discovered_class(
        self, logger_calls: _Recorder, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        log: list[str] = []
        module_name = "src.examples.t_concreto2"
        module = _module_with(module_name, Demo=_example_class(module_name, log))
        importer = _Recorder(module)
        monkeypatch.setattr(runner, "import_module", importer)

        runner.main(["--example", "t_concreto2.py", "--log-level", "disabled"])

        assert importer.calls == [(module_name,)], "Should import the named example"
        assert log == ["ran"], "The example's run() should be called"
        assert APP_CONFIG.log_level == LogLevel.DISABLED, "Level should be applied"

    def test_missing_example_exits(self, logger_calls: _Recorder) -> None:
        with pytest.raises(SystemExit):
            runner.main(["--example", "nope"])
        assert logger_calls.calls == [], "Nothing should run on a bad name"


@pytest.fixture
def drawing_calls(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[_Recorder, _Recorder]:
    """Replace the drawing entry points and send the results folder to a temp dir"""
    saver = _Recorder([])
    shower = _Recorder()
    monkeypatch.setattr(runner, "save_pavement", saver)
    monkeypatch.setattr(runner, "show_pavement", shower)
    monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path / "results")

    def keep_backend(name: str) -> None:
        """Leave the test backend alone"""

    monkeypatch.setattr(runner.plt, "switch_backend", keep_backend)
    return saver, shower


class TestDisplay:
    """Tests for --display: drawing the resolved pavement."""

    def test_display_is_case_insensitive(self) -> None:
        args = runner.build_parser().parse_args(["--load", "x", "--display", "save"])
        assert args.display == "SAVE", "Display mode should be upper-cased"

    def test_display_defaults_to_none(self) -> None:
        args = runner.build_parser().parse_args(["--load", "x"])
        assert args.display is None, "No drawing unless asked"

    def test_invalid_display_is_rejected(self) -> None:
        with pytest.raises(SystemExit):
            runner.build_parser().parse_args(["--load", "x", "--display", "print"])

    def test_drawing_folder(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(runner, "RESULTS_DIR", tmp_path)
        folder = runner.drawing_folder("t_concreto2", date(2026, 11, 7))
        assert folder == tmp_path / "nov-07" / "drawing" / "t_concreto2", (
            "results/<mmm-dd>/drawing/<name>/"
        )

    @pytest.mark.parametrize(
        ("mode", "saves", "shows"),
        [("SAVE", 1, 0), ("SHOW", 0, 1), ("BOTH", 1, 1)],
    )
    def test_load_and_display(
        self,
        mode: str,
        saves: int,
        shows: int,
        pavements_dir: Path,
        logger_calls: _Recorder,
        drawing_calls: tuple[_Recorder, _Recorder],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        pavement = SimpleNamespace(resolve=lambda: None)
        monkeypatch.setattr(runner, "load_pavement", _Recorder(pavement))
        saver, shower = drawing_calls

        runner.main(["--load", "demo", "--display", mode])

        assert len(saver.calls) == saves, f"{mode}: saves {saves} time(s)"
        assert len(shower.calls) == shows, f"{mode}: shows {shows} time(s)"
        if saves:
            drawn, folder = saver.calls[0]
            assert drawn is pavement, "The resolved pavement is drawn"
            assert isinstance(folder, Path) and folder.name == "demo", (
                "Saved under the file's name"
            )
            assert saver.keywords[0] == {"pavement_name": "demo"}, (
                "The title block names the pavement after the file"
            )

    def test_no_display_draws_nothing(
        self,
        pavements_dir: Path,
        logger_calls: _Recorder,
        drawing_calls: tuple[_Recorder, _Recorder],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            runner, "load_pavement", _Recorder(SimpleNamespace(resolve=lambda: None))
        )
        runner.main(["--load", "demo"])
        assert drawing_calls[0].calls == drawing_calls[1].calls == [], "No drawing"

    def test_example_without_pavement_exits(
        self,
        logger_calls: _Recorder,
        drawing_calls: tuple[_Recorder, _Recorder],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        module_name = "src.examples.t_concreto2"
        module = _module_with(module_name, Demo=_example_class(module_name, []))
        monkeypatch.setattr(runner, "import_module", _Recorder(module))
        with pytest.raises(SystemExit):
            runner.main(["--example", "t_concreto2", "--display", "SHOW"])
        assert drawing_calls[1].calls == [], "Nothing to show"

    def test_example_pavement_is_drawn(
        self,
        logger_calls: _Recorder,
        drawing_calls: tuple[_Recorder, _Recorder],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        module_name = "src.examples.t_concreto2"
        pavement = SimpleNamespace()

        class _Example(SimpleExample):
            def run(self) -> Any:
                return pavement

        _Example.__module__ = module_name
        module = _module_with(module_name, Demo=_Example)
        monkeypatch.setattr(runner, "import_module", _Recorder(module))

        runner.main(["--example", "t_concreto2", "--display", "SHOW"])

        assert drawing_calls[1].calls == [(pavement,)], (
            "The example's pavement is shown"
        )

    def test_drawing_error_exits(
        self,
        pavements_dir: Path,
        logger_calls: _Recorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fail(*args: object, **kwargs: object) -> None:
            raise DrawingError("V1: no marks")

        monkeypatch.setattr(
            runner, "load_pavement", _Recorder(SimpleNamespace(resolve=lambda: None))
        )
        monkeypatch.setattr(runner, "show_pavement", fail)
        with pytest.raises(SystemExit) as raised:
            runner.main(["--load", "demo", "--display", "SHOW"])
        assert raised.value.code == 1, "A drawing error exits with status 1"
