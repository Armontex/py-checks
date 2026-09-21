from faststream import AckPolicy
from faststream.kafka import KafkaBroker

from shop.presentation.consumers.reading import keep_bytes, parse_raw_record


def subscribe(*, broker: KafkaBroker, handler: object) -> None:
    """Подписка живёт в переменной: до старта у неё берут клиента."""
    subscriber = broker.subscriber(
        "bets.placed",
        group_id="shop.bets",
        parser=parse_raw_record,
        decoder=keep_bytes,
        ack_policy=AckPolicy.MANUAL,
        no_reply=True,
        auto_offset_reset="none",
    )
    subscriber(handler)
