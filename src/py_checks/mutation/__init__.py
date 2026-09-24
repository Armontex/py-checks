"""The mutation gate: a push leaves no line whose breakage no test would notice.

A surviving mutant is a line that was changed while the tests still passed.
Their list replaces reading the tests by eye with the question "do they check
anything at all?".

The gate is a record, not zero: `record` writes how many survivors each module
has, and `diff` and `full` refuse if any module has more. Raising the record
is a change that explains which survivor is not worth a test.

mutmut is called as a process, the way `schema-drift` calls alembic: the
library reads its output rather than importing it. The compatible version is
pinned in the `python-checks[mutation]` extra — the output format is the
contract between the two.
"""

from py_checks.mutation._constants import BASELINE, SECTION
from py_checks.mutation._errors import GateError
from py_checks.mutation._gate import Diffed, Gate, Verdict, gate
from py_checks.mutation._mutmut import Tally
from py_checks.mutation._settings import Mutation, mutation

__all__ = [
    "BASELINE",
    "SECTION",
    "Diffed",
    "Gate",
    "GateError",
    "Mutation",
    "Tally",
    "Verdict",
    "gate",
    "mutation",
]
