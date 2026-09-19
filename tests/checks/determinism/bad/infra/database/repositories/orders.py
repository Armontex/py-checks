from sqlalchemy import func, insert

from shop.infra.database.models.order import OrderModel


class OrderRepository:
    async def add(self, *, order_id: object) -> None:
        await self._session.execute(
            insert(OrderModel).values(order_id=func.gen_random_uuid(), placed_at=func.now())
        )
