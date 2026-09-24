"""The rule implementations, one package per group.

Inside a group, one module per check. Rules that moved to import-linter, ruff
and alembic are not carried over here; what went where is written down in
`docs/current.md`.

A check is one class, and everything it reads the tree with lives inside it:
helpers do not spread across the module, and it is clear whose they are. A
leaf takes `@staticmethod`; a helper that calls another helper takes
`@classmethod`, so it calls through `cls` rather than by the class's name.

Inside the class lives what belongs to the rule. A word of the language does
not belong to a rule: "what is this node called" is `_names.py`, "where does
this file lie" is `_location.py`, "what is declared here" is `_kind.py`. Six
identical `_name` across classes are not six helpers but one, forgotten in six
places.

The word that lifts a rule from the code is declared once per group, in the
package's `_marker.py`. It lifts any check of the group; to lift exactly one,
there is `# check-ok: <code>: <reason>`.
"""
