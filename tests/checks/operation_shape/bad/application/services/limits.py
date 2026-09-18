"""У сервиса дверей сколько угодно, но фабрика транзакций ему не положена."""


class LimitsService:
    factory: "UnitOfWorkFactory"

    def checked(self) -> bool:
        return True
