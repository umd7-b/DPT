"""Compatibility entry point. Prefer python -m features.B_color.src.hair_color_core."""
import importlib
import runpy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    runpy.run_module('features.B_color.src.hair_color_core', run_name='__main__')
else:
    sys.modules[__name__] = importlib.import_module('features.B_color.src.hair_color_core')
