"""Подписка декоратором — та же подписка, что и вызовом."""

from faststream import AckPolicy
from faststream.kafka import KafkaRouter

from shop.presentation.consumers.reading import keep_bytes, parse_raw_record

router = KafkaRouter()


@router.subscriber(
    "neighbour.example-request.v1",
    group_id="svc.requests",
    parser=parse_raw_record,
    decoder=keep_bytes,
    ack_policy=AckPolicy.MANUAL,
    no_reply=True,
    auto_offset_reset="earliest",
)
async def example_requested(body: bytes) -> None:
    _ = body
