"""Convert the engine's rule exceptions into EngineRuleError."""

from collections.abc import Generator
from contextlib import contextmanager

from pavement_ui.core.errors import EngineRuleError


def rule_message(error: ValueError | KeyError) -> str:
    """Return the engine's original text of a rule exception

    ``str(KeyError)`` wraps the text in quotes, so the first argument is used.
    """
    if isinstance(error, KeyError) and error.args:
        return str(error.args[0])
    return str(error)


@contextmanager
def engine_rules() -> Generator[None]:
    """Re-raise the engine's ValueError and KeyError as EngineRuleError

    The engine signals rule violations with ValueError and failed NBR 6120 table
    lookups with KeyError (docs/UI_SPEC.md §5.2, E17).

    Raises:
        EngineRuleError: Carrying the engine's original message.
    """
    try:
        yield
    except (ValueError, KeyError) as error:
        raise EngineRuleError(rule_message(error)) from error
