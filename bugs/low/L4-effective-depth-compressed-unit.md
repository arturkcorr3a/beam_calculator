# L4 — `effective_depth_compressed` annotated with unit `cm²` (it's a length, cm)

**Severity:** LOW
**Location:** `src/checkers/deformation_checker.py:31`; `slab_deformation_checker.py:47`

## Diagnosis
Unit comment `# cm²` on an effective depth (d'), which is a length.

## Impact
Annotation only; misleading.

## Suggested fix
Change to `# cm`.
