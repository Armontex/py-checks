"""An example environment file, built from the project's settings classes.

The field knows the variable's name — it declares it as `validation_alias`,
and the `config-fields` rule sees to that. So the list of variables follows
from the same classes that read them, and a file listing them is not worth
keeping by hand: it drifts silently, and that is noticed when a variable turns
out to be missing in production.
"""

from py_checks.environment._constants import FILE, SECTION
from py_checks.environment._render import render
from py_checks.environment._settings import Example, example

__all__ = ["FILE", "SECTION", "Example", "example", "render"]
