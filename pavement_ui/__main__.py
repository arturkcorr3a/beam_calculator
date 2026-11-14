"""Entry point: ``python -m pavement_ui``."""

import multiprocessing
import sys

from pavement_ui.app import main

# The guard matters: the engine's worker process is spawned and re-imports the
# main module, which must not open a second window there.
if __name__ == "__main__":
    # In the packaged app the worker starts this same executable; this runs the
    # worker there instead of the window (a no-op when run from source)
    multiprocessing.freeze_support()
    sys.exit(main())
