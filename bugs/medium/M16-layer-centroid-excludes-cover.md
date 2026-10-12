# M16 — `Layer.y_centroid_position` excludes the cover and the stirrup

**Severity:** MEDIUM
**Location:** `src/reinforcement/reinforcement.py:219–259`
(`get_layer_absolute_centroid_with_weight`, `_set_layer_y_centroid_position`),
`src/reinforcement/layer.py:14,22–31`

## Diagnosis
`y_centroid_position` is logged and documented as "cm from bottom edge". In fact it is
the bar-radius centroid plus the spacing of the previous layers, measured from the
**inner face of the stirrup**: the nominal cover and the stirrup diameter are never
added. For a bottom layer of 2φ16 in a 50 cm beam with 2.5 cm cover and φ6.3 stirrups,
it gives 0.8 cm instead of 3.93 cm. A top layer gives 49.2 cm instead of 46.07 cm.

The effective depth `d` is right, because `RebarCalculator.d` subtracts the cover and
the stirrup separately (`rebar_calculator.py:403–408`). For the same reason,
`DEFAULT_DISTANCE_FOR_D_CALCULATION = 1.0` (φ20/2) is correct.

## Impact
- `Layer.has_good_adherence` (used by `AnchorageCalculator.adherence_coefficient`)
  compares this height with the NBR 6118 §9.3.1 zone limits. The bond zone of each
  layer is therefore judged about (cover + stirrup) off.
- The GUI compensates in `pavement_ui/core/engine/readers/reinforcement_reader.py:25–35`
  (adds cover + stirrup diameter, citing this bug). That shift must be removed once
  this is fixed.

## Suggested fix
Add the effective cover and the stirrup diameter in `get_layer_absolute_centroid_with_weight`
(the same terms `RebarCalculator.d` subtracts), and make `get_distance_for_d_calculation`
/ `d` / `d_compressed` stop adding them separately. Alternatively, rename the attribute
to make the reference explicit. Re-check `has_good_adherence` and the anchorage tests
afterwards.
