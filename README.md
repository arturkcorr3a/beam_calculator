# beam_calculator

## Desktop interface

The PySide6 interface (*beam_calculator*) lives in `pavement_ui/` and follows
[docs/UI_SPEC.md](docs/UI_SPEC.md). Run it from the repository root:
```bash
python -m pavement_ui
```

## Code checks

```bash
ruff check pavement_ui && ruff format --check pavement_ui
pyright                      # strict, configured in pyproject.toml
PYTHONPATH=. lint-imports    # GUI layering contracts in pyproject.toml
```

## Testing

Run the test suite with coverage:
```bash
pytest
```

This will automatically:
- Run all tests
- Generate coverage report in the terminal with missing lines
- Create an HTML coverage report in `htmlcov/` directory

### View Coverage Report

**Terminal output:** Coverage summary is shown automatically after running `pytest`

**HTML report:** Open the detailed HTML report by running:
```bash
xdg-open htmlcov/index.html
```

### Manual Coverage Options

If you need specific coverage reports:
```bash
# Terminal only with missing lines
pytest --cov --cov-report=term-missing

# HTML report only
pytest --cov --cov-report=html

# Both terminal and HTML
pytest --cov --cov-report=term-missing --cov-report=html
```

### Coverage Configuration

Coverage settings are configured in `.coveragerc` to exclude:
- All `__init__.py` files
- All test files in `tests/` directory
