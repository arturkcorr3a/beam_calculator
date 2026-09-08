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

- **Ignore Tests**: Do not worry about, create, or modify tests for now unless explicitly instructed to do so.
