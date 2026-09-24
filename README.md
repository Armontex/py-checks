<div align="center">

<img src="docs/logo.svg" width="112" alt="py-checks">

# py-checks

**Your project's architecture, checked like code.**

English · [Русский](docs/readmes/README.ru.md)

[![ci](https://github.com/Armontex/py-checks/actions/workflows/ci.yml/badge.svg)](https://github.com/Armontex/py-checks/actions/workflows/ci.yml)
[![python](https://img.shields.io/badge/python-3.14%2B-3776AB)](https://www.python.org/)
[![checks](https://img.shields.io/badge/checks-28-2ea043)](#what-is-checked)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-FAB040)](#pre-commit)
[![ruff](https://img.shields.io/badge/linted%20with-ruff-261230)](https://docs.astral.sh/ruff/)
[![pyright](https://img.shields.io/badge/types-pyright%20strict-1f6feb)](https://microsoft.github.io/pyright/)
[![license](https://img.shields.io/badge/license-MIT-750014)](https://github.com/Armontex/py-checks/blob/main/LICENSE)

</div>

---

A linter knows the language; it does not know your project. It will not tell
you that an ORM model has wandered into a use case, that a `Numeric` column
was left without a CHECK, that `datetime.now()` is called in the domain rather
than behind a port. These are not language errors — they are broken
conventions, and until now review caught them: by eye, differently for each
reviewer, from scratch every time.

`py-checks` is an engine for conventions like these. The library brings the
rules, the project brings its architecture: the names of the layers, the list
of sealed zones, where the ORM lives, what bounds a column. Without the
project's tables the rules stay silent — the library does not guess what your
domain is called.

```
src/app/modules/cashout/application/offer.py:34:9: determinism: uuid4() is not deterministic;
    the identifier is handed out at the edge and passed inwards
src/app/infra/database/models/bet.py:51:5: model-columns: stake is a Numeric with no bound;
    money is described by Numeric(18, 4)
src/app/presentation/api/v1/routers/bets.py:22:1: edge-declarations: POST /bets
    did not name a response_model
```

## Why

- **A convention stops being spoken.** The rule is written once, with its
  reason, and checked on every commit — rather than recalled at review by
  whoever remembers it.
- **The rule is universal, the table is yours.** One rule, "this call lives
  only here", covers both the transaction boundary and the ban on `float` in
  the domain. The library contains not one name from your project.
- **A refusal explains itself.** The message says what is wrong and what to
  write instead, not "violation of rule #14".
- **An exemption costs one line and owes a reason.**
  `# check-ok: raw-sql: a liveness probe, there is no ORM form of it` — a mark
  without a reason is itself a violation.
- **We do not do other people's work.** What ruff, pyright and import-linter
  can do stays theirs; what was handed over, and why, is written down in
  [`docs/service.md`](https://github.com/Armontex/py-checks/blob/main/docs/service.md).

## Install

```bash
uv add --dev python-checks
```

Installed as `python-checks`, called as `py-checks`: a neighbour holds the
short name on PyPI, while the command, the settings section and the package
stayed as they were.

Needs Python 3.14+. Dependencies: `libcst`, `pydantic`, `pydantic-settings`,
`rich`, `typer`.

## In a minute

Put a `py-checks.toml` next to `pyproject.toml`:

```toml
src = "src"

[module-length]
max-lines = 300

# Rules that depend on place only work in the zones you name.
[model-columns]
zones = ["infra/database/models"]
instead = { Float = "a Float column drifts; state is exact, use Numeric" }

[determinism]
zones = ["modules/*/domain", "modules/*/application"]
instead = { "datetime.now" = "take the clock as a port", "uuid4" = "hand the id out at the edge" }
```

and run:

```bash
py-checks run          # check `src`
py-checks run --fix    # and repair what repairs itself
py-checks list         # which rules exist and which are on
py-checks explain determinism   # what a rule asks for and what it can be told
py-checks doctor       # and whether the config itself holds together
```

The settings can also live in a `[tool.py-checks]` section of
`pyproject.toml` — but one of the two: two places at once is an error to this
library, not a merge.

## What is checked

Twenty-eight rules in nine groups:

| Group | About |
|---|---|
| `imports` | which package is allowed where, which zone is sealed |
| `placement` | what belongs in this directory and how an operation is shaped |
| `signatures` | module length, nesting depth, the shape of a signature |
| `types` | bounds on fields, the shape of an annotation, immutability |
| `database` | the model's boundary, a column's material, the shape of a query, the schema |
| `effects` | the clock, the dice, and the name of an event in the log |
| `api` | what an entrance declares about itself |
| `errors` | the code a refusal carries |
| `calls` | a function whose call sites can be listed |
| `hygiene` | a ceiling on a dependency |

<details>
<summary>All twenty-eight</summary>

| Code | What fails | Scope |
|---|---|:-:|
| `confined-imports` | a package is imported outside the places set aside for it | file |
| `sealed-imports` | a sealed zone imports a foreign package | file |
| `class-modules` | a module holds what its directory does not allow | file |
| `class-placement` | a class lies somewhere other than where its kind lives | file |
| `operation-shape` | an operation is not shaped like an operation | file |
| `required-class` | a module did not declare the class its directory exists for | file |
| `keyword-only-arguments` | a signature is not written out in full | file |
| `function-length` | a function is longer than the limit | file |
| `module-length` | a module is longer than the limit | file |
| `nesting` | control structures are nested deeper than the limit | file |
| `signature-layout` | a list of two or more entries is written on one line | file |
| `annotation-shapes` | a shape is named such that its fields have no names | file |
| `config-fields` | a settings field carries no bound | file |
| `confined-types` | a field in this part of the tree is declared with a type banned here | file |
| `constant-annotations` | a constant did not say by its type that it is one | file |
| `frozen-dataclasses` | a dataclass in a zone is declared without the required arguments | file |
| `bound-checks` | a bounded column did not restate its bound as a CHECK | file |
| `confined-calls` | a named method was called somewhere it does not belong | file |
| `model-boundary` | an ORM model is declared, built or handed out in the wrong place | file |
| `model-columns` | a column is built out of the wrong material | file |
| `raw-sql` | SQL is written as a string where an expression would do | file |
| `statement-keys` | a statement names a column by string, or goes to the database in a loop | file |
| `schema-drift` | the models and the migrations describe different schemas | environment |
| `determinism` | the code reads the clock, the dice or a new identifier itself | file |
| `log-events` | an event in the log is named by something other than an enum member | file |
| `edge-declarations` | an entrance did not say how it behaves | file |
| `refusals` | a no nobody can branch on | file |
| `confined-functions` | a named function was called from somewhere it may not be | file |
| `dependency-bounds` | a dependency may move to a version nobody has ever run | project |

</details>

Every rule explains itself in full — `py-checks explain <code>` prints the
docstring with the reason and the list of settings. A worked set of tables for
a typical service is in
[`docs/service.md`](https://github.com/Armontex/py-checks/blob/main/docs/service.md).

### Three kinds of rule

What a rule is handed to judge, the rule declares itself, in its `scope`:

- **file** — a parsed source file; most rules are these;
- **project** — the root: the manifest, the agreement of the repository's files with one another;
- **environment** — the same, but it needs a live database or a long run. An ordinary run leaves these out: `py-checks run --all`, or by name; their place is CI.

## Marks

A line can be taken out of a rule's judgement, but you have to say why:

```python
text("SELECT 1")  # db-ok: raw-sql: a liveness probe, there is no ORM form of it
```

The canonical form is `# check-ok: <code>: <reason>`, and it lifts exactly one
rule. Every group has a short word of its own (`# db-ok`, `# type-ok`,
`# signature-ok`, …): a person remembers the group, not twenty-eight codes.

A line may carry several marks — a signature written in a column gathers them
on its last line:

```python
    ) -> object:  # signature-ok: this is how pydantic calls it  # type-ok: raw input
```

A mark with no code, with a typo in the code, or with no reason is a violation
itself. A silently dead mark looks like a disabled check, while the check is in
fact running and simply does not see it.

## pre-commit

```yaml
- repo: https://github.com/Armontex/py-checks
  rev: v0.3.1
  hooks:
    - id: py-checks
      args: [--fix]          # repair what repairs itself
    - id: py-checks-sync     # contracts and `.env.example` rebuilt
```

One hook rather than one per rule: which rules run is the config's decision. A
set of rules is called with `args: [--select, "<code>,<code>"]`; a repeated
flag does the same.

It has to stand **before** `ruff-format`: the autofix writes characters, not
columns, and the project's formatter lays the signature out.

Everything else — ruff, pyright, import-linter, commitizen — the project
declares itself: each has a hook written by its own authors.

## Import contracts

The project's layers are described once, and `.importlinter` is built from
that:

```toml
[contracts.layers]
domain = ["domain"]
application = ["application", "domain"]
presentation = ["presentation", "application"]
```

```bash
py-checks sync           # build
py-checks sync --check   # fail if the file has fallen behind
```

It is built not only from the table but from what is on disk: a layer that
does not exist is left out of the contract — otherwise import-linter would
fail on the first module that is not there. The graph itself is walked by
import-linter's own hook.

The header of the built file can be your own — `header` in `[contracts]`,
`#` included; as with `.env.example`, it is for a project whose comments are
in another language.

## The environment example

The name of a variable is known to the settings field — it declares it as
`validation_alias`, and `config-fields` watches for that. So `.env.example` is
derived from the same classes the variables are read into, and there is no
reason to keep it by hand: it falls out of step silently, and that is noticed
when the variable turns out to be missing in production.

```toml
[env-example]
settings = ["myservice.config.settings:Settings"]
```

The same `py-checks sync` builds it alongside the contracts. The root class is
enough: it has already listed its sections as its own fields, and repeating
that list in the settings would mean keeping a second one that drifts from the
first. A section field does not become a variable — it has no name of its own
in the environment. What goes into the file is the variable's name, its
default, the first paragraph of the class docstring and the field's
`description` if it has one — so the explanation lives next to the field
rather than in a file that outlives it.

The header can be written by the project as well — `header = "# Generated by
py-checks."`, `#` included. It is for a project whose comments are in another
language; an empty one keeps the library's.

The classes are imported rather than read as text: the variable's name is an
attribute's value, assembled by a call, and reading it from the source would
mean performing that call yourself.

## A rule of your own

A rule is a class with four fields and a `run`, declared through entry points.
There is no need to fork the library:

```python
# myproject_checks/_no_print.py
import ast
from collections.abc import Iterator
from typing import ClassVar, Final

from py_checks.config import CheckSettings
from py_checks.core import ParsedFile, Scope, Violation

CODE: Final = "no-print"


class NoPrint:
    """Fails if a `print` was left in the source."""

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = CheckSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = "# my-ok"

    @classmethod
    def run(cls, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        for node in ast.walk(file.tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "print":
                yield Violation.from_node(
                    node=node,
                    path=file.path,
                    code=CODE,
                    message="a print in the source; an event is written to the log",
                )
```

```toml
[project.entry-points."py_checks.checks"]
no-print = "myproject_checks:NoPrint"
```

From there it behaves like a native one: it appears in `list` and `explain`,
obeys `ignore`, and is lifted by a mark.

## Commands

| Command | |
|---|---|
| `py-checks run [paths]` | run the checks; `0` — clean, `1` — violations found |
| `py-checks run --fix` | apply the repairs that are unambiguous |
| `py-checks run --select <code>,<code>` | only the named rules, `ignore` notwithstanding |
| `py-checks run --all` | including the rules that need a live environment |
| `py-checks list` | every rule: code, state, one line of description |
| `py-checks explain <code>` | what a rule asks for and what it can be told |
| `py-checks sync [--check]` | build the import contracts and `.env.example` |
| `py-checks doctor` | check the config itself: typos, dead addresses, rules that say nothing |
| `py-checks mutation diff\|full\|record` | the mutation gate over `mutmut`; needs `python-checks[mutation]` |

## Development

```bash
uv sync
uv run pre-commit install
uv run pytest -q
```

A check is described by folders of examples rather than by a test:
`tests/checks/<code>/` with `ok/` and `bad/` inside, and syrupy compares the
snapshot of the output. Project rules have `tests/projects/<code>__<variant>/`.
The library checks itself: a rule that cannot survive its own repository has
no business reaching anybody else's.

The repository's own conventions are in
[`AGENTS.md`](https://github.com/Armontex/py-checks/blob/main/AGENTS.md).

## License

[MIT](https://github.com/Armontex/py-checks/blob/main/LICENSE) — © 2026 Armontex.
