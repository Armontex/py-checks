"""Типы и аннотации.

Чем объявлено значение и что об этом видно из подписи. Готовых правил тут
почти нет: `typing.Literal` закрывается строкой `banned-api` в ruff, голый
дженерик — строгим режимом pyright, остальное — соглашения проекта.
"""

from py_checks.checks.types._annotation_shapes import (
    AnnotationShapes,
    AnnotationShapesSettings,
)
from py_checks.checks.types._config_fields import ConfigFields, ConfigFieldsSettings
from py_checks.checks.types._confined_types import ConfinedTypes, ConfinedTypesSettings
from py_checks.checks.types._constant_annotations import (
    ConstantAnnotations,
    ConstantAnnotationsSettings,
)
from py_checks.checks.types._frozen_dataclasses import (
    FrozenDataclasses,
    FrozenDataclassesSettings,
)
from py_checks.checks.types._marker import MARKER

__all__ = [
    "MARKER",
    "AnnotationShapes",
    "AnnotationShapesSettings",
    "ConfigFields",
    "ConfigFieldsSettings",
    "ConfinedTypes",
    "ConfinedTypesSettings",
    "ConstantAnnotations",
    "ConstantAnnotationsSettings",
    "FrozenDataclasses",
    "FrozenDataclassesSettings",
]
