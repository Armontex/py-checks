## v0.2.0 (2026-09-20)

### Features

- шапку `.env.example` можно написать свою

## v0.1.2 (2026-09-20)

### Fixes

- в строке читаются все маркеры, а не первый

## v0.1.1 (2026-09-20)

### Fixes

- потолок rich опущен до 14

## v0.1.0 (2026-09-20)

### Features

- **signatures**: правило `function-length`
- **sync**: хватает корневого класса настроек
- **sync**: `.env.example` собирается из классов настроек
- **cli**: `--select` принимает список кодов через запятую
- **config**: свой файл настроек рядом с pyproject
- **config-fields**: поле называет переменную окружения
- правило dependency-bounds
- правило confined-functions
- правило endpoint-declarations
- правило log-events
- правило determinism
- команда drift
- правило model-boundary
- правило model-columns
- правило bound-checks
- правило raw-sql
- правило statement-keys
- правило confined-calls
- правила annotation-shapes и constant-annotations
- правило confined-types
- правило config-fields
- kw_only в списке обязательных аргументов dataclass
- правило frozen-dataclasses
- правило signature-layout
- предел аргументов входа в operation-shape
- правило argument-count
- правило nesting
- правило function-length
- правило operation-shape
- правило required-class
- правило class-placement
- **checks**: вид `error` — исключения тоже размещаются
- **checks**: class-modules — директория объявляет, что в ней живёт
- **checks**: confined-imports и sealed-imports закрывают группу импортов
- **contracts**: слои, модули и миграции проверяет import-linter
- **sync**: общие настройки ruff и pyright живут в библиотеке
- **core**: автофикс и правки в нарушениях
- **core**: один маркер на все проверки
- **checks**: keyword-only-arguments
- **checks**: module-length, the first real rule
- **cli**: run, list and explain
- **core**: file discovery, parsing, violations and settings

### Fixes

- **signatures**: пометка `function-length` читается со всей подписи
- **contracts**: поле-список пишется в столбик, библиотека проверяет себя
- **checks**: первый аргумент метода узнаётся по месту, а слово — по группе

### Refactoring

- библиотека называется py-checks
- **checks**: узел превращается в нарушение одним способом
- **checks**: зона - понятие, а не совпадение
- **checks**: имя узла - одно на библиотеку, а не по копии в классе
- **schema-drift**: расхождение схем - правило, а не команда
- **core**: один реестр вместо двух половин
- **sync**: библиотека возит проверки, настройки инструментов возит шаблон
- **checks**: адрес файла — замороженный dataclass
- библиотека знает движок, таблицы знает проект
- **checks**: помощники правила живут в его классе
- все аргументы по имени
- **cli**: name the shape of a command registrar
- **cli**: a command registers itself
- **config**: type TOML tables instead of Any
- **core**: one purpose per module
- **config**: one purpose per module
