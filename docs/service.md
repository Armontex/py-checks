# The settings of a typical service

English · [Русский](readmes/service.ru.md)

The library does not know what a project's layers are called or where its ORM
lives: a service has `domain` and `infra/database`, a command-line utility has
no such layers at all. So there are no tables inside it — the tables arrive
with the template that generates the project.

What follows is what four services had in common at the time of the move. They
are called **A**, **B**, **C** and **D** below, and where they differed, it is
said. This is both a draft for the template and a record of what was held to
be right — with the reason, every time, because a rule without one is a rule
the next reader deletes.

The ruff and pyright settings are here for the same reason: the library does
not carry them, the template lays them down, and from then on they are the
project's own files.

## How to read this

Every rule is written to the same shape:

> **What it catches** — one sentence.
> **The table** — the TOML the project writes.
> **Why** — the failure the rule is paid to prevent.
> **Instead of** — the off-the-shelf tool that was considered, and what it
> costs, measured on the four services rather than guessed at.
> **The mark** — the word that lifts the rule from a line, with a reason.

| Section | |
|---|---|
| [1. One service, whole](#1-one-service-whole) | the entire config of a service, read line by line |
| [2. Where the settings live](#2-where-the-settings-live) | one file, not two |
| [3. Who checks what](#3-who-checks-what) | ruff, pyright, import-linter, us |
| [4. The hooks](#4-the-hooks) | what ships with the library, what the project declares |
| [5. The rules](#5-the-rules) | all twenty-eight, by group |
| [6. The generated files](#6-the-generated-files) | contracts and `.env.example` |
| [7. What is handed to others](#7-what-is-handed-to-others) | ruff, pyright, pytest-alembic, symlinks |

## 1. One service, whole

Before the rules one by one, here is the whole thing at once: `parcels`, an
invented delivery service — three modules (`orders`, `pricing`, `tracking`),
Postgres behind SQLAlchemy, Kafka at the edge, FastAPI on top. Its layout:

```
src/parcels/
├── bootstrap/        the application, the consumer, the probes
├── config/           settings, one class per source
├── entrypoints/      the commands of the executable
├── infra/database/   models, repositories, the unit of work
├── ioc/              the container and its providers
├── modules/
│   ├── orders/{domain,application}
│   ├── pricing/{domain,application}
│   └── tracking/{domain,application}
├── observability/    logs, metrics, traces
├── presentation/     the HTTP edge and the consumers
└── shared/           primitives, ports, the event vocabulary
```

And its entire `py-checks.toml`, with the reason on every table. Nothing in it
comes from the library: the library brings rules, this file brings the
architecture.

```toml
# Where our own code is. Everything else — tests, migrations, generated code —
# is judged by the tools that own it.
src = "src"

# --- Imports and boundaries -------------------------------------------------

[contracts]
# Tying the layers together is the whole of their work, so they may see all.
composition-root = ["ioc", "bootstrap", "entrypoints"]

# Dependencies point inwards. `presentation` deliberately does not see
# `domain`: the edge translates into the application's DTOs and back, and a
# router reading a domain object ties the shape of the outside world to the
# shape of the rules.
[contracts.layers]
domain = ["domain", "shared"]
application = ["domain", "application", "shared"]
infra = ["domain", "application", "infra", "shared", "config"]
presentation = ["application", "presentation", "shared", "config"]
observability = ["observability", "shared", "config"]
config = ["config", "shared"]
shared = ["shared"]

# A package -> the directories allowed to import it. A line here widens a
# framework's reach through the codebase, so it is added deliberately.
[confined-imports]
sqlalchemy = ["infra/database", "ioc"]
asyncpg = ["infra/database", "ioc"]
alembic = ["infra/database"]
aiokafka = ["infra/kafka", "ioc"]
fastapi = ["presentation", "bootstrap"]
starlette = ["presentation", "bootstrap"]
dishka = ["ioc", "bootstrap", "presentation"]
uvicorn = ["entrypoints"]
typer = ["entrypoints"]
prometheus_client = ["observability"]
sentry_sdk = ["observability"]

[sealed-imports]
# The rules and the interfaces around them: a DTO here is a dataclass, not a
# framework's model. `shared` is sealed with them because every module's
# domain imports it — a framework that reaches it is inside every sealed layer
# at once.
zones = ["modules", "shared"]

[sealed-imports.allow]
# A use case leads and may therefore say what happened; the rules are true
# whether or not anybody is listening.
application = ["structlog"]

# --- The layout: one block per directory ------------------------------------

# `only` — what may be declared here; `home` — what may be declared ONLY here;
# `suffix` — the class this directory exists for; `required` — a module here
# must declare one; `operation` — the shape of an operation kept here.

[layout."application/use_cases"]
only = ["class"]
suffix = "UseCase"
required = true
# One public door, and three fields through it. What came from outside and
# filled four is a thing with a name: a command, a query, a DTO.
operation = { method = "execute", max-arguments = 3, forbids = ["UnitOfWork"] }

[layout."application/services"]
only = ["class"]
suffix = "Service"
required = true
# A service has as many doors as its entity has transitions, so `method` is
# not set: a caller who would have to make three calls will make two.
operation = { forbids = ["UnitOfWork"] }

[layout."application/ports"]
only = ["port", "alias"]
home = ["port"]

[layout."application/dto"]
only = ["dataclass", "alias"]
home = ["dataclass"]
# Only inside the application: a dataclass in the bootstrap or in
# observability is three fields put side by side, not a DTO.
area = "application"

# A domain value object is a dataclass too: once a kind has a home, it lives
# only in the blocks that claim it, so every home is named.
[layout."modules/*/domain"]
home = ["dataclass"]

# A schema declared next to a route accidentally becomes shared, so request
# and response live apart: one class for both ends is a request that grew a
# field the response never wanted.
[layout."presentation/schemas/requests"]
only = ["model", "alias"]
home = ["model"]

[layout."presentation/schemas/responses"]
only = ["model", "alias"]
home = ["model"]

# Settings are a model as well, and this is their home.
[layout.config]
home = ["model"]
suffix = "Settings"
required = true

[layout."infra/database/models"]
suffix = "Model"
required = true
# The home of the ORM models: `model-boundary` reads the same table rather than
# naming these two directories a second time in one of its own.
orm = "declared"

[layout."infra/database/repositories"]
only = ["class"]
suffix = "Repository"
required = true
# Building a model means writing a row, and a row is written here.
orm = "built"

# The port of a repository and its implementation lawfully live in two places.
[layout."shared/ports"]
only = ["port", "alias"]

[layout.errors]
only = ["error", "alias"]
home = ["error"]

[layout.exceptions]
home = ["error"]

# --- Length, depth, shape ---------------------------------------------------

[function-length]
max-lines = 50

[module-length]
max-lines = 600

# `with` is deliberately absent: a nested `with` is caught by ruff `SIM117`,
# with an autofix and a ready answer.
[nesting]
try = 1
if = 2

[signature-layout]
calls = true

# --- Types ------------------------------------------------------------------

[frozen-dataclasses]
zones = ["modules"]
options = ["frozen", "slots", "kw_only"]

[annotation-shapes]

[constant-annotations]

[confined-types]
# Binary floating point does not hold a price: a rounding error in stored
# state is money that stops adding up.
"modules/*/domain" = ["float"]
# `int` says the version may be −10000, `str` that the tag may be empty. None
# of that is true of the business, and the type is the last place to say it
# once instead of re-checking by eye.
domain = ["str", "int", "float", "Decimal"]
shared = ["str", "int", "float", "Decimal"]

[config-fields]
zones = ["config"]
# The field names the variable it is read from — and `.env.example` is built
# out of exactly that.
alias = "validation_alias"

[config-fields.bounds]
int = ["ge", "gt", "le", "lt"]
float = ["ge", "gt", "le", "lt"]
str = ["min_length", "pattern"]

# --- The database -----------------------------------------------------------

[model-columns]
zones = ["infra/database/models"]
defaults = [
    "default",
    "insert_default",
    "default_factory",
    "server_default",
    "onupdate",
    "server_onupdate",
]
skip = ["str", "int", "float", "Decimal", "dict", "Any"]
aware = ["DateTime"]

[model-columns.instead]
Enum = "a bare Enum is a native Postgres type; use stored_enum()"
Float = "a Float column drifts; state is exact, use Numeric"
JSONB = "a bare JSONB is a shape nobody declared; wrap it in a TypeDecorator"

[model-columns.wrappers]
# The module where the wrapper over the material lives: naming it there is
# allowed, because that is the one place that turns it into something else.
Enum = "_enum_column"

[bound-checks]
zones = ["infra/database/models"]
primitives = [
    "PositiveDecimal",
    "NonNegativeDecimal",
    "PositiveInt",
    "NonEmptyString",
    "Weight",
]

[raw-sql]

[statement-keys]
zones = ["infra/database/repositories"]

[[confined-calls.rules]]
methods = ["commit", "rollback", "begin", "begin_nested"]
zones = ["modules", "presentation", "infra/database"]
# The broker's edge: a consumer's `commit()` acknowledges an offset, not a
# transaction.
skip = ["presentation/consumers"]
owner = "unit_of_work"
because = "unit_of_work owns the transaction boundary"

# --- Effects ----------------------------------------------------------------

[determinism]
zones = ["modules", "repositories"]

[determinism.instead]
"datetime.now" = "take the Clock port and call it"
"date.today" = "take the Clock port and call it"
"time.monotonic" = "take the Clock port and call it"
"uuid4" = "hand the identifier out of IdGenerator and pass it in"
"uuid7" = "hand the identifier out of IdGenerator and pass it in"
"random.*" = "take the value as an argument"
# The same source through SQL: `func.<name>()` is a call the DATABASE makes.
"func.now" = "the row's time comes from the Clock port, not from the database"
"func.gen_random_uuid" = "the row's identifier comes from whoever built it"

[log-events]
enum = "LogEvent"

# --- Refusals ---------------------------------------------------------------

# A refusal has two halves: the sentence is for a person and may be rewritten,
# the code is what a caller branches on and may not.
[refusals]
zones = ["modules"]
carries = "refusal"
allow = ["NotImplementedError"]
internal = ["InvariantError"]

# --- The edge ---------------------------------------------------------------

# One block per framework, and the block says only what this service demands of
# an entrance. What an entrance IS - the method names, a decorator or a call,
# how the first argument is written - the rule knows: their authors decided it,
# and a table about it here would be a retelling of somebody else's docs.
[edge-declarations.fastapi]
required = ["path", "status_code", "summary", "responses"]

[edge-declarations.faststream]
required = [
    "group_id",
    "parser",
    "decoder",
    "ack_policy",
    "no_reply",
    "auto_offset_reset",
    "isolation_level",
]

[confined-functions]
# Conversion has one implementation, and its call sites can be listed.
declared-in = "shared/money"

[confined-functions.calls]
to_eur = ["modules/pricing/application", "modules/orders/application/use_cases/quote"]
in_cents = ["modules/pricing/application"]

[dependency-bounds]

# --- The mutation gate ------------------------------------------------------

# What gets mutated is mutmut's own table; here is only what the gate needs:
# where the record lives, and the profile the property tests draw under while
# they are mutated — a fresh example every run kills a mutant once and misses
# it the next time, and the record would move on its own.
[mutation]
baseline = "tools/mutation_baseline.json"
env = { HYPOTHESIS_PROFILE = "deterministic" }

# --- What is built rather than checked --------------------------------------

[env-example]
settings = ["parcels.config.settings:Settings"]
```

Read top to bottom, the file says what kind of service this is: three modules
with sealed rules, one transaction boundary, a database whose columns are made
of bounded primitives, an HTTP edge that declares its answers, and a clock
that arrives through a port. That is the whole point of the table being the
project's: the library has no opinion about any of it until this file says so.

## 2. Where the settings live

Everything below is written as `[tool.py-checks.<code>]` sections — that is
the `pyproject.toml` view. The settings also have a file of their own:
`py-checks.toml` or `pychecks.toml`, with or without a leading dot. In that
file there is no prefix — the whole file *is* that section:

```toml
# pychecks.toml
src = "src"

[module-length]
max-lines = 300
```

One of the two is chosen. Both at once is an error rather than a merge: it is
a question without an answer, and it is better asked out loud than settled by
silently reading one and forgetting the other. A `pyproject.toml` with no
section does not count as the second place — every project has one, and a
silent presence is not a choice.

A file of its own also names the project root: the tool works where there is
no `pyproject.toml` at all.

Two settings stand outside the rules, at the top of the file:

```toml
src = "src"                      # where the project's own code is
ignore = ["schema-drift"]        # rules this project does not run
extend-exclude = ["generated"]   # on top of the default exclusions
```

## 3. Who checks what

The rules below exist because nothing off the shelf covers them. Where
something does, it keeps the job — a second opinion costs a second
configuration, and the two drift.

| The convention | Who holds it |
|---|---|
| Function length | rule `function-length`: ruff `PLR0915` counts statements rather than lines, and on four services, at a limit of 50, it does not fire once — where by lines ten functions are over |
| Branches in a function | ruff `PLR0912` |
| Nested `with` | ruff `SIM117`, with an autofix |
| Depth of `try` and `if` | rule `nesting`: ruff has nothing for it — `PLR1702` counts every kind as one number and lives in preview |
| Arguments into an operation | rule `operation-shape`, setting `max-arguments`: `PLR0913` knows neither classes nor the exception for a constructor |
| A list in a column | rule `signature-layout`, with an autofix: the formatter respects a trailing comma but never writes one, and `COM812` fires off a line break that is already there |
| A signature written out in full | rule `keyword-only-arguments`, with an autofix |
| `frozen=True, slots=True` on values | rule `frozen-dataclasses`: ruff has no rule about how a dataclass is declared |
| Bounds on settings fields | rule `config-fields`: neither pydantic nor ruff demands `Field(...)` or a bound |
| `Any` in a signature | ruff `ANN401` — parameters and return only; class fields it does not see |
| A string key, a tuple by position | rule `annotation-shapes` |
| `Final` and `ClassVar` on constants | rule `constant-annotations` |
| A column by string, N+1 in a repository | rule `statement-keys` |
| The material of a column | rule `model-columns` |
| A model past the boundary of the database layer | rule `model-boundary`: ruff sees the import out of the models package; what is then done with that name it does not |
| Models and migrations out of step | rule `schema-drift` on top of `alembic check`: statics cannot see this, it needs a database |
| A migration that rolls back | pytest-alembic `test_up_down_consistency` |
| The clock, the dice, a new identifier | rule `determinism`: `TID251` knows no zones, its per-file relief also lifts the ban on `Literal`, and `func.gen_random_uuid()` inside a statement it does not see at all |
| A naive timestamp | ruff `DTZ` |
| The name of an event in the log | rule `log-events`: nothing off the shelf |
| A complete declaration at an entrance | rule `edge-declarations`: FastAPI and FastStream give the words but demand none of them; Schemathesis checks the schema against the code, not the schema for completeness |
| The call sites of a conversion | rule `confined-functions`: nothing off the shelf |
| A ceiling on a dependency | rule `dependency-bounds`: nothing off the shelf; `deptry` (unused and undeclared) and `uv lock --check` are useful alongside |
| A complete `.env.example` | built by `py-checks sync`, plus `config-fields` with `alias` |
| `AGENTS.md` and `CLAUDE.md` in step | a symlink, plus the `check-symlinks` and `destroyed-symlinks` hooks |
| Surviving mutants | `py-checks mutation` over `mutmut`: the scope is mutmut's, the record is the project's, the three passes are the library's |
| A CHECK under a bounded column | rule `bound-checks` |
| SQL as a string instead of an expression | rule `raw-sql`: `TID251` bans `text()` outright and takes 94 lawful places down with it |
| The transaction boundary | rule `confined-calls`: ruff sees names, but neither zones nor an owner |
| A type banned in a zone | rule `confined-types`: neither ruff nor pyright knows that `Decimal` in the domain is not enough |
| Module length | rule `module-length`: ruff has no rule; in pylint it is `C0302` |
| A magic number, a forgotten `print`, commented-out code | ruff `PLR2004`, `T20`, `ERA` |
| `typing.Literal` instead of `StrEnum` | ruff `TID251`, one `banned-api` line instead of 138 lines of checker |

A separate bandit is then unnecessary: the `S` rules are bandit, rewritten
inside ruff. On the four services it stood next to ruff as a second dependency
and a second hook — the move throws it out.

## 4. The hooks

The library publishes only its own:

```yaml
- repo: https://github.com/Armontex/py-checks
  rev: v0.3.1
  hooks:
    - id: py-checks
      args: [--fix]          # repair what repairs itself
    - id: py-checks-sync
```

One hook rather than one per rule: which rules run is the config's decision,
and the hook list is not obliged to say it a second time. A single rule is
called with `args: [--select, "<code>,<code>"]` — the same arrangement ruff
has.

It has to stand **before** `ruff-format`. The autofix writes characters, not
columns: once a `*` is inserted the signature can pass the line limit, and it
is the project's formatter that lays it out. The library calls `ruff` itself
if it finds one on PATH, but in the hook's own isolated environment there is
none — there the file is left repaired but unformatted, and the next hook in
the same run fixes that.

The rest the project declares itself — ruff, pyright, import-linter,
commitizen. Each has a hook written by its own authors, and they know more
about themselves than we would. Building their config for them is another
matter: `.importlinter` falls behind the layout on disk, so `py-checks sync`
builds it and import-linter's own hook walks the graph:

```yaml
- repo: https://github.com/seddonym/import-linter
  rev: v2.5
  hooks:
    - id: import-linter
```

For the same reason import-linter is not a dependency of the library: we never
import it, and handing a third-party tool to everyone who installed us would
be deciding, on the project's behalf, what checks its imports.

### `doctor` — the config judged instead of the code

A rule with no table says nothing, and that silence looks exactly like a
convention nobody breaks. `py-checks doctor` is the command that reads the
config itself and says where the quiet comes from:

```
$ py-checks doctor
py-checks.toml

  typo in a section name
    [class-lenght] — no such section; closest: module-length, function-length

  rule is on but silent
    [statement-keys] — no zones named: nowhere to judge
    [layout] — the section is empty and the rule has no defaults

  address that is not on disk
    [layout] — 'application/handlers' not found in src

complaint(s): 3
```

Four questions, all of them about the file rather than the tree: a section
name nobody reads (a typo is silently ignored otherwise — nothing looks for a
section nobody declared), `ignore` naming a rule that does not exist, a rule
whose table leaves it with nothing to judge, and an address no directory or
module answers to. The last one is the slow one: a directory gets renamed, the
block stays, and the rule goes on looking where nothing is.

It belongs in CI beside `run`, not in the hooks: it reads the whole tree of
`src` to answer the last question, and it has nothing to say about the file
that is being committed. It exits `1` when it has complaints.

### `mutation` — the tests judged instead of the code

A surviving mutant is a line that was changed while every test still passed.
`py-checks mutation` runs `mutmut` and refuses a push that leaves more of them
in a module than that module's record allows:

```bash
py-checks mutation diff     # the modules this branch touched — what a push runs
py-checks mutation full     # everything mutmut mutates, module by module
py-checks mutation record   # a full pass, written down as the new record
```

Each pass also says what it tried and how that ended — for information, not as
a verdict. `killed` is what mutmut itself counts as killed: a failed test, a
timeout, a mutant the type checker refused. `left` is the survivors the
gate judges. Anything else — `suspicious`, a segfault — is shown apart rather
than folded into either:

```
$ py-checks mutation full
mutants: run 2643, killed 2630, left 13
ok: 13 survivor(s), as recorded
```

It is an extra rather than part of the core: `pip install
"python-checks[mutation]"`. The library never imports mutmut — it calls it as
a process, the way `schema-drift` calls alembic — but it reads what mutmut
prints, and that format is the contract between the two. The extra pins the
major in which the format holds: a parser that missed every `survived` line
would count zero and pass everything.

It belongs on push rather than in CI: the report is for whoever is about to
push the tests it judges, and a CI runner is the weakest machine there is to
spend minutes of mutation on.

```yaml
- repo: local
  hooks:
    - id: mutation-gate
      name: no new mutant survives the unit tests
      entry: nice -n 19 uv run py-checks mutation diff
      language: system
      pass_filenames: false
      always_run: true
      stages: [pre-push]
```

| Key | Default | |
|---|---|---|
| `command` | `["mutmut"]` | how mutmut is called |
| `baseline` | `"mutation-baseline.json"` | where `record` writes the survivors per module |
| `against` | `["origin/develop", "develop"]` | what a branch is compared to when the push does not say |
| `children` | mutmut decides | how many mutants run at once; `--children` overrides it |
| `env` | `{}` | variables for the run |

What gets mutated is not in this table. It is `source_paths` and
`do_not_mutate` of mutmut itself, read from wherever mutmut reads them —
`[tool.mutmut]` if `pyproject.toml` has one, `[mutmut]` of `setup.cfg`
otherwise. Stating the scope twice is how the two would come apart. A project
that states it nowhere is refused: a gate that does not know what is mutated
would judge nothing and pass everything.

**Why module by module.** The record is a map, not a number, and `full` judges
it module by module just as `diff` does. A total stays put when one module
gains a survivor and another loses one — and the new hole goes through under
cover of somebody else's work.

**Why the survivors are run again.** mutmut's cache is keyed on the mutated
source, so a mutant that a test written today kills stays on record as alive:
nothing about its file changed. `diff` names the modules it judges and `full`
names the survivors the cache believes in, and naming is what makes mutmut run
them again. Two verdicts count, `survived` and `no tests`; the second is the
stronger, since a module with no test at all would otherwise score zero. A
`not checked` is a refusal: mutmut exits `1` when its test collection fails,
and by the exit code alone that run looks like one that left survivors.

**Instead of `tools/check_mutation_gate.py`.** Three services carried it, in
three versions of 514, 600 and 700 lines, and the fix for `not checked` had
reached two of them.

## 5. The rules

Nine groups. Each group has a short word that lifts any rule in it from a
line — `# import-ok`, `# placement-ok`, `# signature-ok`, `# type-ok`,
`# db-ok`, `# effect-ok`, `# api-ok`, `# call-ok`, `# hygiene-ok` — and the
canonical `# check-ok: <code>: <reason>` always works and lifts exactly one.

### 5.1 imports — which package is allowed where

#### `confined-imports` — a package is imported outside the places set aside for it

```toml
[tool.py-checks.confined-imports]
sqlalchemy = ["infra/database", "ioc"]
asyncpg = ["infra/database", "ioc"]
aiosqlite = ["infra/database"]
alembic = ["infra/database"]
fastapi = ["presentation", "bootstrap"]
starlette = ["presentation", "bootstrap"]
starlette_exporter = ["bootstrap"]
dishka = ["ioc", "bootstrap", "presentation"]
uvicorn = ["entrypoints"]
typer = ["entrypoints"]
sentry_sdk = ["observability"]
prometheus_client = ["observability", "bootstrap", "infra"]
opentelemetry = ["observability", "bootstrap", "infra"]
```

**Why.** A framework spreads by import. The day the ORM is imported in a use
case, the use case can no longer be read without a database, and the layer
diagram becomes a drawing rather than a fact. The table says where each
framework is allowed to be seen; everything not in the table is unrestricted.

An empty list means "nowhere" — that is how a library that was taken out is
kept out: `agents = []`.

**Where the services differed.** Each added its own line: `maxapi =
["presentation", "bootstrap/channels", "ioc"]` in A, `aiokafka =
["infra/kafka", "ioc"]` in D, `shared_contracts` in C and D.

**The mark.** `# import-ok: confined-imports: <reason>`.

#### `sealed-imports` — a sealed zone imports a foreign package

```toml
[tool.py-checks.sealed-imports]
# `modules` holds the rules and the interfaces around them: a DTO here is a
# dataclass, not a framework's model. `shared` is sealed by A and C: every
# module's domain imports it, so a framework that reaches it is inside every
# sealed layer at once.
zones = ["modules", "shared"]

[tool.py-checks.sealed-imports.allow]
# A use case leads and may therefore say what happened; the rules are true
# whether or not anybody is listening.
application = ["structlog"]
```

**Why.** `confined-imports` names a package and says where it may go. This is
the other direction: a zone is named, and nothing third-party may enter it
except by the allow list. The two are needed together because the first only
knows the packages somebody remembered to write down, and the sealed zone is
exactly the place where the next forgotten one would do the damage.

**Where the services differed.** B keeps an address validator in `shared`, so
only `modules` is sealed there.

**The mark.** `# import-ok: sealed-imports: <reason>`.

### 5.2 placement — what belongs where

Five rules speak about one and the same thing from five sides: what may live
here, what lives *only* here, what a module must declare, what shape an
operation has, and which end of the ORM model's boundary this directory is.
They read one table — `[layout]`, one block per directory:

```toml
[layout."application/use_cases"]
only = ["class"]        # nothing but classes is declared here
suffix = "UseCase"      # they are named *UseCase — and *UseCase lives nowhere else
required = true         # a module here must declare one, first and alone
operation = { method = "execute", max-arguments = 3 }
```

| Key | Read by | Says |
|---|---|---|
| `only` | `class-modules` | the kinds allowed in this directory, and nothing else sits beside them |
| `home` | `class-placement` | the kinds whose only home this is |
| `area` | `class-placement` | the part of the tree where the claim applies at all |
| `suffix` | `class-placement`, `required-class`, `operation-shape` | the name of the class this directory exists for |
| `required` | `required-class` | a module here must declare such a class, first and alone |
| `operation` | `operation-shape` | the shape of the operation kept here |
| `orm` | `model-boundary` | which end of the model's boundary this is: `"declared"` or `"built"` |
| `base` | `model-boundary` | the base class the models here are known by |

The heading is an address, not a directory name, and it is matched as
consecutive pieces of a path: `application/use_cases` is found inside
`modules/<name>/` as well, and a `*` matches any one piece
(`modules/*/domain`). A directory the layout says nothing about is nobody's
business.

**A home claimed is a home enumerated.** The moment a kind gets a `home`, it
lives *only* in the blocks that claim it — so every legitimate home is on the
list:

```toml
[layout."application/dto"]
home = ["dataclass"]

# A domain value object is a dataclass too, and this is where it lives.
[layout."modules/*/domain"]
home = ["dataclass"]
```

That is the point of the table rather than a chore: the file answers "where do
dataclasses live in this service" by itself, instead of the reader inferring it
from the absence of a rule.

#### `class-modules` — a module holds what its directory does not allow

Reads `only`.

**Why.** A directory is a promise about what is inside it. A port declared
next to a use case is a port nobody will find, and a dataclass in `ports/` is
an interface that quietly grew a field.

The key is a path, not a name: `application/services` holds an orchestrating
class, while `domain/services` holds functions — rules that compare two facts.
A rule by name would have banned the whole domain category.

The kinds are `class`, `port` (Protocol, ABC), `dataclass`, `model`
(pydantic), `alias`, `enum`, `error`, `function`. Imports, constants,
`if TYPE_CHECKING` and the docstring are allowed everywhere.

An error is recognised both by the base `Exception` and by the name of the
base: `class NotFound(OrderError)` inherits from its own root rather than from
`Exception`, but the root's name ends the same way. So a package's whole
vocabulary of refusals gathers in `errors/` or `exceptions.py`, and the reader
finds it in one place.

**The mark.** `# placement-ok: class-modules: <reason>`.

#### `class-placement` — a class lies somewhere other than where its kind lives

Reads `home` and `suffix`.

**Why.** The directory names the kind, and the reader finds the port without
opening a file. A `dataclass` in `application` must be in `dto/` — and a
domain value object is a dataclass as well, which is why the domain is on the
list of its homes rather than exempt from the rule.

Several addresses for one subject read as equals: a repository port and its
implementation lawfully live in two places, and the refusal vocabulary lives
in `errors/` or in `exceptions.py`.

**The mark.** `# placement-ok: class-placement: <reason>`.

#### `required-class` — a module did not declare the class its directory exists for

Reads `required` beside `suffix`.

**Why.** A file in `use_cases` exists for a use case; a file in `repositories`
exists for a repository. The class comes first and comes alone: the file name
is how a reader finds the class, and a module named after none of the three
use cases inside it answers the question "where is `ResolveLimitsUseCase`"
with "read all three".

Above the required class, constants, aliases and enums are allowed. The enum
is not a concession but a necessity: a class body executes at declaration
time, and a vocabulary the class names inside itself cannot be written below
it.

The rule leaves `__init__.py` alone (re-export, not declaration), as well as
an empty module and a module with a leading underscore: `_base.py` holds its
directory's machinery rather than one of its classes. The underscore is the
only form of that relief; there is no list of bare names.

When several blocks match, the innermost wins, and at equal depth the longer
address: `application/services` requires a class while `domain/services`
requires nothing.

**The mark.** `# placement-ok: required-class: <reason>`.

#### `operation-shape` — an operation is not shaped like an operation

Reads `operation` beside `suffix`.

```toml
operation = { method = "execute", max-arguments = 3, forbids = ["UnitOfWork"] }
```

**Why.** A use case is asked for one thing: one public method, and it is
called `execute`. A second public method is a second operation sharing a
constructor with the first, and a caller who needs one drags in the
dependencies of both. Private methods are unlimited: a long operation broken
into `_begun`, `_judged` and `_risked` is still one operation.

An empty `method` means the number of doors is not limited: a module's service
has as many as its entity has transitions, and that is the same decision
rather than a concession.

The door takes three fields, no more. What came from outside and filled four
is a thing with a name: a command, a query, a DTO. Public methods are counted,
so the constructor is out of the count by construction: dependencies arrive
through it, and that is wiring, not an entrance. The first argument of a
method is decided by position rather than by name — `self` in a `@staticmethod`
counts like any other.

Nothing stands next to the operation: no second class, no function, neither
above nor below. Constants and aliases may; an enum may not, unlike in other
directories — a vocabulary is a class, and an operation that needed one is
naming something its module does not own.

`forbids` matches a type name by substring, so `UnitOfWork`, `IAuthUnitOfWork`
and `AuthUnitOfWorkFactory` are refused alike — what is forbidden is holding
the transaction, not spelling its name one particular way.

**Instead of `PLR0913`.** It knows neither classes nor the exception for a
constructor. At `max-args = 3` it gives 29, 142, 96 and 108 hits across the
services, and inside `use_cases` alone 49 — every one of them on `__init__`.

**Where the services differed.** Who the ban belongs to is the project's line:
in A the use case opens the transaction and hands the service its
repositories, while in B, C and D the use case holds the factory itself —
there the ban is on services only.

**The mark.** `# placement-ok: operation-shape: <reason>`.

### 5.3 signatures — length, depth, the shape of a call

#### `keyword-only-arguments` — a signature is not written out in full

```toml
# no table: the rule is on for the whole tree
```

**Why.** A positional argument is a promise about order that the call site
has to remember. Named arguments make a call read like the sentence it is,
and a parameter added in the middle stops being able to break a caller
silently. The autofix writes the `*`; the formatter lays the signature out.

Library callbacks are the exception that needs a name rather than a setting:
a framework calls `process_bind_param(self, value, dialect)` and the signature
is not ours to change. Those lines carry a mark.

**The mark.** `# signature-ok: keyword-only-arguments: <reason>` — anywhere in
the signature, including the closing line of a signature written in a column.

#### `signature-layout` — a list of two or more entries is written on one line

```toml
[tool.py-checks.signature-layout]
# The half about calls is switched off for the duration of a move: in a
# service written without it, it touches nearly every file — 693 places in B,
# 860 in D.
calls = true
```

**Why.** A list of two or more entries is written one per line — in the
signature and at the call site. In a column, editing one argument touches one
line and says exactly that; the same list on one line shifts everything after
the edit, and review reads the whole of it to find the change.

At a call site the rule fires on two or more **named** arguments, and that is
the entire border between our code and other people's: every function of ours
is keyword-only, so a call of ours is all names, while `isinstance(node,
ast.Call)` and `range(1, 10)` are somebody else's positional signature and are
left alone. Once it fires, it unfolds every argument, positional ones
included.

A decorator is the single exception: `@dataclass(frozen=True, slots=True)` is
a label, not a list read for meaning.

**Instead of `ruff format`.** The formatter keeps a list in a column when the
trailing comma is there (the magic trailing comma), but it never writes one.
So `--fix` writes the comma and calls the formatter — the layout from there
on is the formatter's.

**The mark.** `# signature-ok: signature-layout: <reason>`.

#### `function-length` — a function is longer than the limit

```toml
[tool.py-checks.function-length]
max-lines = 50
```

**Why.** The body is counted, not the signature: a function whose parameters
stand in a column is not thereby longer. Fifty lines is where a function stops
fitting on a screen and starts being held in the head.

**Instead of `PLR0915`.** It counts statements rather than lines, and on four
services, at a limit of 50, it does not fire once — where by lines ten
functions are over.

**The mark.** `# signature-ok: function-length: <reason>`.

#### `module-length` — a module is longer than the limit

```toml
[tool.py-checks.module-length]
max-lines = 600
```

**Why.** Lines are counted as written, blank ones and comments included: the
reader has to hold all of them. Ruff has no rule for this; in pylint it is
`C0302`.

**The mark.** `# signature-ok: module-length: <reason>`.

#### `nesting` — control structures are nested deeper than the limit

```toml
# `with` is deliberately absent from the table: a nested `with` is caught by
# ruff `SIM117`, with an autofix and a ready answer — "make it one `with a, b:`".
[tool.py-checks.nesting]
try = 1
if = 2
```

**Why.** Depth is where logic stops being read and starts being decoded. Each
kind has its own limit because they cost different things: a second `try`
inside the first hides which line threw, while a second level of `if` is an
ordinary fork and the third is the one too many. An `elif` is a branch, not a
level; an `else:` written out with an `if` inside is a level — that is the
extra indent.

**Instead of `PLR1702`.** First, it is preview-only: without `--preview` ruff
silently does not run it and reports everything clean. Second, it counts total
depth as one number for every kind at once — at a limit of 3 it lets a `try`
inside a `try` through, and at 1 it takes down the lawful `for`/`try`/`with`/`if`
chain that D actually has.

**The mark.** `# signature-ok: nesting: <reason>`.

### 5.4 types — bounds, shapes, immutability

#### `annotation-shapes` — a shape is named such that its fields have no names

```toml
[tool.py-checks.annotation-shapes]
# keys default to ["str"], tuples default to true
```

**Why.** A dict with a string key reads as a set of named fields — and which
ones, a `TypedDict` or a dataclass will say. A fixed-length tuple names its
fields by position: `row[2]` says nothing and survives a reordering in
silence.

A genuine bag of keys — HTTP headers, a trace-context carrier — is marked.

**Where the services differed.** In A and C all 5 and 34 places where the rule
fires are marked exactly so.

**The mark.** `# type-ok: annotation-shapes: headers, not fields`.

#### `constant-annotations` — a constant did not say by its type that it is one

```toml
[tool.py-checks.constant-annotations]
# module defaults to "Final", inside-class to "ClassVar"
```

**Why.** An `UPPER_SNAKE` name is a promise; `Final` makes it checkable.
Without it the name reads as a constant and behaves as a variable, and anyone
who imported the module is free to rebind it.

Inside a class body the word is a different one: `Final` there means the
attribute cannot be overridden at all (PEP 591), and bounded primitives are
built on exactly that overriding — `PositiveDecimal.BOUND` replaces the base's
`BOUND`. `ClassVar` says "belongs to the class" and leaves overriding open.
Enums are left alone: a member is a vocabulary.

`Any` in an annotation is not part of this: ruff `ANN401` catches it, though
only in parameters and returns — a class field and a variable it does not see.

**The mark.** `# type-ok: constant-annotations: <reason>`.

#### `confined-types` — a field in this part of the tree is declared with a type banned here

```toml
[tool.py-checks.confined-types]
# Binary floating point does not hold a price, and a rounding error in stored
# state is money that stops adding up. In the application a number on its way
# to a report is arithmetic, and `float` is lawful there.
"modules/*/domain" = ["float"]

# `int` says the version may be −10000, `str` that the tag may be empty,
# `Decimal` that the coefficient may be negative or NaN. None of that is true
# of the business, and the type is the last place where it can be said once
# instead of re-checked by eye.
domain = ["str", "int", "float", "Decimal"]
shared = ["str", "int", "float", "Decimal"]
```

**Why.** A zone is a path, and a `*` in it matches any one piece. Zones add
up: a file in `modules/pricing/domain` falls under both lines at once.

A zone is made of directories. `domain` takes `domain/` and everything under
it, but not `application/exceptions/domain.py`: a module that happens to share
a layer's name is not that layer. The file's own name answers only to `*`, so
`domain/*` still takes `domain/exceptions.py`. The same holds for every
`zones` key and for `sealed-imports`.

Class fields are judged; `ClassVar` and `Final` are not fields — they belong
to the class rather than to an instance, cross no boundary and are not the
rule's business. An annotation is seen through: `tuple[str, ...]` is the same
bare string one floor down.

`shared` is in the table on purpose: the read contracts live there. Without
it the writing side of a projection refuses a NaN and the reading side hands
it back.

**Where the services differed.** The width of a zone is the project's call: in
D the rule is named by `entity`, `entities`, `value_objects`, and
`domain/services` was left out — four `Decimal` fields there are declared
bare.

**The mark.** `# type-ok: confined-types: <reason>`.

#### `config-fields` — a settings field carries no bound

```toml
[tool.py-checks.config-fields]
zones = ["config"]
# factory defaults to "Field"
# alias = "validation_alias" — see §6, the `.env.example` builder needs it

[tool.py-checks.config-fields.bounds]
int = ["ge", "gt", "le", "lt"]
float = ["ge", "gt", "le", "lt"]
str = ["min_length", "pattern"]
```

**Why.** The value arrives as text from an environment nobody reviews, so both
halves of the declaration are compulsory.

A field is declared through `Field(...)`: that is where the variable's alias,
the default and the bounds live, and a bare `name: str = "x"` silently drops
all three.

A field with a bare number names its bound, otherwise `POSTGRES_POOL_SIZE=0`
and a pool of five hundred are both accepted here and fail somewhere the
settings are no longer visible in the traceback. A bare string is the same
hole with a quieter failure: an unset variable arrives as an empty string, and
an empty broker address or topic name is accepted as configuration.
`max_length` does not count as a bound: a ceiling says how long a value may
be, not that there is one.

An annotation is already a rule when it carries the bound itself:
`Port = Annotated[int, Field(ge=1, le=65535)]`, and a field of that type owes
nothing. A `ClassVar` is a constant next to the fields, not a field.

**Where the services differed.** The `str` line is the newest part of the
rule: A and C hold to it, B has 4 fields without it, D has 12. A project
moving gradually takes `str` out of the table and puts it back when it is
fixed.

**The mark.** `# type-ok: config-fields: <reason>`.

#### `frozen-dataclasses` — a dataclass in a zone is declared without the required arguments

```toml
[tool.py-checks.frozen-dataclasses]
zones = ["modules"]
# options default to ["frozen", "slots", "kw_only"]
```

**Why.** A thing of the business is a value: assembled once and not changed,
so an existing object cannot quietly slide into a state that is not allowed.
`frozen` buys that, `slots` keeps a typo from inventing an attribute nobody
declared, and `kw_only` keeps two fields of the same type from swapping
places — in a value of four strings only the author remembers the order.

The zone is the same as for sealed imports, and for the same reason: keeping
values immutable makes sense where the rules live, not in a config assembled
from the environment and not in the wiring.

**Where the services differed.** A, B and D declare every value inside
`modules` this way; C has 120 without `kw_only`.

**Instead of ruff.** There is no such rule: `RUF008`, `RUF009`, `RUF045` and
`RUF049` speak about a dataclass's contents, none about how it is declared.

**The mark.** `# type-ok: frozen-dataclasses: <reason>`.

### 5.5 database — the model, the column, the statement

#### `model-boundary` — an ORM model is declared, built or handed out in the wrong place

```toml
[tool.py-checks.layout."infra/database/models"]
orm = "declared"
# base defaults to "Base"

[tool.py-checks.layout."infra/database/repositories"]
orm = "built"
```

**Why.** A model is a description of a table, and three rules keep it one.

*Declared* in the models package. Alembic's `autogenerate` sees exactly the
models the imports of that package reach: a table declared off to the side
does not make it into a migration, and the disagreement surfaces not here but
on the first write to a database that has no such table.

*Built* only in repositories. To build a model is to write a row, and a row is
written by whoever holds the session. A model built in a use case either does
nothing — there is nowhere to add it — or it is a write performed by a layer
with no transaction to finish it.

*Not returned* by a repository's public method. A model carries the session
with it: touching an attribute after the transaction closed either fails or
goes to the database from a layer that may not, and half the schema is
reachable from there by relationships — a query leaving code that never asked
for a connection. Repositories return DTOs, identifiers, counts — everything
the database layer has finished with.

A model is recognised in two ways, both visible in one file: declaration by
the `Base` parent, use by the import from the models package. It is not looked
for by name: `SettingsModel` in the settings, `DeviceModel` in the domain and
`ChooseModel` in a dialogue are not tables, and their suffix is the same.

The first of the three rules partly repeats `class-placement`: that one judges
by a name's suffix and says where a `*Model` class belongs; this one judges by
the base and says a class with `Base` among its parents exists nowhere but in
the models package.

**The mark.** `# db-ok: model-boundary: <reason>`.

#### `model-columns` — a column is built out of the wrong material

```toml
[tool.py-checks.model-columns]
zones = ["infra/database/models"]
defaults = [
    "default",
    "insert_default",
    "default_factory",
    "server_default",
    "onupdate",
    "server_onupdate",
]
skip = ["str", "int", "float", "Decimal", "dict", "Any"]
aware = ["DateTime"]

[tool.py-checks.model-columns.instead]
Enum = "a bare Enum is a native Postgres type; use stored_enum()"
Float = "a Float column drifts; state is exact, use Numeric"
JSONB = "a bare JSONB is a shape nobody declared; wrap it in a TypeDecorator"
JSON = "a bare JSON is a shape nobody declared; wrap it in a TypeDecorator"

[tool.py-checks.model-columns.wrappers]
# The module where the wrapper over the material lives: naming it there is
# allowed. In A and C that is `_enum_column`, in B and D `enum_column`.
Enum = "_enum_column"
```

**Why.** A native Postgres enum needs an `ALTER TYPE` for every new member,
and these vocabularies belong to somebody else and will grow. `Float` does
not hold a price exactly, and a column is state: the rounding error
accumulates with every write. A bare `JSONB` is a shape nobody declared —
what the writer put in is what every reader gets, and the parsing that would
have caught a missing key happens in each of them separately or nowhere.

A default is a value nobody wrote: the writer skipped the column, the row got
a number anyway, and an omission that a type checker would have caught on a
missing constructor argument turns into a plausible row. `onupdate` is the
worst of them — a second clock next to the one passed in as an argument so
that a test and a retry see the same stamp.

A `DateTime` without `timezone=True` stores a naive stamp: the writer's wall
clock, unsigned, compared as though the signature did not matter. The
annotation and `nullable=` must agree: SQLAlchemy lets them diverge, and then
pyright reasons by one while the database holds the other.

`UUID`, `datetime`, `date` and `bool` are deliberately absent from `skip`:
they are exhaustive in themselves, and there is no subset of `bool`.

**The mark.** `# db-ok: model-columns: <reason>`.

#### `bound-checks` — a bounded column did not restate its bound as a CHECK

```toml
[tool.py-checks.bound-checks]
zones = ["infra/database/models"]
primitives = [
    "PositiveDecimal",
    "NonNegativeDecimal",
    "PositiveInt",
    "NonNegativeInt",
    "NonEmptyString",
    "MarginFraction",
    "FiniteDecimal",
    "OfferedPrice",
]
# helper defaults to { call = "bound_check", column = "column", primitive = "primitive" }
```

**Why.** A column declared `Mapped[PositiveDecimal]` promises twice. pyright
holds every row **built here** to values the type let through;
`bound_check(column=..., primitive=PositiveDecimal)` in `__table_args__` holds
every row written any other way — a backfill, a psql session, a second
service next year. An annotation without a CHECK is a database trusting code
it has never seen.

Presence is checked rather than equivalence, and that is why it can be
trusted: the SQL is generated from the same `BOUND` the type refuses by, so
there is no second expression to compare against — there is a call somebody
may have forgotten. Separately refused is a `primitive=` naming a type other
than the one in the annotation: that is the only way to smuggle the
disagreement back in.

The list of types is the project's and is written as words: the rule does not
import the code it checks. A name written before the type exists costs
nothing — the rule fires on the annotation, and there is none until the
primitive is written.

**The mark.** `# db-ok: bound-checks: <reason>`.

#### `raw-sql` — SQL is written as a string where an expression would do

```toml
[tool.py-checks.raw-sql]
# calls default to CheckConstraint, text, literal_column, column
```

**Why.** A CHECK written as `"margin >= 0 AND margin < 1"` is a second
definition of a rule the domain has already stated, in a language nobody in
the repository checks. Rename the column and the string still compiles; move
the bound and the string still names the old number, and the disagreement
surfaces as a constraint violation on a row that was correct by every rule the
code knew.

Written as an expression — `CheckConstraint(and_(margin >= NOTHING, margin <
WHOLE))` — it is made of an attribute pyright already checks and of the
constants the entity refuses by.

Where there honestly is no expression, the reason goes on the line. Across the
four services there are twelve such places: liveness probes, SQLite's `PRAGMA`
and `column("fixture_id", Uuid)` where the requested pairs are in no table at
all.

Migrations keep their SQL in words on purpose — they are history, and they may
have no right to import the constants they would need. The project's
`extend-exclude` excludes them, not the rule.

**Instead of `TID251` on `sqlalchemy.text`.** Across the four services it
gives 94 hits, 52 of them in `migrations/versions` alone.

**The mark.** `# db-ok: raw-sql: a PRAGMA is not a query`.

#### `statement-keys` — a statement names a column by string, or goes to the database in a loop

```toml
[tool.py-checks.statement-keys]
zones = ["infra/database/repositories"]
# lists default to ["index_elements"], mappings to ["set_"],
# sub-queries to ["from_select"], loops to ["execute"]
```

**Why.** Rows are assembled through models, so pyright holds the column list:
a missing column is a missing argument, a renamed one an unexpected keyword.
A string key opens the hole again: it matches nothing at check time.

`index_elements` and `set_` together are `ON CONFLICT DO UPDATE` — that is the
inbox and every upsert. A string that has stopped matching there raises
nothing: the conflict is simply not found, the duplicate is inserted a second
time, and idempotency — the whole reason the inbox exists — quietly ends.

An `execute(...)` inside a loop is a trip to the database per iteration. A
hundred bets is a hundred round trips where one statement would have done.
Sometimes the loop is honest, and then the reason goes on the line of the loop
or the call. Liftable rather than advisory, deliberately: a warning that
brings nothing down is read once, while a mark is written by somebody who had
a reason, and it stays in the file for the next reader.

**The mark.** `# db-ok: statement-keys: a bet has no more than twenty legs, and every one of them moved`.

#### `confined-calls` — a named method was called somewhere it does not belong

```toml
[[tool.py-checks.confined-calls.rules]]
methods = ["commit", "rollback", "begin", "begin_nested"]
zones = ["modules", "presentation", "infra/database"]
# The broker's edge: a consumer's `commit()` acknowledges an offset, not a
# transaction.
skip = ["presentation/consumers"]
owner = "unit_of_work"
because = "unit_of_work owns the transaction boundary"
```

**Why.** A bet is one transaction: take the money, write the bet, write the
event that tells the rest of the platform. A repository committing halfway
turns it into three, and the balance stops agreeing with the bets. `begin` is
banned next to `commit` and `rollback` for the same reason from the other end:
the caller has already opened a transaction, and a second one inside either
fails or quietly nests.

From a single file only the method's name is visible — whose object it is
would take type inference to say. Hence both frames: the zone where a
`commit()` can only be the session's, and `outside` for the edge where the
word is taken by somebody else's meaning.

**Where the services differed.** A and C judge all four names; B and D only
`commit` and `rollback`, because `begin` is taken there by a domain repository
(`progress.begin(enrollment=...)`).

**The mark.** `# db-ok: confined-calls: <reason>`.

#### `schema-drift` — the models and the migrations describe different schemas

```toml
[tool.py-checks.schema-drift]
# versions defaults to "migrations/versions",
# models to "src/*/infra/database/models", variable to "DATABASE_URL",
# url to "sqlite+aiosqlite:///{path}", alembic to ["alembic"]
```

**Why.** A column added to a model with no migration behind it is a service
that works on every developer's machine and fails on the first deployment. Or,
worse, does not fail: SQLAlchemy asks for a column the table has not got, and
the error arrives as a query at three in the morning rather than as a release
that refused to go out.

None of the file-reading rules can see this: `model-columns` and
`bound-checks` judge the model, the migration has rules of its own, and the
**disagreement** between the halves is what alembic's `check` is for. So the
rule needs a live database and is declared `scope = ENVIRONMENT`: an ordinary
run leaves it out, and it is called by name or with everything:

```bash
py-checks run --select schema-drift
py-checks run --all
```

It brings its own database — an empty file in a temporary directory, migrated
from nothing to `head` and deleted afterwards. Not the developer's database:
that one stands at whatever revision its owner last ran, which is exactly the
state the check does not trust.

Hence its place: not in pre-commit, where every commit would pay for running
every migration, but as a CI step — next to the tests, where a database
already exists.

**Three caveats you meet at once.**

- The project's `env.py` must read the database address from the variable
  (`variable`). Where it takes it from its own settings, the rule cannot slip
  a database underneath — there a CI step raises a throwaway Postgres and
  passes it under the same name.
- The default SQLite needs `aiosqlite` in the environment. A project that does
  not keep one is better off pointing `url` at the same throwaway Postgres the
  tests use.
- `alembic` is called by the same name as in the caller's environment: the run
  is already inside the project's environment, and a second `uv run` inside it
  would rebuild that environment mid-check.

**The mark.** `# db-ok: schema-drift: <reason>`.

### 5.6 effects — the clock, the dice, the log

#### `determinism` — the code reads the clock, the dice or a new identifier itself

```toml
[tool.py-checks.determinism]
zones = ["modules", "repositories"]

[tool.py-checks.determinism.instead]
"datetime.now" = "take the Clock port and call it"
"datetime.utcnow" = "take the Clock port and call it"
"date.today" = "take the Clock port and call it"
"time.monotonic" = "take the Clock port and call it"
"time.perf_counter" = "take the Clock port and call it"
"uuid4" = "hand the identifier out of IdGenerator and pass it in"
"uuid7" = "hand the identifier out of IdGenerator and pass it in"
"random.*" = "take the value as an argument"
# Names rather than the whole module: `secrets.compare_digest` is
# deterministic and is needed exactly where tokens are compared.
"secrets.token_urlsafe" = "take the value as an argument"
"secrets.token_hex" = "take the value as an argument"
"secrets.randbelow" = "take the value as an argument"
# The same source through SQL: `func.<name>()` is a call the DATABASE makes
# while it runs the statement.
"func.now" = "the row's time comes from the Clock port, not from the database"
"func.gen_random_uuid" = "the row's identifier comes from whoever built it"
```

**Why.** `datetime.now()`, `uuid4()` and `random.random()` make a use case
untestable: the same input gives a different output, and the test either
freezes the world with a mock or asserts nothing at all. Business code takes
them as a dependency:

```python
async def handle(self, *, command: PlaceBet) -> BetId:
    placed_at = self._clock.now()  # a port, injected
    bet_id = command.bet_id  # handed out at the edge
```

A call through a port the rule leaves alone — it judges global sources. A name
is matched against the tail: `datetime.now` matches `datetime.datetime.now`
too, and `random.*` matches any call into that module.

Repositories are inside the same zone, and there the source is written in SQL.
A `gen_random_uuid()` inside an INSERT is the same decision one floor down,
where it is even harder to see: a test has nothing to assert about it, the
storage layer becomes the author of an identifier nobody passed it, and a
uuid4 appears among uuid7s — random where everything else is ordered, and
ordering is the whole reason an index on them is worth anything.

**Instead of `TID251`.** It covers half and costs more than it looks. It bans
a name across the whole tree, and relief is written as paths in
`per-file-ignores` — which lifts `TID251` in that file **entirely**, together
with the ban on `typing.Literal` handed to the same rule. Measured across the
four services: 27 hits, every one of them lawful — `shared/clock.py`,
`shared/ids.py`, `infra/auth/secrets.py` and `time.monotonic()` in
`presentation`, where a duration is measured for a metric. Exactly the places
the zone leaves alone.

Ruff's `DTZ` group above stands alongside rather than instead: a naive
timestamp is a different mistake, and across the four services it currently
does not occur once.

**The mark.** `# effect-ok: determinism: <reason>`.

#### `log-events` — an event in the log is named by something other than an enum member

```toml
[tool.py-checks.log-events]
enum = "LogEvent"
# levels default to debug, info, warning, warn, error, exception, critical
# receiver defaults to "(^|_)log(ger)?$" — `logger`, `log`, `self._logger`
```

**Why.** An event's name is not read by a human: a processor in the structlog
chain turns `consumer.message.handled` into a counter, and an alert joins on
that string. A literal written at the call site has no definition, and the
code that emits the name is tied to nothing that catches it: a typo breaks no
test, it simply stops matching, and the metric quietly reads zero.

```python
logger.info("consumer started", topics=topics)  # refused
logger.info(LogEvent.CONSUMER_STARTED, topics=...)  # required
```

The rule reads the **shape** `LogEvent.SOMETHING` and does not look for the
member: a name that is not in the enum is refused by pyright, and without
pyright it is an `AttributeError` on the first run — collecting the members
would mean catching what is already caught.

A third-party logger — a library's, or one whose vocabulary another project
owns — is lifted by a mark. Across the four services there are no such places:
330 calls, all through `LogEvent`.

**Instead of the rule.** Types close this as well — a wrapper over structlog
declaring `event: LogEvent`: a literal is then refused by pyright, because
`str` does not fit `LogEvent`, even though `LogEvent` is a `StrEnum`. The
price is a logger class of your own in every service and `**kwargs` passed
through, and third-party loggers inside the service are still called directly.

**The mark.** `# effect-ok: log-events: not our logger`.

### 5.7 api — what an entrance declares

#### `edge-declarations` — an entrance did not say how it behaves

```toml
[tool.py-checks.edge-declarations.fastapi]
required = ["path", "status_code", "summary", "responses"]

[tool.py-checks.edge-declarations.faststream]
required = [
    "group_id",
    "parser",
    "decoder",
    "ack_policy",
    "no_reply",
    "auto_offset_reset",
    "isolation_level",
]
```

One block per framework, and the block names one thing: what this service
demands. Everything else about an entrance was decided by whoever wrote the
framework — `router.post` is a decorator and its path is written as `path=`,
`broker.subscriber` is as often an ordinary call and its topic is written
first and without a name — and a table repeating that here would be a retelling
of somebody else's documentation, stale the moment it changes.

That is also what keeps the rule honest about names. A route is matched only
as a decorator, because `get`, `post` and `delete` are the same names an HTTP
client goes by and reading every `.post(...)` in the tree would find a route in
the first adapter that talks to a neighbour. A subscription is matched
anywhere, because `subscriber` is not a word anything else here is called.

A block named after a framework the rule does not know is refused by name, with
the ones it knows listed.

**Why.** A route decorator is a contract. Whoever reads the generated schema —
a neighbouring service, a person writing a client — reads only what the
decorator declared, and a field that is not there does not exist for them,
whatever the function body returns.

FastAPI has the mechanism; it demands none of it. A route with no `summary`
lands in the schema with the function's name in place of a description
("Create Ladder" — a phrase about the code, not about the endpoint), and with
an empty `responses` it lands with a promise that it never refuses: success is
inferred from the signature, refusals are not, and nothing in the schema says
this route answers 409.

The first argument is the only thing in a decorator whose meaning depends on
position. A path is written as `path=` and a path passed positionally is
refused; a topic is written first and without a name and a subscription that
names it is refused. Both are the frameworks' own conventions, so neither is
in the table.

`response_model` is not required where there is no body: 204, 205 and 304 — a
response model next to them promises what the protocol forbids. A status
written as neither a number nor an `HTTPStatus` member reads as unknown, and
an unknown one is taken to have a body: a check that fired needlessly is
lifted by a mark, while one that stayed silent is a contract nobody will miss.

A route with `include_in_schema=False` the rule leaves alone: the schema is
what it protects, and such a route is not in it. That is exactly `/docs` and
its neighbours — they describe the schema rather than stand in it.

A consumer is the other entrance in the same layer, and it has neither a
status nor a response model. What it declares instead is what happens to a
record: which topic, under whose group, how the bytes are read, when the
offset moves and where a new group starts. Every one of those has a FastStream
default, and every default is a decision the design already made differently —
`AckPolicy.REJECT_ON_ERROR` drops the record the broker has just redelivered,
`auto_offset_reset="latest"` skips the backlog a new group exists to read, and
an automatic decoder turns the bytes into a dict before the inbox has seen
what arrived.

**Instead of Schemathesis.** It solves the neighbouring problem: it takes a
finished schema and checks, by requests against a running service, that the
answers match it. About an empty `responses` it says nothing — the service
answers exactly as promised, that is, with nothing. Useful on top, not
instead.

**The mark.** `# api-ok: edge-declarations: <reason>`.

### 5.8 calls — where a function may be called from

#### `confined-functions` — a named function was called from somewhere it may not be

```toml
[tool.py-checks.confined-functions]
declared-in = "shared/money"

[tool.py-checks.confined-functions.calls]
to_eur = [
    "modules/acceptance/application/use_cases/convert_stake",
    "modules/cashout/application",
    "modules/limits/domain/services/money",
]
from_eur = ["modules/cashout/application"]
in_cents = [
    "modules/acceptance/application/use_cases/convert_stake",
    "modules/cashout/application",
    "modules/limits/domain/services/money",
]
```

**Why.** A service counts in one currency, and the guarantee behind that
sentence is not the name of a type: it is that conversion has one
implementation and its call sites can be listed. Three edges convert, and each
has a reason a reader can check: acceptance measures the stake once, on the
way in, and records the result together with the rate that produced it;
cashout converts the stake inwards and the offer outwards at one rate — which
is why the number the player sees does not depend on the rate moving between
two calls; limits convert the configured ceiling at the moment the coupon is
judged, which is why the ceiling follows the rate and nobody has to reissue
the settings.

Anywhere else, a conversion is an amount in somebody's currency in the middle
of a calculation — the very thing "euros on the inside" exists to prevent —
and the error it gives is a number that is right up to the day two currencies
meet.

`in_cents` is on the list for a narrower reason: it is not a conversion, but
it is the second place where an exact quantity stops being exact, and a
quantity rounded early is a rounding the arithmetic never asked for.

A place is a piece of a path, not a file: an edge is a place in the design,
and a file split in two has not stopped being an edge. `declared-in` takes the module
where the function is declared out of the rule's reach: there it is written,
not called.

**The mark.** `# call-ok: confined-functions: <reason>`.

### 5.9 hygiene — the manifest

#### `dependency-bounds` — a dependency may move to a version nobody has ever run

```toml
[tool.py-checks.dependency-bounds]
# ceilings default to ==, <=, <, ~=, ===
# pins default to rev, tag
```

**Why.** A requirement declares a ceiling one of two ways: an exact version
(`greenlet==3.5.5`) or a floor-and-ceiling pair (`pydantic>=2.13.5,<3`;
`structlog~=26.1` is the same thing said differently).

A bare floor is refused — `pre-commit>=4.6.2`. It reads as a minimum and
behaves as "whatever is newest the moment somebody rebuilt the lock": a major
comes out, the lock moves, and the change arrives in whichever commit happened
to touch the dependencies. A ceiling makes that arrival a deliberate edit,
with a diff behind it and a test run — the only place a breaking upgrade can
be read at all.

`uv.lock` does not replace this: it pins what is installed today and is
rebuilt — a constraint is what survives the rebuild.

Every group is checked — `project.dependencies`, extras, `dependency-groups`,
`build-system.requires`: a test dependency decides whether the suite passes,
and a build one whether a wheel exists at all. There is one exception, and it
carries its own nail: a requirement with no specifiers whose name is in
`[tool.uv.sources]` with a `rev` or a `tag`.

This rule judges a project rather than a source file: instead of a parsed file
it is handed the root, and it is called once per run along with the rest —
`py-checks run`. What it is handed, the rule says itself, in its `scope`.

**The mark.** `# hygiene-ok: dependency-bounds: <reason>`.

### 5.10 errors — what a module refuses with

#### `refusals` — a no nobody can branch on

```toml
[tool.py-checks.refusals]
zones = ["modules"]
carries = "refusal"
allow = ["NotImplementedError"]
internal = ["InvariantError", "StaleWriteError"]
```

**Why.** A refusal has two halves. The sentence is for a person: it is read in
a log, it gets rewritten, and nothing may depend on its wording. The code is
what a caller branches on — "not enough funds" is a screen, "the basket
changed" is a re-price — so the sentence is free to change and the code is
not. That only holds while every no a module says carries one.

A builtin exception carries neither. A `ValueError` crossing a use case is a
refusal about which the outside knows only that it happened, and the perimeter
turns it into a 500 because there is nothing else it can honestly do.
`allow` names the builtins that are not refusals: `NotImplementedError` is not
a no, it is a method that does not exist yet, and it is the one exception a
reader never mistakes for an answer.

`carries` is the name of the field a refusal of your own is given
(`raise BasketChanged(refusal=Refusal.BASKET_CHANGED)`). Leave it out and the
rule judges only the builtins — which is the whole of it for a service that
has no vocabulary of codes yet.

`internal` names your errors that are not a no to anybody outside: they say
the code is written wrong, that a port broke its promise, or that a record
contradicts what is stored. Nobody branches on those, and the answer to them
is a retry or a page.

**Instead of ruff.** `TRY002` fires on `raise Exception(...)` and nothing
else — a `ValueError` is exactly as codeless and passes it. `TRY003` is about
the length of a message, not about whether anything can be done with it.

**The mark.** `# error-ok: refusals: <reason>`.

## 6. The generated files

Two files in the repository are not written by hand and not checked either —
they are built, by `py-checks sync`, from what they are derived from. The hook
`py-checks-sync` (`sync --check`) fails when they have fallen behind.

### `.importlinter` — from the layer table

```toml
[tool.py-checks.contracts]
# Tying the layers together is the whole of their work, so they may see all.
composition-root = ["ioc", "bootstrap", "entrypoints"]

# Dependencies point inwards: the domain knows nothing, the application knows
# the domain, and everything that speaks to the outside world knows the
# application and is invisible to it. `presentation` deliberately does not see
# `domain`: the edge translates its own types into the application's DTOs and
# back, and a router reading a domain object has tied the shape of the outside
# world to the shape of the rules.
[tool.py-checks.contracts.layers]
domain = ["domain", "shared"]
application = ["domain", "application", "shared"]
infra = ["domain", "application", "infra", "shared", "config"]
presentation = ["application", "presentation", "shared", "config"]
observability = ["observability", "shared", "config"]
config = ["config", "shared"]
shared = ["shared"]
```

The file is built from the table **and** from what is on disk: a layer that
does not exist is left out of the contract, otherwise import-linter would fail
on the first module that is not there. Modules get an `independence` contract
and migrations a `forbidden` one against the application package — both come
out of the layout rather than out of the table.

`header` writes the built file's own header, `#` included — for a project
whose comments are in another language.

**Where the services differed.** D has one more layer between the application
and the edge — an operation that needs two modules is a workflow:

```toml
workflows = ["domain", "application", "workflows", "shared"]
presentation = ["application", "workflows", "presentation", "shared", "config"]
```

### `.env.example` — from the settings classes

```toml
[tool.py-checks.env-example]
settings = ["myservice.config.settings:Settings"]
# path defaults to ".env.example"
# header — your own header, `#` included
```

The root class is named; the sections find themselves from there: a field
whose type is a model is "another group of variables starts here". Such a
field does not become a variable — it has no name of its own in the
environment. What goes into the file is the variable's name, its default, the
first paragraph of the class docstring and the field's `description` if it has
one — the comment somebody used to write beside the variable moves to the
field, where it is read without the file.

The price is that the generator imports the settings, that is, runs
application code. There is no other way: the variable's name is an attribute's
value assembled by a call, and reading it as text would mean performing that
call yourself.

Half of this convention is still a check: `config-fields` with
`alias = "validation_alias"` requires a field to name the variable it is read
from. Without that only pydantic knows the name — it derives it from the field
name and a prefix — and there is nothing to build `.env.example` out of. A
field declared with `default_factory` is the exception: that is a nested
section, not a value, and the variables are read by its own fields.

## 7. What is handed to others

### ruff

`ruff.toml` in the root; `pyproject.toml` then holds no `[tool.ruff]` section
— having found its own file in the root, ruff stops reading pyproject
entirely, and a section left there silently stops applying.

```toml
line-length = 100
target-version = "py314"

[lint]
select = [
    "E",
    "F",
    "I",
    "UP",
    "B",
    "S",       # bandit: assert, weak randomness, injections
    "ASYNC",   # a blocking call inside async def
    "DTZ",     # datetime with no zone
    "N",       # naming
    "ARG",     # an argument nobody reads
    "ANN401",  # `Any` in a parameter or a return
    "TC",      # an import for an annotation, needed by the type checker only
    "ERA",     # commented-out code
    "T20",     # a forgotten print
    "SIM117",  # a nested `with` instead of one `with a, b:`, with an autofix
    "PLR0912", # too many branches
    "PLR0915", # too many statements
    "PLR2004", # a number in a comparison instead of a constant
    "PGH",     # a blind ignore hides every future error too; name the code
]
# B008: a call in a default is how fastapi and typer declare dependencies —
# there it is the signature, not hidden state.
ignore = ["B008"]

[lint.flake8-tidy-imports.banned-api]
# A Literal is a vocabulary written as loose strings: nothing names it,
# nothing walks it, and the same words are typed again wherever a value is
# built, compared or stored. A StrEnum is the same set with a name: the
# members are in one place, a test can walk them, and a column's CHECK is
# taken from there.
"typing.Literal".msg = "a vocabulary of strings is a StrEnum, not a Literal"
```

Per-directory relief is the project's; what every service had in common:

```toml
[lint.per-file-ignores]
# A test asserts — that is what it is for; the number it compares against is
# the subject of the test, and a name in place of the number hides it.
"tests/*" = ["S101", "PLR2004", "ARG001", "S105", "S106", "TC001", "TC002", "TC003"]
# fastapi, dishka and pydantic read annotations at run time: an import moved
# under TYPE_CHECKING is not a saving here but a NameError at route
# declaration.
"src/*/presentation/*" = ["TC001", "TC002", "TC003"]
"src/*/bootstrap/*" = ["TC001", "TC002", "TC003"]
"src/*/ioc/*" = ["TC001", "TC002", "TC003"]
"src/*/config/*" = ["TC001", "TC002", "TC003"]
"src/*/infra/database/models/*" = ["TC001", "TC002", "TC003"]
# A revision is alembic's own template, and the SQL in it is written in words
# and frozen on the migration's birthday.
"migrations/versions/*" = ["TC003", "S608"]
```

### pyright

`pyrightconfig.json` in the root — for the same reason: having found it,
pyright stops reading `[tool.pyright]` from pyproject.

```json
{
  "pythonVersion": "3.14",
  "typeCheckingMode": "strict",
  "venvPath": ".",
  "venv": ".venv",
  "include": ["src", "tests"]
}
```

Strict everywhere rather than per directory: an unannotated function and an
`Any` that reached a boundary are errors in the composition root as well.

### pytest-alembic — a migration that rolls back

`test_up_down_consistency` applies and rolls back every revision against a
real database — stronger than any reading of the source.

What it will not say: a `downgrade()` left as `pass` rolls back beautifully
and rolls nothing back. A migration that honestly cannot be undone says so out
loud:

```python
def downgrade() -> None:
    raise NotImplementedError("drops the audit table; restore from a backup")
```

`pass` is a release with no way out: a deployment that went wrong at three in
the morning is then fixed forwards by whoever is awake. Writing the reverse
while the forward one is fresh takes minutes.

### A symlink — `CLAUDE.md` for `AGENTS.md`

Two tools read two names for the same instructions. A pointer inside the file
does not work: each reads only its own name, and a file with a link instead of
text is a file with no content for the agent that opened it. So a symlink at
the filesystem level, rather than a copy or a check that two texts are equal:

```bash
ln -s AGENTS.md CLAUDE.md
```

After that there is nothing to check — a broken symlink is caught by the
ready-made `check-symlinks` and `destroyed-symlinks` hooks. One caveat:
symlinks travel badly to Windows and through some editors.

### mutmut — surviving mutants

A CI step of the project with a baseline of its own, not a rule: mutation
testing needs the test suite, several minutes and a list of what already
survives. Its config lives where mutmut looks for it — `[tool.mutmut]` in
`pyproject.toml`, or `[mutmut]` in `setup.cfg` if the project keeps its tool
settings in separate files.
