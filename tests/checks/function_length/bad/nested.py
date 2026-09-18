"""Вложенная функция считается отдельно и входит в длину внешней."""


def outer() -> int:
    def inner() -> int:
        step_0 = 0
        step_1 = 1
        step_2 = 2
        step_3 = 3
        step_4 = 4
        step_5 = 5
        step_6 = 6
        step_7 = 7
        step_8 = 8
        step_9 = 9
        step_10 = 10
        step_11 = 11
        return step_0

    return inner()
