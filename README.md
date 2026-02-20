# beam_calculator

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
