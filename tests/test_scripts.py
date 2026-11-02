"""pytest wrapper for the stdlib script tests that pytest does not collect (QUALITY_AUDIT §7 L):
tests/engine_supabase_test.py (mock Supabase/Worker) and tests/test_prep_pages.py (top-level script).
Each runs in its own interpreter; it must exit 0 and print "ALL TESTS PASSED"."""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.parametrize("script", ["engine_supabase_test.py", "test_prep_pages.py"])
def test_script(script):
    r = subprocess.run([sys.executable, os.path.join(HERE, script)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8"), timeout=900)
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode == 0, out[-4000:]
    assert "ALL TESTS PASSED" in r.stdout, out[-4000:]
