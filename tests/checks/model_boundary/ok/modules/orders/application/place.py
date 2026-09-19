class PlaceOrder:
    async def __call__(self, *, order_id: int) -> None:
        await self._orders.add(order_id=order_id)
