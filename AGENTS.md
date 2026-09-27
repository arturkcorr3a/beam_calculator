# AGENTS

## Code tags

### `# PAPER`

Comments tagged `# PAPER` mark places where a literature reference needs to be found and cited (e.g., a Brazilian standard, a textbook, or a technical paper that justifies the method used). **Never remove a `# PAPER` comment.** Add the reference once found, but keep the tag so it remains searchable.

## Docstring standard

All Python docstrings follow **Google style**.

### Structure

```python
def function(param: type) -> return_type:
    """One-line imperative summary (no trailing period).

    Optional paragraph with additional context, formulas, or caveats.

    Args:
        param: Meaning, valid range, and physical unit. Do NOT repeat the type
            — it is already in the signature.

    Returns:
        What is returned, including units. Omit if the function returns None
        or the summary already makes it fully obvious.

    Raises:
        ExceptionType: Condition that triggers it. List only exceptions the
            function itself explicitly raises.

    References:
        ABNT NBR XXXX:YYYY — Section X.X.X
        Author (year) — Chapter/Section title, page.
    """
```

### Section rules

1. **Summary line** — imperative verb phrase, max one line, no trailing period.
2. **Args** — include only parameters whose meaning, unit, or valid range is non-obvious from name and type alone. Skip `self`. Indent continuation lines by 4 spaces.
3. **Returns** — include units. Omit for `None` returns and for trivially obvious returns (e.g. a `bool` property named `is_cracked`).
4. **Raises** — list only exceptions raised explicitly in the body. Omit if none.
5. **References** — normative standards and textbook citations. Format: `ABNT NBR XXXX:YYYY — Section X.X.X` or `Author (year) — Section/Table identifier`. Place after all other sections.
6. **Attributes** (classes only) — list public instance attributes with their physical unit when relevant. Skip attributes already fully described by their name and type annotation.

### When to prompt the user

Before writing or updating a docstring, if any of the following is unclear, ask the user before proceeding:

- The **physical unit** of a parameter or return value (e.g. is this in kN or kN/m²?)
- The **valid range or constraint** for a numeric parameter (e.g. must be >= 1.0?)
- **Which normative section** the function implements (e.g. ABNT NBR 6118 — which section?)
- The **intent** of a non-obvious parameter name

Do not guess units or normative references — incorrect documentation is worse than no documentation.

---

## Project Rules

- **Strict typing**: All Python code must pass Pylance's `strict` type-checking mode (`.vscode/settings.json` sets `"python.analysis.typeCheckingMode": "strict"`). This means:
  - Every function and method must have fully annotated parameters and return types.
  - Bare `dict` or `list` without type arguments is not allowed — use `dict[str, object]`, a `TypedDict`, or a concrete parameterized type.
  - `**spread` into a `TypedDict` constructor is not allowed when the source is `dict[str, object]` — construct TypedDicts with explicit keyword arguments instead.

- **`AppConfig` ↔ persistency sync**: Whenever a field is added to, removed from, or renamed in `src/config.py`'s `AppConfig`, the persistency layer must be updated in lockstep:
  - `src/persistency/schema.py` — add/remove/rename the field in `ConfigDict`
  - `src/persistency/serialization.py` — add/remove/rename the field in `config_to_dict`
  - `src/persistency/deserialization.py` — add/remove/rename the field in `config_from_dict`

---

## Testing conventions

When writing tests,
follow the patterns established in `tests/properties/`:

- **Class-based tests** (`class TestXxx`), generally one discrete named method per
  case. `@pytest.mark.parametrize` is allowed when a single behavior has many
  mechanical input/output variations (e.g. a lookup-table grid) and separate
  methods would only duplicate one assertion; keep distinct behaviors in
  distinct methods.
- **Float comparisons**: `assert_approx(actual, expected, "message")` from
  `tests.helpers`.
- **Exact/integer comparisons**: `assert x == expected, "message"`.
- **`APP_CONFIG` overrides**: `monkeypatch.setattr(APP_CONFIG, "field", value)`.
- **Fixtures**: module-level `@pytest.fixture` with full return-type annotations.
  No `conftest.py`.
- **Test doubles**: prefer `types.SimpleNamespace` over `MagicMock` — it fails
  loudly on missing attributes instead of fabricating them.
- **Imports**: `from src.*` for production code, `from tests.helpers import
  assert_approx`.
- **Docstrings**: Google-style, imperative summary, no trailing period (per the
  docstring standard above).
