# L11 — `rebar_choice_options` changes type between init and use

**Severity:** LOW
**Location:** `src/reinforcement/reinforcement.py:41,65`

## Diagnosis
Initialised as `[]` (list), reassigned to a dict at line 65 and iterated with
`.values()`. Strict-typing smell.

## Impact
Type-checker / maintainability; no runtime effect.

## Suggested fix
Initialise `{}` with a proper annotation.
