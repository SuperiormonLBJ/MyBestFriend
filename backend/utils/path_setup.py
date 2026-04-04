"""
Ensures the backend project root is on sys.path so that `utils.*` and `src.*`
are importable regardless of the working directory when a module is loaded.

Import this at the top of any backend module that needs cross-package imports:

    import utils.path_setup  # noqa: F401

Idempotent — safe to call from multiple modules.
"""
import sys
from pathlib import Path

_project_root = str(Path(__file__).parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
