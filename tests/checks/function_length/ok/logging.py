"""Одна настройка цепочкой: разрезать её пополам — положить порядок в два места."""


def configured() -> None:  # signature-ok: function-length: одна настройка, читается целиком
    configure(
        processors=[
        "processor_0",
        "processor_1",
        "processor_2",
        "processor_3",
        "processor_4",
        "processor_5",
        "processor_6",
        "processor_7",
        "processor_8",
        "processor_9",
        "processor_10",
        "processor_11",
        "processor_12",
        "processor_13",
        ],
    )


def configure(*, processors: list[str]) -> None:
    del processors
