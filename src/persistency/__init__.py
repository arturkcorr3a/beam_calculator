"""Persist and reload a Pavement configuration as YAML.

The persisted document records only the *construction inputs* of a pavement
(pillar geometry, beam layout and wall, slab corners/usage/permanent load).
Everything else — beam axes, centerlines, spans, slab thickness and variable
load — is derived and rebuilt by :meth:`Pavement.resolve`, so it is deliberately
omitted.

The package is split by concern:

- :mod:`~src.persistency.schema` — the ``TypedDict`` document schema,
- :mod:`~src.persistency.serialization` — pavement objects -> plain dict,
- :mod:`~src.persistency.deserialization` — plain dict -> pavement objects,
- :mod:`~src.persistency.yaml_io` — the YAML file I/O (the only place ``yaml`` is used).

The typical workflow is::

    loaded = load_pavement("results/pavement.yaml")
    loaded.resolve()
"""

from src.persistency.deserialization import pavement_from_dict
from src.persistency.serialization import pavement_to_dict
from src.persistency.yaml_io import load_pavement, save_pavement

__all__ = [
    "load_pavement",
    "pavement_from_dict",
    "pavement_to_dict",
    "save_pavement",
]
