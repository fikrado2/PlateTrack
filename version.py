"""Root re-export of the single source of truth for version/branding.

The real values live in ``platetrack/version.py`` so the packaged app can
import them without depending on the repository layout.  Build scripts
(PyInstaller metadata, Inno Setup preprocessor) read the values from here.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from platetrack.version import (  # noqa: F401,E402
    APP_NAME,
    COPYRIGHT,
    PUBLISHER,
    __version__,
)

if __name__ == "__main__":
    # e.g.  python version.py  ->  1.0.0  (used by build.ps1)
    print(__version__)
