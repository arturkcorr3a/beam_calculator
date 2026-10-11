# M16 — `Layer.y_centroid_position` excludes the cover and the stirrup

**Severity:** MEDIUM
**Location:** `src/reinforcement/reinforcement.py:218–259`
(`get_layer_absolute_centroid_with_weight`, `_set_layer_y_centroid_position`),
`src/reinforcement/layer.py:14,22–31`

## Diagnosis
`y_centroid_position` is documented as "cm from bottom edge", but it is computed as the
bar-radius centroid plus the spacing of the previous layers, measured from the **inner
face of the stirrup**. The nominal cover and the stirrup diameter are never added. For a
bottom layer of 2φ16 in a 50 cm beam with 2.5 cm cover and φ6.3 stirrups it gives 0.8 cm
instead of 3.93 cm; a top layer gives 49.2 cm instead of 46.07 cm. The effective depth
`d` is right because `RebarCalculator.d` subtracts the cover and the stirrup separately.

## Impact
- `Layer.has_good_adherence` compares this height with the NBR 6118 §9.3.1 zone limits,
  so the bond zone of each layer is judged about (cover + stirrup) off.
- `ContinuousBeam.report` prints layer heights that are not from the bottom edge.
- The GUI compensates in `pavement_ui/core/engine/readers/reinforcement_reader.py`
  (adds cover + stirrup diameter); that shift should be removed once this is fixed.

## Suggested fix
Add the effective cover and the stirrup diameter in `get_layer_absolute_centroid_with_weight`
(the same terms `RebarCalculator.d` subtracts), or rename the attribute to make the
reference explicit. Re-check `has_good_adherence` and the anchorage tests afterwards.
