# beam_calculator

Desktop program for the design of reinforced concrete beams of a typical floor
according to the Brazilian standard ABNT NBR 6118. You draw the floor plan
(pillars, continuous beams and solid slabs) and the program:

- distributes the slab loads to the beams (loads from ABNT NBR 6120);
- pre-sizes slabs and beams and checks slab and beam deflections;
- analyses each continuous beam and designs its longitudinal reinforcement,
  stirrups and, in beams taller than 60 cm, skin reinforcement, with anchorage,
  lap splices and support bars;
- details the bars and computes steel, concrete and formwork quantities;
- prices the beams' steel (SINAPI, 10/2026) and concrete (price given by the
  user) in a net budget, exportable to PDF;
- exports the beam drawings (PDF and DXF) and the design report (PDF), and keeps
  a calculation log of every run.

An isolated continuous beam calculator is also available, outside the floor plan.
Its beams can be saved and opened as `.beam.yaml` files, together with the
project settings.

**Language:** the interface, the reports and the drawings are currently
available in **Portuguese (pt-BR) only**.

> [!WARNING]
> **Technical responsibility disclaimer.** beam_calculator is an academic work
> (undergraduate thesis, UFRGS). Its results do not replace the analysis, the
> judgment and the responsibility of a licensed structural engineer, who must
> check every result before using it in a real project.

## Screenshots

<!-- TODO screenshot: main window with a floor plan → resources/screenshots/main-window.png -->
<!-- TODO screenshot: beam results window → resources/screenshots/beam-results.png -->
<!-- TODO screenshot: beam detailing drawing → resources/screenshots/beam-drawing.png -->

*Screenshots coming soon.*

## Installation

Ready-to-use installers for Windows and Linux are published on the
[Releases](https://github.com/arturkcorr3a/beam_calculator/releases) page; no
Python installation is needed. Step-by-step instructions (in Portuguese) are in
[INSTALACAO.md](INSTALACAO.md).

## Example pavements

The program ships with example pavements and a commented template, in the
`exemplos` folder next to the program (`resources/examples/` in this
repository). Open one with **Arquivo → Abrir exemplo…**: it opens as an untitled
project, so **Salvar** asks where to save your copy and the example stays
unchanged.

- `residencial.pavement.yaml`: residential floor with 21 pillars and 8 slabs;
- `laje_rebaixada.pavement.yaml`: 8 pillars and 3 slabs, one of them lowered;
- `template.pavement.yaml`: a small pavement in which every field is explained (meaning,
  unit and accepted values), to start a project by editing the file by hand;
- `template.beam.yaml`: the same for the isolated beam calculator, a two-span
  beam with every field explained. Open it with the calculator's **Abrir…**
  button (it replaces the project settings with the file's ones).

Project files are plain YAML text and can be edited in any text editor.

## Running from source

Requirements: **Python 3.14** on Windows or Linux.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pavement_ui
```

## Known limitations

<!-- TODO update the known limitations before the final release -->

- **Typical floor only.** One floor at a time; pillars are supports of the
  beams and are not designed.
- **Solid slabs only.** Slabs are pre-sized, loaded and checked for deflection;
  their reinforcement is not designed.
- **Rectangular beams.** The flange (T-beam) contribution of the slab is not
  considered, and the bending moments are not redistributed.
- **Ultimate limit state in bending and shear**, with normal combinations only
  (ABNT NBR 6118, Table 11.1). Torsion and crack width (ELS-W) are not
  checked.
- **Skin bars stop at the pillar faces.** Beams taller than 60 cm get their
  minimum skin bars per span (ABNT NBR 6118, 17.3.5.2.3), detailed, drawn and
  counted in the quantities, marked "(PELE)". The bars of each span run in its
  clear span only, from pillar face to pillar face, with no anchorage length
  into the supports.
- **Deflection (ELS-DEF)** is checked against the visual acceptability limit
  l/250 only.
- **One steel and one concrete class per project**, passive reinforcement only
  (no prestressing).
- **Building loads only**: no vehicle loads.

## Development

The engine lives in `src/` and the PySide6 interface in `pavement_ui/`. Code and
documentation conventions are in [AGENTS.md](AGENTS.md); see
[CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue or a pull request.
How versions are numbered and published is in its
[Releases](CONTRIBUTING.md#releases) section.

### Code checks

```bash
ruff check .
ruff format --check <changed files>
pyright                      # strict, pavement_ui (configured in pyproject.toml)
pyright src tests            # the engine and the tests
PYTHONPATH=. lint-imports    # GUI layering contracts in pyproject.toml
```

### Testing

```bash
pytest
```

This runs the whole suite and prints a coverage summary with the missing lines;
coverage settings are in `.coveragerc`. An HTML report is written to `htmlcov/`
(`xdg-open htmlcov/index.html`).

## Citation

If you use beam_calculator in academic work, please cite it as described in
[CITATION.cff](CITATION.cff) (GitHub shows it under "Cite this repository").

## License

Copyright (C) 2026 Artur Kalil Corrêa

beam_calculator is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. It is distributed WITHOUT ANY WARRANTY; see [LICENSE](LICENSE).

The packaged app bundles third-party libraries under their own licenses
(PySide6/Qt under LGPL-3.0, anastruct under GPL-3.0, the others under BSD, MIT,
PSF or Apache-2.0); their texts ship in the app folder, in `_internal/licenses/`.

Tables reproduced from ABNT NBR 6120:2019 and from Carvalho & Figueiredo Filho
(2014), in `src/data/`, are cited at their source in each module.

---

Leia em português: [LEIAME.md](LEIAME.md)
