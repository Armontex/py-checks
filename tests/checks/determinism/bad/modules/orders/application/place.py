import random
from datetime import UTC, datetime
from uuid import UUID, uuid4


class PlaceOrder:
    async def __call__(self, *, total: int) -> UUID:
        order_id = uuid4()
        await self._orders.add(
            order_id=order_id,
            total=total,
            placed_at=datetime.now(UTC),
            bucket=random.choice((1, 2)),
        )
        return order_id
