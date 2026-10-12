# M2 — `nominal_covering` uses global `APP_CONFIG` concrete, not the element's own

**Severity:** MEDIUM (latent)
**Location:**
- `src/structural_elements/rectangular_beam.py:13–37` — `_BeamMeta.nominal_covering` (class-level property)
- `src/pavement_elements/slab.py:50–73` — `_SlabMeta.nominal_covering` (same pattern)
- Consumers (all class-level): `src/reinforcement/reinforcement.py:140,150,402`,
  `src/calculators/anchorage_calculator.py:168`, `src/calculators/rebar_calculator.py:436`,
  `src/pavement_elements/continuous_beam.py:214`,
  `pavement_ui/core/engine/isolated_beam_engine.py:63`,
  `pavement_ui/core/engine/readers/beam_reader.py:62`,
  `pavement_ui/core/engine/readers/design_point_reader.py:45`

## Diagnosis
The "concrete greater than minimum" cover discount (NBR 6118 §7.4.7.6) reads
`APP_CONFIG.pavement_concrete`, not the element's own `concrete`. Because
`nominal_covering` is a metaclass property, it cannot see the instance.

Currently **latent**: every production path builds beams with the configured
concrete:
- `BeamCalculator` (`beam_calculator.py:273`) uses `APP_CONFIG.pavement_concrete`.
- The isolated-beam engine applies the beam's `concrete_key` to the config before
  constructing the section.

The two values only differ when someone constructs `RectangularBeam` directly with a
different concrete (examples, tests).

## Impact
If a beam is ever built with a concrete different from the configured one: wrong
nominal cover (±0.5 cm), so wrong effective depth and anchorage space.

## Suggested fix
Make `nominal_covering` an instance property that reads `self.concrete`. This touches
every class-level call site listed above (src and `pavement_ui/core/engine`). Apply the
same change to `Slab`, or document the single-concrete assumption explicitly.

## User Edit

Leave it like that, and change the code so EVERYWHERE uses the APP_CONFIG concrete
