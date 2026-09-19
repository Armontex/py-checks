import structlog

from shop.shared.log_events import LogEvent

logger = structlog.get_logger()


class PlaceOrder:
    async def __call__(self, *, order_id: str) -> None:
        logger.info(LogEvent.ORDER_PLACED, order_id=order_id)
        self._logger.warning(LogEvent.ORDER_SLOW, order_id=order_id)
        logger.info("psycopg говорит своё")  # effect-ok: log-events: не наш логгер
        self._session.info(order_id)
