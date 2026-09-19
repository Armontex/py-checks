from uuid import UUID


class PlaceOrder:
    async def __call__(self, *, total: int) -> UUID:
        order_id = self._ids.new()
        await self._orders.add(order_id=order_id, total=total, placed_at=self._clock.now())
        return order_id
