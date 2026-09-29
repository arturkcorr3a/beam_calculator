# L12 — `parent: QWidget = None` should be `QWidget | None = None`

**Severity:** LOW
**Location:** `beam_gui.py:126,178,199,372`; `pavement_gui.py:116,857,945,1110`

## Diagnosis
Non-Optional annotation with `None` default — a strict-Pylance error (suppressed by
file-level `# type: ignore`, but still off-standard).

## Impact
Annotation / standard violation only; no runtime effect.

## Suggested fix
`parent: QWidget | None = None`.
