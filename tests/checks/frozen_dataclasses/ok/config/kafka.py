"""Вне зоны: конфиг собирают из окружения, и правило его не касается."""

from dataclasses import dataclass


@dataclass
class KafkaSettings:
    topic: str = "orders"
