from shop.infra.database.models.order import OrderModel


class OrderRepository:
    async def get(self, *, order_id: int) -> OrderModel | None:
        return await self._session.get(OrderModel, order_id)

    async def _raw(self, *, order_id: int) -> OrderModel | None:
        return await self._session.get(OrderModel, order_id)
