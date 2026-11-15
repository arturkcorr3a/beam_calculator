# Contributing to beam_calculator

Thank you for your interest. Please read this page before opening an issue or a
pull request.

## Project status

beam_calculator is an undergraduate thesis (TCC) under development. **Until the
thesis defense, pull requests may not be accepted**, since the code is part of
an academic evaluation. **Issues are very welcome**, especially bug reports and
calculation errors.

## Reporting a calculation error

Open an issue with:

1. **Input data**: the values you entered or, better, the project file
   (`.yaml`, saved with *Arquivo → Salvar*) attached to the issue.
2. **Obtained result**: what the program gave, with the element (e.g. beam V3,
   span 2) and, if possible, the relevant part of the calculation log
   (`beam_calculator_<date-time>.log`; see [INSTALACAO.md](INSTALACAO.md) for
   its folder).
3. **Expected result**: the value you expected.
4. **Source of the expected result**: the standard item (e.g. ABNT NBR 6118,
   17.3.5.2.1), the book and page, or your hand calculation.

Calculation errors are not security vulnerabilities; report them as normal
issues (see [SECURITY.md](SECURITY.md)).

## Development environment

You need **Python 3.14**.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pavement_ui            # run the interface
```

## Checks before a pull request

All of these must pass:

```bash
pytest
ruff check .
ruff format --check <changed files>   # format only the files you changed
pyright                                # pavement_ui, strict
pyright src tests                      # the engine and the tests
PYTHONPATH=. lint-imports              # GUI layering contracts
```

Some committed files are intentionally not ruff-formatted, so never run
`ruff format` on whole folders.

## Code standards

Follow [AGENTS.md](AGENTS.md), which holds the project rules. In short:

- Docstrings in **Google style**, with units and a `References:` section.
- **Every criterion taken from a standard cites its item** (e.g.
  `ABNT NBR 6118:2014 — Section 17.3.5.2.1`) in the docstring's References.
- Comments tagged **`# PAPER`** mark places that still need a literature
  reference; never remove the tag.
- Strict typing (pyright strict), and the GUI layering rules of AGENTS.md.
- Engine changes in `src/` come with tests; the source-of-truth tests that
  encode published worked examples must not be changed.

## Workflow

- One branch per change, created from `master`.
- Open a pull request to `master`, describing what changed and why.
- Write descriptive commit messages.

## License

By contributing, you agree that your contributions are distributed under the
project license, the [GNU General Public License v3.0 or later](LICENSE)
(GPL-3.0-or-later).
