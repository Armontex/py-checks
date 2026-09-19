from sqlalchemy.orm import Mapped

from shop.infra.database.models.base import Base


class OrderModel(Base):
    order_id: Mapped[int]
