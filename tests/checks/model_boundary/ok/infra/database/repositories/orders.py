from dataclasses import dataclass

from shop.infra.database.models.order import OrderModel


@dataclass(frozen=True, slots=True)
class Order:
    order_id: int


class OrderRepository:
    async def add(self, *, order: Order) -> None:
        self._session.add(OrderModel(order_id=order.order_id))

    async def get(self, *, order_id: int) -> Order | None:
        row = await self._session.get(OrderModel, order_id)
        return None if row is None else self._order_of(row=row)

    @staticmethod
    def _order_of(*, row: OrderModel) -> Order:
        return Order(order_id=row.order_id)
