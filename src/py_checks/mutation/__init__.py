"""Мутационный гейт: пуш не оставляет строки, поломку которой не заметит ни один тест.

Выживший мутант — строка, которую поменяли, а тесты прошли. Их список заменяет
чтение тестов глазами с вопросом «а они вообще что-нибудь проверяют?».

Гейт — запись, а не ноль: `record` пишет, сколько выживших числится за каждым
модулем, а `diff` и `full` отказывают, если где-то их стало больше. Поднять
запись — правка с объяснением, какой из выживших не стоит теста.

mutmut зовётся процессом, как `schema-drift` зовёт alembic: библиотека читает
его вывод, а не импортирует его. Совместимая версия закреплена в extra
`python-checks[mutation]` — формат вывода и есть договор между ними.
"""

from py_checks.mutation._constants import BASELINE, SECTION
from py_checks.mutation._errors import GateError
from py_checks.mutation._gate import Diffed, Gate, Verdict, gate
from py_checks.mutation._settings import Mutation, mutation

__all__ = [
    "BASELINE",
    "SECTION",
    "Diffed",
    "Gate",
    "GateError",
    "Mutation",
    "Verdict",
    "gate",
    "mutation",
]
