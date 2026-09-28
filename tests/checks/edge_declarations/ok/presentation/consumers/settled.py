"""Парсер и декодер решены один раз, на роутере, — подписке их не повторять."""

from faststream import AckPolicy
from faststream.kafka import KafkaRouter

from shop.presentation.consumers.reading import keep_bytes, parse_raw_record

router = KafkaRouter(prefix="", parser=parse_raw_record, decoder=keep_bytes)


@router.subscriber(
    "bets.settled",
    group_id="shop.settled",
    ack_policy=AckPolicy.MANUAL,
    no_reply=True,
    auto_offset_reset="earliest",
)
async def bet_settled(body: bytes) -> None:
    _ = body
