"""Command-line runner for the examples and saved pavements.

Usage::

    python -m src.main --example t_concreto2 [--log-level ELEMENT] [--log-output console]
    python -m src.main --load saved_fixed [--log-level GENERAL] [--log-output both]
    python -m src.main --load t_concreto2 --display SAVE

``--display`` draws the detailed beams of the resulting pavement: SHOW opens each beam's sheet in a
window, SAVE writes every drawing to
``results/<mmm-dd>/drawing/<name>/``, and BOTH does both.
"""

from __future__ import annotations

import argparse
import inspect
from collections.abc import Sequence
from datetime import date
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from types import ModuleType

import matplotlib.pyplot as plt

from src.config import APP_CONFIG
from src.drawing.api import DrawingError, save_pavement, show_pavement
from src.examples.simple_example import SimpleExample
from src.logger import LogLevel, LogOutput, configure_logger
from src.pavement_elements.pavement import Pavement
from src.persistency import load_pavement

EXAMPLES_DIR = Path(__file__).parent / "examples"
SAVED_DIR = Path(__file__).parent.parent / "saved"
RESULTS_DIR = Path(__file__).parent.parent / "results"
EXAMPLES_PACKAGE = "src.examples"
_INTERFACE_MODULE = "simple_example"


class DisplayMode(StrEnum):
    """What ``--display`` does with the drawings"""

    SHOW = "SHOW"  # open each beam sheet in a window
    SAVE = "SAVE"  # write the DXF, PNG and PDF files
    BOTH = "BOTH"  # save, then show


def build_parser() -> argparse.ArgumentParser:
    """Build the parser for the runner's command-line options"""
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Run an example from src/examples or a pavement saved in saved/.",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--example",
        metavar="NAME",
        help="Example module in src/examples (the .py extension is optional).",
    )
    target.add_argument(
        "--load",
        metavar="PATH",
        help="YAML file in saved/ to load and resolve (.yaml is optional).",
    )
    parser.add_argument(
        "--log-level",
        type=str.upper,
        choices=[level.name for level in LogLevel],
        help=f"Minimum log level to show (default: {APP_CONFIG.log_level.name}).",
    )
    parser.add_argument(
        "--log-output",
        type=str.lower,
        choices=[output.value for output in LogOutput],
        help=f"Where logs are written (default: {APP_CONFIG.log_output.value}).",
    )
    parser.add_argument(
        "--display",
        type=str.upper,
        choices=[mode.value for mode in DisplayMode],
        help=(
            "Draw the detailed beams: SHOW opens each beam sheet, SAVE writes "
            "DXF, PNG and PDF files to results/<mmm-dd>/drawing/<name>/, BOTH does "
            "both (default: no drawing)."
        ),
    )
    return parser


def available_examples() -> list[str]:
    """List the example module names in src/examples, sorted"""
    return sorted(
        path.stem
        for path in EXAMPLES_DIR.glob("*.py")
        if path.stem not in {"__init__", _INTERFACE_MODULE}
    )


def available_saved() -> list[str]:
    """List the YAML file names in saved/, sorted"""
    return sorted(path.name for path in SAVED_DIR.glob("*.yaml"))


def resolve_saved(name: str) -> Path:
    """Map a ``--load`` value to a file in saved/, adding ``.yaml`` if missing"""
    path = SAVED_DIR / name
    return path if path.suffix == ".yaml" else path.with_name(f"{path.name}.yaml")


def find_example(module: ModuleType) -> SimpleExample:
    """Instantiate the single SimpleExample subclass defined in a module

    Subclasses that are only imported into the module are ignored.

    Raises:
        ValueError: If the module defines no subclass or more than one.
    """
    classes = [
        member
        for _, member in inspect.getmembers(module, inspect.isclass)
        if issubclass(member, SimpleExample)
        and member is not SimpleExample
        and member.__module__ == module.__name__
    ]
    if len(classes) != 1:
        names = [cls.__name__ for cls in classes]
        raise ValueError(
            f"{module.__name__} must define exactly one SimpleExample subclass, "
            f"found {len(classes)}: {names}"
        )
    return classes[0]()


def apply_log_options(level: str | None, output: str | None) -> None:
    """Apply the optional log flags to APP_CONFIG and reconfigure the logger

    Args:
        level: A ``LogLevel`` name, or None to keep the current level.
        output: A ``LogOutput`` value, or None to keep the current output.
    """
    if level is not None:
        APP_CONFIG.log_level = LogLevel[level]
    if output is not None:
        APP_CONFIG.log_output = LogOutput(output)
    configure_logger(APP_CONFIG.log_level, APP_CONFIG.log_output)


def drawing_folder(name: str, today: date | None = None) -> Path:
    """Return the folder where SAVE writes a pavement's drawings

    Args:
        name: Name of the example or saved file.
        today: Date of the run; None reads the clock.
    """
    day = (today or date.today()).strftime("%b-%d").lower()
    return RESULTS_DIR / day / "drawing" / name


def display_pavement(pavement: Pavement, mode: DisplayMode, name: str) -> None:
    """Save and/or show the drawings of a resolved pavement

    Args:
        name: Name of the example or saved file, used for the output folder.

    Raises:
        DrawingError: If a beam is not detailed or has items without marks.
    """
    if mode is DisplayMode.SAVE:
        plt.switch_backend("Agg")  # no window is needed
    if mode in (DisplayMode.SAVE, DisplayMode.BOTH):
        folder = drawing_folder(name)
        paths = save_pavement(pavement, folder, pavement_name=name)
        print(f"[DRAWINGS SAVED] {len(paths)} files in {folder}")
    if mode in (DisplayMode.SHOW, DisplayMode.BOTH):
        show_pavement(pavement, pavement_name=name)


def main(argv: Sequence[str] | None = None) -> None:
    """Parse the command line and run the requested example or saved pavement

    Args:
        argv: Arguments without the program name; None reads ``sys.argv``.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    example: str | None = args.example
    load: str | None = args.load
    log_level: str | None = args.log_level
    log_output: str | None = args.log_output
    display: str | None = args.display
    pavement: Pavement | None

    if example is not None:
        name = Path(example).stem
        if name not in available_examples():
            parser.error(
                f"example '{example}' not found in {EXAMPLES_DIR}; "
                f"available: {', '.join(available_examples())}"
            )
        apply_log_options(log_level, log_output)
        pavement = find_example(import_module(f"{EXAMPLES_PACKAGE}.{name}")).run()
        if display is not None and pavement is None:
            parser.error(f"example '{name}' builds no detailed pavement to draw")
    else:
        assert load is not None  # guaranteed by the required exclusive group
        path = resolve_saved(load)
        if not path.is_file():
            parser.error(
                f"file '{load}' not found in {SAVED_DIR}; "
                f"available: {', '.join(available_saved())}"
            )
        name = path.stem
        apply_log_options(log_level, log_output)
        pavement = load_pavement(path)
        pavement.resolve()

    if display is not None and pavement is not None:
        try:
            display_pavement(pavement, DisplayMode(display), name)
        except DrawingError as error:
            parser.exit(1, f"{parser.prog}: error: {error}\n")


if __name__ == "__main__":
    main()
