"""Compatibility entry point. Prefer python -m retrieval.search_geometry."""
import importlib
import runpy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    runpy.run_module('retrieval.search_geometry', run_name='__main__')
else:
    sys.modules[__name__] = importlib.import_module('retrieval.search_geometry')
