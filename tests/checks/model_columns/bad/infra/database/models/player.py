"""Связи, которые загрузятся сами при первом касании."""

from sqlalchemy import orm
from sqlalchemy.orm import Mapped, relationship

LOADER = "raise"


class PlayerModel:
    bets: Mapped[list["BetModel"]] = relationship(back_populates="player")
    tenant: Mapped["TenantModel"] = relationship(lazy="selectin")
    wallet: Mapped["WalletModel"] = orm.relationship(lazy="select")
    limits: Mapped["LimitsModel"] = relationship(lazy=LOADER)
