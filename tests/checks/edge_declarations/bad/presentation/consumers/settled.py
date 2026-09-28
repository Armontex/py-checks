"""Роутер без парсера; брокер из другого модуля; имя, собранное дважды по-разному."""

from faststream import AckPolicy
from faststream.kafka import KafkaRouter

from shop.presentation.consumers.brokers import broker
from shop.presentation.consumers.reading import keep_bytes, parse_raw_record

router = KafkaRouter(decoder=keep_bytes)

twice = KafkaRouter(parser=parse_raw_record, decoder=keep_bytes)
twice = KafkaRouter(decoder=keep_bytes)


@router.subscriber(
    "bets.settled",
    group_id="shop.settled",
    ack_policy=AckPolicy.MANUAL,
    no_reply=True,
    auto_offset_reset="earliest",
)
async def bet_settled(body: bytes) -> None:
    _ = body


@broker.subscriber(
    "bets.voided",
    group_id="shop.voided",
    decoder=keep_bytes,
    ack_policy=AckPolicy.MANUAL,
    no_reply=True,
    auto_offset_reset="earliest",
)
async def bet_voided(body: bytes) -> None:
    _ = body


@twice.subscriber(
    "bets.cashed",
    group_id="shop.cashed",
    ack_policy=AckPolicy.MANUAL,
    no_reply=True,
    auto_offset_reset="earliest",
)
async def bet_cashed(body: bytes) -> None:
    _ = body
