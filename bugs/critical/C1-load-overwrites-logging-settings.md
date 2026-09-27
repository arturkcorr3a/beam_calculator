# C1 — Loading a pavement overwrites the user's logging settings with defaults

**Severity:** CRITICAL
**Location:** `src/persistency/yaml_io.py:64–67`

## Diagnosis
After `config_from_dict(...)` rebuilds an `AppConfig` from the 9 *persisted* fields,
the loop `for field in AppConfig.__dataclass_fields__: setattr(APP_CONFIG, field,
getattr(loaded_config, field))` copies **all** dataclass fields — including
`log_level` and `log_output`, which are intentionally *not* persisted
(`config.py:31–35`). The reconstructed config therefore carries the class defaults
(`"PROPERTY"`, `"both"`), which then clobber whatever the user had set.

## Impact
Opening any saved pavement silently resets the user's logging configuration.
Data-integrity / least-surprise violation.

## Suggested fix
Iterate only over the persisted field names (the keys of `config_to_dict(...)` /
`ConfigDict`), not `AppConfig.__dataclass_fields__`.
