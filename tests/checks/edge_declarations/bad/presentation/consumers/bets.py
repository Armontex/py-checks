from faststream.kafka import KafkaBroker

from shop.presentation.consumers.reading import keep_bytes, parse_raw_record


def subscribe(*, broker: KafkaBroker, handler: object) -> None:
    subscriber = broker.subscriber(
        topic="bets.placed",
        group_id="shop.bets",
        parser=parse_raw_record,
        decoder=keep_bytes,
        ack_policy="manual",
        no_reply=True,
        auto_offset_reset="none",
    )
    subscriber(handler)


def subscribe_settled(*, broker: KafkaBroker, handler: object) -> None:
    subscriber = broker.subscriber(
        "bets.settled",
        group_id="shop.bets",
    )
    subscriber(handler)
