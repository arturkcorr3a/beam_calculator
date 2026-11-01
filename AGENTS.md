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

    Optional paragraph with additional context or caveats.

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
7. **No formulas** — never write formulas or equations in docstrings. Describe the rule in words and cite the norm section in References.

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
  - `pavement_ui/core/model/settings.py` — add/remove/rename the field in `ConfigValues` (or `LogValues` for log settings)
  - `pavement_ui/core/engine/config_mapper.py` — map the field between `ConfigValues` and `AppConfig`
  - `pavement_ui/presentation/dialogs/config/` — the form section that edits the field

- **Patch notes (default step)**: every change set ends with a `docs/patches/NN-patch-<kebab-case-slug>.md` file describing the change for the TCC report. `NN` is a two-digit sequence number, one above the highest existing file in `docs/patches/` (the first is `01`). Write it in pt-BR, after the test run (so the numbers are real), with these sections:
  - **Contexto** — why the change was made
  - **Referências normativas** — norm items involved, with a short quote or paraphrase
  - **Alterações por arquivo** — link to each changed file and what changed in it
  - **Mudanças de comportamento/resultados** — old → new values of affected results
  - **Testes** — tests added or changed

---

## Interface (`pavement_ui`)

The desktop GUI follows [docs/UI_SPEC.md](docs/UI_SPEC.md).

- Business rules live in the engine (`src/`). **Never** reimplement calculation, inclusion rules or validation in the UI.
- Only `pavement_ui/core/engine/` imports `src.*`. `src/` never imports `pavement_ui`.
- `pavement_ui/core` never imports PySide6. `pavement_ui/presentation` never imports `src` nor `pavement_ui.core.engine`.
- Every user-visible text lives in `pavement_ui/presentation/text/strings/` (pt-BR). Code identifiers stay in English.
- One file = one responsibility (one public class or widget). Target ≤ 200 lines; hard cap 300.
- Engine changes are limited to those listed in docs/UI_SPEC.md §5.3, unless explicitly requested.
- No automated tests for `pavement_ui`; engine changes in `src/` get tests per the conventions below.
- Checks before finishing a stage:
  - `.venv/bin/ruff check pavement_ui && .venv/bin/ruff format --check pavement_ui`
  - `.venv/bin/pyright` (strict, configured in `pyproject.toml`)
  - `PYTHONPATH=. .venv/bin/lint-imports` (layering contracts in `pyproject.toml`)
  - `.venv/bin/pytest` when `src/` changed

---

## Source-of-truth tests (`tests/carvalho_source_of_truth/`)

These tests encode worked examples from Carvalho (`docs/carvalho-examples/`). **Do not modify them unless the user explicitly asks.** In particular, never change inputs, expected values, tolerances or `xfail` markers to make a test pass: a failure means the engine disagrees with the book. The only allowed edit without an explicit request is keeping the code runnable after an engine API change (imports, constructor/attribute names, unit conversions), without changing what is asserted.

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
