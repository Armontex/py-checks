"""Связь грузится только там, где запрос это сказал."""

from sqlalchemy.orm import Mapped, relationship


class PlayerModel:
    bets: Mapped[list["BetModel"]] = relationship(back_populates="player", lazy="raise")
    tenant: Mapped["TenantModel"] = relationship(lazy="raise_on_sql")
