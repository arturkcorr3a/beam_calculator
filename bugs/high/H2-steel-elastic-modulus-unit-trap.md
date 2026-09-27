# H2 — Steel `elastic_modulus` value is labelled kN/cm² but is really MPa (10× trap)

**Severity:** HIGH
**Location:** `src/properties/steel.py:11–15`

## Diagnosis
Returns `210_000` with docstring "in kN/cm²". Steel E_s = 210 GPa = 210,000 MPa =
**21,000 kN/cm²**. The stored number is the MPa value. **Every current consumer treats
it as MPa and is therefore correct:** `rebar_calculator.py:255,432` do
`Steel.elastic_modulus / 10  # MPa → kN/cm²`; `deformation_checker.py:107` divides by
`ecs` (also MPa); `report_exporter.py:589` prints it as MPa. So this is **not** an
active miscalculation today — but the docstring directly contradicts every call site.

## Impact
Latent 10× error. A future caller trusting the "kN/cm²" docstring and *not* dividing by
10 would be off by an order of magnitude.

## Suggested fix
Change the docstring unit to **MPa**. (Better long-term: store `21_000` kN/cm² once and
delete the scattered `/10` conversions — but that is a coordinated change across all
four call sites.)
