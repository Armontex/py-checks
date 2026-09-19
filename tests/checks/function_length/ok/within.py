def short():
    first = 1
    second = 2
    third = 3
    fourth = 4
    return first + second + third + fourth


def signature_does_not_count(
    first,
    second,
    third,
    fourth,
):
    return first + second + third + fourth


class Holder:
    @staticmethod
    def method():
        return 1
