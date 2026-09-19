import structlog

logger = structlog.get_logger()


class PlaceOrder:
    async def __call__(self, *, order_id: str) -> None:
        logger.info("order.placed", order_id=order_id)
        self._logger.warning(f"заказ {order_id} медленный")
