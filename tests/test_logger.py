"""Unit tests for the logger module (BeamLogger, LogLevel, LogOutput, logger_label)."""

from __future__ import annotations

import io
import itertools
from pathlib import Path

import pytest
from rich.console import Console

import src.logger as logger_module
from src.logger import (
    BeamLogger,
    LogLevel,
    LogOutput,
    logger_label,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def console_logger() -> BeamLogger:
    """BeamLogger writing to console only, threshold at PROPERTY (most verbose)."""
    return BeamLogger(LogLevel.PROPERTY, LogOutput.CONSOLE)


@pytest.fixture
def captured_logger() -> tuple[BeamLogger, io.StringIO]:
    """BeamLogger with a StringIO-backed console for deterministic output capture.

    Returns a (logger, buffer) pair so tests can read emitted lines from buffer.
    """
    buf = io.StringIO()
    lg = BeamLogger(LogLevel.PROPERTY, LogOutput.CONSOLE)
    lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
    return lg, buf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _emitted(buf: io.StringIO) -> str:
    """Return everything written to a StringIO capture buffer.

    Args:
        buf: Buffer whose position is reset to the start before reading.

    Returns:
        Full string content of the buffer, stripped of the trailing newline.
    """
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# 1. LogLevel
# ---------------------------------------------------------------------------


class TestLogLevelEnum:
    """Tests for LogLevel numeric ordering and name attributes."""

    @pytest.mark.parametrize(
        ("level", "expected_value"),
        [
            (LogLevel.PROPERTY, 1),
            (LogLevel.OPERATION, 2),
            (LogLevel.ITERATION, 3),
            (LogLevel.ELEMENT, 4),
            (LogLevel.INTERACTION, 5),
            (LogLevel.GENERAL, 6),
            (LogLevel.DISABLED, 7),
        ],
    )
    def test_numeric_values(self, level: LogLevel, expected_value: int) -> None:
        assert level == expected_value, (
            f"LogLevel.{level.name} should have numeric value {expected_value}"
        )

    def test_ordering_ascending(self) -> None:
        levels = [
            LogLevel.PROPERTY,
            LogLevel.OPERATION,
            LogLevel.ITERATION,
            LogLevel.ELEMENT,
            LogLevel.INTERACTION,
            LogLevel.GENERAL,
            LogLevel.DISABLED,
        ]
        for a, b in itertools.pairwise(levels):
            assert a < b, f"LogLevel.{a.name} should be less than LogLevel.{b.name}"

    @pytest.mark.parametrize(
        ("level", "expected_name"),
        [
            (LogLevel.PROPERTY, "PROPERTY"),
            (LogLevel.OPERATION, "OPERATION"),
            (LogLevel.ITERATION, "ITERATION"),
            (LogLevel.ELEMENT, "ELEMENT"),
            (LogLevel.INTERACTION, "INTERACTION"),
            (LogLevel.GENERAL, "GENERAL"),
            (LogLevel.DISABLED, "DISABLED"),
        ],
    )
    def test_names(self, level: LogLevel, expected_name: str) -> None:
        assert level.name == expected_name, (
            f"LogLevel member at value {level.value} should have name {expected_name!r}"
        )


# ---------------------------------------------------------------------------
# 2. LogOutput
# ---------------------------------------------------------------------------


class TestLogOutputEnum:
    """Tests for LogOutput string values and round-trip construction."""

    def test_console_value(self) -> None:
        assert LogOutput.CONSOLE == "console", (
            "LogOutput.CONSOLE should equal the string 'console'"
        )

    def test_file_value(self) -> None:
        assert LogOutput.FILE == "file", "LogOutput.FILE should equal the string 'file'"

    def test_both_value(self) -> None:
        assert LogOutput.BOTH == "both", "LogOutput.BOTH should equal the string 'both'"

    def test_roundtrip_console(self) -> None:
        assert LogOutput("console") is LogOutput.CONSOLE, (
            "LogOutput('console') should return the CONSOLE member"
        )

    def test_roundtrip_file(self) -> None:
        assert LogOutput("file") is LogOutput.FILE, (
            "LogOutput('file') should return the FILE member"
        )

    def test_roundtrip_both(self) -> None:
        assert LogOutput("both") is LogOutput.BOTH, (
            "LogOutput('both') should return the BOTH member"
        )


# ---------------------------------------------------------------------------
# 3. BeamLogger file lifecycle
# ---------------------------------------------------------------------------


class TestBeamLoggerFileLifecycle:
    """Tests for log-file creation and cleanup in BeamLogger."""

    def test_console_mode_opens_no_file(self) -> None:
        lg = BeamLogger(LogLevel.GENERAL, LogOutput.CONSOLE)
        assert lg._log_file is None, (  # pyright: ignore[reportPrivateUsage]
            "CONSOLE mode should not open a log file (_log_file must be None)"
        )
        assert lg._file_console is None, "CONSOLE mode should not create a file console"  # pyright: ignore[reportPrivateUsage]

    def test_file_mode_creates_log_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        lg = BeamLogger(LogLevel.GENERAL, LogOutput.FILE)
        assert lg._log_file is not None, "FILE mode should open a log file"  # pyright: ignore[reportPrivateUsage]
        assert lg._file_console is not None, "FILE mode should create a file console"  # pyright: ignore[reportPrivateUsage]
        log_files = list(tmp_path.glob("beam_calculator_*.log"))
        assert len(log_files) == 1, (
            "FILE mode should create exactly one timestamped log file"
        )
        lg._log_file.close()  # pyright: ignore[reportPrivateUsage]

    def test_both_mode_creates_log_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        lg = BeamLogger(LogLevel.GENERAL, LogOutput.BOTH)
        assert lg._log_file is not None, "BOTH mode should open a log file"  # pyright: ignore[reportPrivateUsage]
        log_files = list(tmp_path.glob("beam_calculator_*.log"))
        assert len(log_files) == 1, (
            "BOTH mode should create exactly one timestamped log file"
        )
        lg._log_file.close()  # pyright: ignore[reportPrivateUsage]

    def test_configure_switches_from_file_to_console(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        lg = BeamLogger(LogLevel.GENERAL, LogOutput.FILE)
        old_file = lg._log_file  # pyright: ignore[reportPrivateUsage]
        assert old_file is not None
        lg.configure(LogLevel.GENERAL, LogOutput.CONSOLE)
        assert old_file.closed, (
            "configure to CONSOLE should close the previously-open log file"
        )
        assert lg._log_file is None, (  # pyright: ignore[reportPrivateUsage]
            "After reconfiguring to CONSOLE, _log_file should be None"
        )
        assert lg._file_console is None, (  # pyright: ignore[reportPrivateUsage]
            "After reconfiguring to CONSOLE, _file_console should be None"
        )

    def test_configure_switches_from_console_to_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        lg = BeamLogger(LogLevel.GENERAL, LogOutput.CONSOLE)
        assert lg._log_file is None  # pyright: ignore[reportPrivateUsage]
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        lg.configure(LogLevel.GENERAL, LogOutput.FILE)
        assert lg._log_file is not None, "configure to FILE should open a new log file"  # pyright: ignore[reportPrivateUsage]
        log_files = list(tmp_path.glob("beam_calculator_*.log"))
        assert len(log_files) == 1, (
            "configure to FILE should create exactly one new log file"
        )
        lg._log_file.close()  # pyright: ignore[reportPrivateUsage]

    def test_configure_replaces_file_with_new_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        lg = BeamLogger(LogLevel.GENERAL, LogOutput.FILE)
        first_file = lg._log_file  # pyright: ignore[reportPrivateUsage]
        assert first_file is not None
        lg.configure(LogLevel.PROPERTY, LogOutput.FILE)
        assert first_file.closed, (
            "configure should close the old log file before opening a new one"
        )
        assert lg._log_file is not None, (  # pyright: ignore[reportPrivateUsage]
            "configure to FILE should open a replacement log file"
        )
        assert lg._log_file is not first_file, (  # pyright: ignore[reportPrivateUsage]
            "configure should create a different file handle, not reuse the old one"
        )
        lg._log_file.close()  # pyright: ignore[reportPrivateUsage]

    def test_del_closes_open_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        lg = BeamLogger(LogLevel.GENERAL, LogOutput.FILE)
        f = lg._log_file  # pyright: ignore[reportPrivateUsage]
        assert f is not None
        lg.__del__()
        assert f.closed, "__del__ should close the open log file"

    def test_del_on_console_logger_is_safe(self, console_logger: BeamLogger) -> None:
        # Must not raise even though _log_file is None
        console_logger.__del__()


# ---------------------------------------------------------------------------
# 4. Level gating
# ---------------------------------------------------------------------------


class TestLogLevelGating:
    """Tests that messages below the configured threshold are suppressed."""

    def test_below_threshold_emits_nothing(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.ELEMENT, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_property("should be suppressed", label="T")
        lg.log_operation("should be suppressed", label="T")
        lg.log_iteration("should be suppressed", label="T")
        assert _emitted(buf).strip() == "", (
            "Messages below ELEMENT threshold should produce no output"
        )

    def test_at_threshold_emits(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.ELEMENT, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_element("visible", label="T")
        assert "visible" in _emitted(buf), (
            "A message at the configured threshold should appear in output"
        )

    def test_above_threshold_emits(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.ELEMENT, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_general("also visible", label="T")
        assert "also visible" in _emitted(buf), (
            "A message above the configured threshold should appear in output"
        )

    def test_disabled_suppresses_all(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.DISABLED, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        for method in (
            lg.log_property,
            lg.log_operation,
            lg.log_iteration,
            lg.log_element,
            lg.log_interaction,
            lg.log_general,
        ):
            method("msg", label="T")
        assert _emitted(buf).strip() == "", (
            "DISABLED level should suppress all log messages"
        )

    def test_disabled_message_level_emits_nothing(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.DISABLED, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg._log(LogLevel.DISABLED, "msg", "T")  # pyright: ignore[reportPrivateUsage]
        assert _emitted(buf).strip() == "", (
            "A message at DISABLED level should be dropped, not raise or emit"
        )


# ---------------------------------------------------------------------------
# 5. Indent and format
# ---------------------------------------------------------------------------


class TestLogIndentAndFormat:
    """Tests for the output line format and per-level indentation."""

    def test_general_has_no_indent(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.GENERAL, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_general("hello", label="Tag")
        line = _emitted(buf)
        assert line.startswith("[GENERAL | Tag]"), (
            "GENERAL (indent=0) output should start with the tag bracket, no leading spaces"
        )

    def test_property_has_maximum_indent(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.PROPERTY, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_property("hello", label="Tag")
        line = _emitted(buf)
        # GENERAL(6) - PROPERTY(1) = 5, indent = "  " * 5 = 10 spaces
        assert line.startswith(" " * 10), (
            "PROPERTY (indent=5 * 2 spaces = 10) should have 10 leading spaces"
        )

    def test_operation_has_eight_spaces(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.PROPERTY, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_operation("hello", label="Tag")
        line = _emitted(buf)
        # GENERAL(6) - OPERATION(2) = 4, indent = "  " * 4 = 8 spaces
        assert line.startswith(" " * 8)
        assert not line.startswith(" " * 9), (
            "OPERATION (indent=4 * 2 = 8) should have exactly 8 leading spaces"
        )

    def test_level_name_in_output(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.PROPERTY, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_element("msg", label="Tag")
        line = _emitted(buf)
        assert "ELEMENT" in line, (
            "The level name 'ELEMENT' should appear in the output line"
        )

    def test_tag_in_output(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.PROPERTY, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_element("msg", label="MyTag")
        line = _emitted(buf)
        assert "MyTag" in line, "The explicit label should appear in the output line"

    def test_message_in_output(self) -> None:
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.PROPERTY, LogOutput.CONSOLE)
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_element("payload text", label="T")
        line = _emitted(buf)
        assert "payload text" in line, (
            "The message content should appear in the output line"
        )

    def test_output_written_to_file_console(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        lg = BeamLogger(LogLevel.PROPERTY, LogOutput.FILE)
        assert lg._file_console is not None  # pyright: ignore[reportPrivateUsage]
        assert lg._log_file is not None  # pyright: ignore[reportPrivateUsage]
        lg.log_general("file content", label="T")
        lg._log_file.flush()  # pyright: ignore[reportPrivateUsage]
        content = Path(lg._log_file.name).read_text(encoding="utf-8")  # pyright: ignore[reportPrivateUsage]
        assert "file content" in content, (
            "FILE mode should write the message to the log file"
        )
        lg._log_file.close()  # pyright: ignore[reportPrivateUsage]

    def test_both_mode_writes_to_console_and_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        buf = io.StringIO()
        lg = BeamLogger(LogLevel.PROPERTY, LogOutput.BOTH)
        assert lg._log_file is not None  # pyright: ignore[reportPrivateUsage]
        lg._console = Console(file=buf, no_color=True, highlight=False)  # pyright: ignore[reportPrivateUsage]
        lg.log_general("both output", label="T")
        lg._log_file.flush()  # pyright: ignore[reportPrivateUsage]
        console_out = _emitted(buf)
        file_content = Path(lg._log_file.name).read_text(encoding="utf-8")  # pyright: ignore[reportPrivateUsage]
        assert "both output" in console_out, (
            "BOTH mode should write the message to the console"
        )
        assert "both output" in file_content, (
            "BOTH mode should also write the message to the log file"
        )
        lg._log_file.close()  # pyright: ignore[reportPrivateUsage]


# ---------------------------------------------------------------------------
# 6. Explicit label bypasses frame introspection
# ---------------------------------------------------------------------------


class TestExplicitLabel:
    """Tests that an explicitly-provided label short-circuits inspect logic."""

    def test_explicit_label_used(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger
        lg.log_property("msg", label="ExplicitTag")
        assert "ExplicitTag" in _emitted(buf), (
            "An explicit label argument should appear in the output tag"
        )

    def test_explicit_label_overrides_class_label(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        """Test that explicit label on an instance method overrides the class _log_label."""
        lg, buf = captured_logger

        @logger_label("ClassLabel")
        class _Caller:
            def emit(self) -> None:
                lg.log_general("msg", label="OverrideLabel")

        _Caller().emit()
        out = _emitted(buf)
        assert "OverrideLabel" in out, (
            "Explicit label should appear in output even when the class has _log_label"
        )
        assert "ClassLabel" not in out, (
            "Class _log_label should NOT appear when an explicit label is given"
        )


# ---------------------------------------------------------------------------
# Module-level caller for the no-dot-qualname branch (line 103 of logger.py)
# ---------------------------------------------------------------------------
# This function must be defined at the top level of the test module so that
# its co_qualname has no "." — only then does _log take the ``tag_name = qualname``
# branch (lines 102-103).  A nested or local function always has dots in its
# qualname (e.g. "TestXxx.test_foo.<locals>.fn").

_TOP_LEVEL_LOGGER_CAPTURE: list[tuple[BeamLogger, io.StringIO]] = []


def _top_level_caller_fn() -> None:
    """Call log_general from a true module-level function to exercise the no-dot branch."""
    if _TOP_LEVEL_LOGGER_CAPTURE:
        lg, _ = _TOP_LEVEL_LOGGER_CAPTURE[0]
        lg.log_general("top-level msg")


# ---------------------------------------------------------------------------
# 7. Caller tag resolution via inspect frames
# ---------------------------------------------------------------------------


class TestCallerTagResolution:
    """Tests for the three-branch caller-tag introspection in BeamLogger._log."""

    # (A) instance path — static label

    def test_instance_static_label(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger

        @logger_label("StaticFoo")
        class _Caller:
            def emit(self) -> None:
                lg.log_property("msg")

        _Caller().emit()
        assert "StaticFoo" in _emitted(buf), (
            "Instance caller with static @logger_label should use the class label as tag"
        )

    # (A) instance path — dynamic label (attr present)

    def test_instance_dynamic_label_resolved(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger

        @logger_label("Widget {widget_id}")
        class _Caller:
            widget_id: int = 42

            def emit(self) -> None:
                lg.log_property("msg")

        _Caller().emit()
        assert "Widget 42" in _emitted(buf), (
            "Dynamic @logger_label should resolve {attr} against the calling instance"
        )

    # (A) instance path — dynamic label (attr missing → literal {key})

    def test_instance_dynamic_label_missing_attr(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger

        @logger_label("Item {nonexistent_attr}")
        class _Caller:
            def emit(self) -> None:
                lg.log_property("msg")

        _Caller().emit()
        assert "{nonexistent_attr}" in _emitted(buf), (
            "Dynamic @logger_label with a missing attribute should fall back to literal {key}"
        )

    # (B) static method path — local class: f_globals lookup fails, falls through to qualname

    def test_staticmethod_local_class_uses_qualname(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        """Test that a static method on a local (non-top-level) class falls back to qualname.

        The frame-inspection branch resolves the class via ``f_globals.get(class_name)``,
        which only works for top-level classes. A class defined inside a test method is
        local and will not be found, so the tag falls back to the function qualname.
        """
        lg, buf = captured_logger

        @logger_label("StaticService")
        class _LocalCaller:
            @staticmethod
            def emit() -> None:
                lg.log_general("msg")

        _LocalCaller.emit()
        out = _emitted(buf)
        # Local class → f_globals lookup misses → qualname used as tag
        assert "_LocalCaller" in out or "emit" in out, (
            "Static method on a local class should fall back to the qualname as tag"
        )
        assert "StaticService" not in out, (
            "Local class label is NOT resolved (class not in f_globals)"
        )

    # (B) static method path — dynamic label falls through to qualname

    def test_staticmethod_dynamic_label_falls_through_to_qualname(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger

        @logger_label("Dynamic {attr}")
        class _CallerDynamic:
            @staticmethod
            def emit() -> None:
                lg.log_general("msg")

        _CallerDynamic.emit()
        out = _emitted(buf)
        # property is not str, so falls through to qualname (contains class name and method)
        assert "emit" in out or "_CallerDynamic" in out, (
            "Static method with dynamic @logger_label should fall back to qualname (not the property)"
        )

    # (C) local function nested inside a test — qualname includes the function name

    def test_local_function_uses_qualname(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        """Test that a function with no 'self' local uses its qualname as the tag.

        The function is local to the test method, so its qualname contains
        "<locals>._local_fn".  Rich may wrap the long tag string across multiple
        lines; assert on the short suffix that is guaranteed to survive wrapping.
        """
        lg, buf = captured_logger

        def _local_fn() -> None:
            lg.log_general("msg")

        _local_fn()
        out = _emitted(buf)
        # Qualname ends with _local_fn; check without the wrapping concern
        assert "_local_fn" in out.replace("\n", ""), (
            "A function with no 'self' caller should include the function name in the tag"
        )

    # (C) true module-level function — no dots in qualname → line 103 branch

    def test_top_level_function_uses_bare_qualname(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        """Test the no-dot-qualname branch (logger.py line 103) via a true module-level caller.

        ``_top_level_caller_fn`` is defined at module scope; its ``co_qualname``
        is ``_top_level_caller_fn`` with no dots.  The ``_log`` frame inspector
        then takes the ``tag_name = qualname`` branch instead of the class-lookup path.
        """
        lg, buf = captured_logger
        _TOP_LEVEL_LOGGER_CAPTURE.clear()
        _TOP_LEVEL_LOGGER_CAPTURE.append((lg, buf))
        try:
            _top_level_caller_fn()
        finally:
            _TOP_LEVEL_LOGGER_CAPTURE.clear()
        out = _emitted(buf)
        assert "_top_level_caller_fn" in out.replace("\n", ""), (
            "A true module-level function should use its bare qualname as the log tag"
        )

    # instance path — class without _log_label falls back to qualname

    def test_instance_without_label_uses_qualname(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger

        class _Unlabelled:
            def emit(self) -> None:
                lg.log_general("msg")

        _Unlabelled().emit()
        out = _emitted(buf)
        assert "emit" in out or "_Unlabelled" in out, (
            "An instance caller without @logger_label should fall back to its qualname"
        )


# ---------------------------------------------------------------------------
# 8. logger_label decorator
# ---------------------------------------------------------------------------


class TestLoggerLabelDecorator:
    """Tests for the logger_label class decorator in both static and dynamic forms."""

    def test_static_form_sets_string(self) -> None:
        @logger_label("My Section")
        class _C:
            pass

        assert _C._log_label == "My Section", (  # type: ignore[attr-defined]
            "Static @logger_label should set _log_label to the plain string on the class"
        )

    def test_static_form_is_accessible_as_class_attribute(self) -> None:
        @logger_label("Cls Attr")
        class _C:
            pass

        instance = _C()
        assert instance._log_label == "Cls Attr", (  # type: ignore[attr-defined]
            "Static _log_label should be readable as an instance attribute (class lookup)"
        )

    def test_dynamic_form_sets_property(self) -> None:
        @logger_label("Item {name}")
        class _C:
            pass

        assert isinstance(_C._log_label, property), (  # type: ignore[attr-defined]
            "Dynamic @logger_label (with {}) should set _log_label to a property"
        )

    def test_dynamic_form_resolves_attr(self) -> None:
        @logger_label("Widget {widget_id}")
        class _C:
            widget_id: int = 99

        instance = _C()
        assert instance._log_label == "Widget 99", (  # type: ignore[attr-defined]
            "Dynamic @logger_label should resolve {widget_id} via getattr on the instance"
        )

    def test_dynamic_form_multiple_attrs(self) -> None:
        @logger_label("{first} and {second}")
        class _C:
            first: str = "A"
            second: str = "B"

        instance = _C()
        assert instance._log_label == "A and B", (  # type: ignore[attr-defined]
            "Dynamic @logger_label should resolve multiple {attr} placeholders"
        )

    def test_dynamic_form_missing_attr_literal_fallback(self) -> None:
        @logger_label("X {missing}")
        class _C:
            pass

        instance = _C()
        assert instance._log_label == "X {missing}", (  # type: ignore[attr-defined]
            "Dynamic @logger_label with a missing attribute should fall back to literal {key}"
        )

    def test_decorator_returns_original_class(self) -> None:
        class _C:
            pass

        result = logger_label("Label")(_C)
        assert result is _C, (
            "logger_label decorator should return the original class object unchanged"
        )


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------


class TestSuppressed:
    """suppressed() silences messages temporarily and restores the level."""

    def test_nothing_is_emitted_inside(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger
        with lg.suppressed():
            lg.log_general("hidden", label="T")
        assert _emitted(buf) == "", "no message should be emitted while suppressed"

    def test_level_is_restored_on_exit(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger
        with lg.suppressed():
            pass
        lg.log_property("visible", label="T")
        assert "visible" in _emitted(buf), (
            "messages should be emitted after the context"
        )

    def test_level_is_restored_after_exception(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger
        with pytest.raises(RuntimeError), lg.suppressed():
            raise RuntimeError("deliberate test error")
        lg.log_property("visible", label="T")
        assert "visible" in _emitted(buf), (
            "the level should be restored even when the context raises"
        )

    def test_module_alias_targets_the_shared_logger(self) -> None:
        assert logger_module.suppress_logging.__self__ is logger_module._logger, (  # pyright: ignore[reportPrivateUsage, reportFunctionMemberAccess]
            "suppress_logging should suppress the module's shared logger"
        )


# ---------------------------------------------------------------------------
# Level change without reconfiguring
# ---------------------------------------------------------------------------


class TestBeamLoggerSetLevel:
    """set_level() changes the threshold without touching the log file."""

    def test_set_level_keeps_open_log_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(logger_module, "_LOGS_DIR", tmp_path)
        lg = BeamLogger(LogLevel.PROPERTY, LogOutput.FILE)
        first_file = lg._log_file  # pyright: ignore[reportPrivateUsage]
        assert first_file is not None
        lg.set_level(LogLevel.GENERAL)
        assert lg._log_file is first_file, (  # pyright: ignore[reportPrivateUsage]
            "set_level should keep the same log file handle"
        )
        assert not first_file.closed, "set_level should not close the log file"
        log_files = list(tmp_path.glob("beam_calculator_*.log"))
        assert len(log_files) == 1, "set_level should not create a new log file"
        first_file.close()

    def test_set_level_in_console_mode_opens_no_file(
        self, console_logger: BeamLogger
    ) -> None:
        console_logger.set_level(LogLevel.GENERAL)
        assert console_logger._log_file is None, (  # pyright: ignore[reportPrivateUsage]
            "set_level in CONSOLE mode should not open a log file"
        )

    def test_set_level_filters_lower_messages(
        self, captured_logger: tuple[BeamLogger, io.StringIO]
    ) -> None:
        lg, buf = captured_logger
        lg.set_level(LogLevel.GENERAL)
        lg.log_property("hidden", label="T")
        assert _emitted(buf) == "", "messages below the new level should be dropped"
        lg.log_general("visible", label="T")
        assert "visible" in _emitted(buf), "messages at the new level should be emitted"

    def test_module_alias_targets_the_shared_logger(self) -> None:
        assert logger_module.set_log_level.__self__ is logger_module._logger, (  # pyright: ignore[reportPrivateUsage, reportFunctionMemberAccess]
            "set_log_level should change the module's shared logger"
        )


# ---------------------------------------------------------------------------
# Default log folder
# ---------------------------------------------------------------------------


class TestDefaultLogsDir:
    """default_logs_dir() keeps logs/ from source and moves to the user's folder when packaged."""

    def test_source_run_uses_repository_logs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delattr("sys.frozen", raising=False)
        expected = Path(logger_module.__file__).parent.parent / "logs"
        assert logger_module.default_logs_dir() == expected, (
            "run from source, logs should stay in the repository's logs/"
        )

    def test_packaged_app_uses_user_log_folder(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_user_log_dir(appname: str, appauthor: bool) -> str:
            return f"/user-logs/{appname}-{appauthor}"

        monkeypatch.setattr("sys.frozen", True, raising=False)
        monkeypatch.setattr(
            logger_module.platformdirs, "user_log_dir", fake_user_log_dir
        )
        assert logger_module.default_logs_dir() == Path(
            "/user-logs/beam_calculator-False"
        ), "packaged, logs should go to the per-user log folder, with no author level"
