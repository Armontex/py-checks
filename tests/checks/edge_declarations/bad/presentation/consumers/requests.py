"""Декоратор, забывший ack_policy и auto_offset_reset."""

from faststream.kafka import KafkaRouter

from shop.presentation.consumers.reading import keep_bytes, parse_raw_record

router = KafkaRouter()


@router.subscriber(
    "neighbour.example-request.v1",
    group_id="svc.requests",
    parser=parse_raw_record,
    decoder=keep_bytes,
    no_reply=True,
)
async def example_requested(body: bytes) -> None:
    _ = body
