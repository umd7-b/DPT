"""Compatibility entry point. Prefer python -m shared.detect_landmarks."""
import importlib
import runpy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == '__main__':
    runpy.run_module('shared.detect_landmarks', run_name='__main__')
else:
    sys.modules[__name__] = importlib.import_module('shared.detect_landmarks')
