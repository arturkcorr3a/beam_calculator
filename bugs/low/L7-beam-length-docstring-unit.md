# L7 — `RectangularBeam` constructor docstring says `length` is metres; code uses cm

**Severity:** LOW
**Location:** `src/structural_elements/rectangular_beam.py:75` (vs `12`, `105`, `114`)

## Diagnosis
`UNITS["length"]="cm"`, and `self.length/100.0` is printed as metres → `self.length` is
stored in **cm**, contradicting the "(m)" docstring.

## Impact
A caller following the docstring passes metres and builds a beam 100× too short.

## Suggested fix
Correct the docstring to "(cm)".
