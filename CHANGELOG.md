## v0.6.0 (2026-09-24)

### Features

- сообщения, докстринги и комментарии в src — по-английски
- **mutation**: прогон говорит, сколько запущено, убито и осталось
- **mutation**: мутационный гейт командой py-checks mutation

### Fixes

- **doctor**: зону ищет как директорию, а не как модуль
- class-placement говорит «is a dataclass», refusals — без игрока
- зона — это директории, а не модуль с тем же именем

## v0.5.0 (2026-09-21)

### BREAKING CHANGE

- [endpoint-declarations] -> [edge-declarations], блок на фреймворк:
`[edge-declarations.fastapi]` и `[edge-declarations.faststream]`, а в блоке
только `required`. Имена методов, декоратор или вызов, `response_model`,
статусы без тела и `include_in_schema` знает библиотека.

### Features

- **errors**: отказ несёт код, на который можно ветвиться
- **api**: вход объявляет себя, а таблица называет фреймворк

### Fixes

- **ci**: пропуск прогона не выдаётся форку

## v0.4.2 (2026-09-21)

### Fixes

- **placement**: притязание дома ограничивается областью
- **ci**: автослияние возврата требует прав на репозиторий (#14)

## v0.4.1 (2026-09-21)

### BREAKING CHANGE

- [model-columns] `unruled` -> `skip`; [bound-checks] `call`,
`column` и `primitive` собраны в блок `helper`.
- [nesting.limits] -> [nesting]; [confined-imports.packages] ->
[confined-imports]; [confined-types.zones] -> [confined-types]. Секция
[model-boundary] убрана: `declared` и `built` стали ключом `orm` в [layout],
`base` — ключом того же блока.
- [determinism] `sources` -> `instead`; [model-columns]
`types` -> `instead`; [raw-sql] `calls` -> `instead`; [statement-keys]
`calls` -> `sub-queries`.
- [confined-calls] `outside` -> `skip`, `said` -> `because`;
[confined-functions] `home` -> `declared-in`; [model-columns] `homes` ->
`wrappers`.
- секции [class-modules], [class-placement], [required-class]
и [operation-shape] заменены общей таблицей [layout]. Оставшаяся в настройках
секция падает с сообщением, куда её переписать.

### Features

- **cli**: команда doctor судит настройки, а не код
- **placement**: одна таблица [layout] вместо четырёх секций

### Refactoring

- «не суди это» — одно слово; хелпер — один блок
- секция сама себе таблица, model-boundary читает раскладку
- «запрещённое -> чем заменить» зовётся одним словом
- настройки зовут вещи одними словами

## v0.3.2 (2026-09-20)

### Docs

- README по-английски, русская версия — `docs/readmes/README.ru.md`
- `docs/service.md` переписан справочником: одна форма на правило, две
  языковые версии
- ссылки README на PyPI ведут в репозиторий полным адресом, в метаданных
  появились Homepage, Source, Issues, Changelog, Documentation

## v0.3.1 (2026-09-20)

## v0.3.0 (2026-09-20)

### Features

- шапку `.importlinter` тоже можно написать свою

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
