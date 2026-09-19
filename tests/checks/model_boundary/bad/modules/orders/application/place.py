from sqlalchemy.orm import Mapped

from shop.infra.database.models.base import Base
from shop.infra.database.models.order import OrderModel


class PlaceOrder:
    async def __call__(self, *, order_id: int) -> None:
        self._session.add(OrderModel(order_id=order_id))


class DraftModel(Base):
    draft_id: Mapped[int]
