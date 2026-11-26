"""Import the integration modules without executing its HA entry point.

The codec and model modules are pure Python; only ``__init__.py`` needs Home
Assistant. Registering the package here keeps the tests fast and independent of
an installed Home Assistant while still exercising the real files.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "custom_components.pobovi_ring"

if "custom_components" not in sys.modules:
    sys.modules["custom_components"] = types.ModuleType("custom_components")

if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT / "custom_components" / "pobovi_ring")]
    sys.modules[PACKAGE] = package
