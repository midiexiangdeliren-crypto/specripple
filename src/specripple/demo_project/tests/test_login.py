"""Executable acceptance checks for REQ-001 and TASK-001 (stdlib only).

Runs standalone: `python tests/test_login.py` exits 0 when all documented
acceptance cases hold, 1 otherwise.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from login import login  # noqa: E402

CASES = [
    (("alice@example.com", "wonderland"), "session issued"),
    (("alice@example.com", "wrong-password"), "login failed"),
    (("ghost@example.com", "wonderland"), "login failed"),
]

failures = [
    "login%s -> %r, expected %r" % (args, login(*args), want)
    for args, want in CASES
    if login(*args) != want
]
for line in failures:
    print("FAIL " + line)
print("%d/%d cases passed" % (len(CASES) - len(failures), len(CASES)))
raise SystemExit(1 if failures else 0)
