"""Entry point: ``python -m pavement_ui``."""

import sys

from pavement_ui.app import main

# The guard matters: the engine's worker process is spawned and re-imports the
# main module, which must not open a second window there.
if __name__ == "__main__":
    sys.exit(main())
