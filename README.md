# beam_calculator

To install the app (Windows, Fedora, other Linux distributions), see
[INSTALACAO.md](INSTALACAO.md).

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

## Releases

The installers are built and tested by GitHub Actions
([.github/workflows/release.yml](.github/workflows/release.yml)) and published
as a GitHub Release when a tag starting with `v` is pushed:
```bash
git tag v0.1.0
git push origin v0.1.0
```
A tag with a hyphen (`v0.1.0-rc1`) makes a pre-release. Running the workflow by
hand (Actions → Release → Run workflow) builds and tests the packages without
publishing them; they are in the run's artifacts.

To build locally, with the venv active: `packaging/build_linux.sh` (`.tar.gz`),
then `packaging/build_rpm.sh` (`.rpm`, needs `rpm-build`); on Windows,
`packaging\build_windows.ps1` (needs Inno Setup). `packaging/smoke_test.sh`
checks a Linux build.

## License

Copyright (C) 2026 Artur Kalil Corrêa

beam_calculator is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. It is distributed WITHOUT ANY WARRANTY; see [LICENSE](LICENSE).

The packaged app bundles third-party libraries under their own licenses
(PySide6/Qt under LGPL-3.0, anastruct under GPL-3.0, the others under BSD, MIT,
PSF or Apache-2.0); their texts ship in the app folder, in `_internal/licenses/`.
