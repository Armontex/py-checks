from sqlalchemy import insert

from shop.infra.database.models.order import OrderModel


class OrderRepository:
    async def add(self, *, order_id: object, placed_at: object) -> None:
        await self._session.execute(
            insert(OrderModel).values(order_id=order_id, placed_at=placed_at)
        )
