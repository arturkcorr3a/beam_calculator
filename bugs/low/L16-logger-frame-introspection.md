# L16 — `logger._log` frame introspection + missing `DISABLED` style

**Severity:** LOW
**Location:** `src/logger.py:82,88–105`

## Diagnosis
Recovers a label by walking `f_back.f_back`; any indirection shifts the frame and
mislabels. `LogLevel.DISABLED` has no `_LEVEL_STYLES` entry, so `_LEVEL_STYLES[level]`
would `KeyError` if ever logged at that level (only used as a threshold today, so it
doesn't fire).

## Impact
Cosmetic (wrong tag) plus a latent `KeyError` if `DISABLED` is ever passed as a message
level.

## Suggested fix
`_LEVEL_STYLES.get(level, "")`; document the frame-depth assumption.
