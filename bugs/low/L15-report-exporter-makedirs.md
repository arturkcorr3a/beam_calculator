# L15 — `report_exporter` `makedirs(dirname(...))` fragile on odd paths

**Severity:** LOW
**Location:** `src/gui/report_exporter.py:400,425`

## Diagnosis
Safe for the default filename, but `dirname` of an unusual relative path could misbehave.
(File is `# type: ignore` / "AI-Generated -> re-do".)

## Impact
Minor; possible error on unusual paths.

## Suggested fix
`d = os.path.dirname(filepath); if d: os.makedirs(d, exist_ok=True)`.
