"""When each main window action is enabled (docs/UI_SPEC.md §8.2) — pure, no Qt."""

from dataclasses import dataclass
from enum import Enum, auto


class ActionId(Enum):
    NEW = auto()
    OPEN = auto()
    SAVE = auto()
    SAVE_AS = auto()
    QUIT = auto()
    FOCUS_PILLARS = auto()
    FOCUS_BEAMS = auto()
    FOCUS_SLABS = auto()
    CLEAR = auto()
    VALIDATE = auto()
    DESIGN = auto()
    RESULTS = auto()
    CONFIG = auto()
    ISOLATED = auto()
    ABOUT = auto()


@dataclass(frozen=True, slots=True)
class ActionContext:
    """What the enabling rules depend on

    Attributes:
        busy: An engine job (pavement design or isolated beam) is running.
        has_elements: At least one element is registered.
        has_results: The last design succeeded.
    """

    busy: bool
    has_elements: bool
    has_results: bool


_ALWAYS = frozenset({ActionId.QUIT, ActionId.ISOLATED, ActionId.ABOUT})
# These use or change the engine state, so they wait while a job runs
_WHEN_IDLE = frozenset(
    {
        ActionId.NEW,
        ActionId.OPEN,
        ActionId.SAVE,
        ActionId.SAVE_AS,
        ActionId.FOCUS_PILLARS,
        ActionId.FOCUS_BEAMS,
        ActionId.FOCUS_SLABS,
        ActionId.VALIDATE,
        ActionId.DESIGN,
        ActionId.CONFIG,
    }
)


def enabled_actions(context: ActionContext) -> frozenset[ActionId]:
    """Return the actions enabled in context"""
    enabled = set(_ALWAYS)
    if not context.busy:
        enabled |= _WHEN_IDLE
        if context.has_elements:
            enabled.add(ActionId.CLEAR)
    if context.has_results:
        enabled.add(ActionId.RESULTS)
    return frozenset(enabled)
