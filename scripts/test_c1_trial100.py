"""Record tests without PowerShell treating unittest's stderr as command errors."""
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features.C1_lbp.src.trial100 import OUT, write_json
from features.C1_lbp.src.lbp236 import Context


class Tee:
    def __init__(self, stream):
        self.stream = stream

    def write(self, text):
        sys.stdout.write(text)
        self.stream.write(text)

    def flush(self):
        sys.stdout.flush()
        self.stream.flush()


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_c1_*.py')
    started = time.perf_counter()
    with (OUT / 'evidence/unit_integration_tests.log').open('x', encoding='utf-8', newline='\n') as stream:
        result = unittest.TextTestRunner(stream=Tee(stream), verbosity=2).run(suite)
    write_json(OUT / 'evidence/unit_integration_tests.json', dict(Context().lock, tests_run=result.testsRun,
               failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped),
               successful=result.wasSuccessful(), elapsed_seconds=time.perf_counter() - started,
               note='Earlier PowerShell stderr Tee wrapper returned exit1 despite all26 tests passing; this runner records stdout and returns unittest status. No numerical changes needed.'))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
