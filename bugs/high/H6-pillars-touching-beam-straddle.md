# H6 — `_pillars_touching_beam` misses a pillar that fully straddles the beam band

**Severity:** HIGH
**Location:** `src/pavement_elements/continuous_beam.py:376–381`

## Diagnosis
`touches_beam` is true when `pillar_low` OR `pillar_high` lies in the beam band. A wide
pillar whose range *contains* the band (`pillar_low < beam_low and pillar_high >
beam_high`) has neither endpoint inside → returns False. `_validate_no_skipped_pillars`
then misses it.

## Impact
A genuine skipped-pillar geometry escapes validation.

## Suggested fix
Use interval overlap: `pillar_low <= beam_high and pillar_high >= beam_low`.
