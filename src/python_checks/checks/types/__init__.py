"""Типы и аннотации.

Чем объявлено значение и что об этом видно из подписи. Готовых правил тут
почти нет: `typing.Literal` закрывается строкой `banned-api` в ruff, голый
дженерик — строгим режимом pyright, остальное — соглашения проекта.
"""

from python_checks.checks.types._annotation_shapes import (
    AnnotationShapes,
    AnnotationShapesSettings,
)
from python_checks.checks.types._config_fields import ConfigFields, ConfigFieldsSettings
from python_checks.checks.types._confined_types import ConfinedTypes, ConfinedTypesSettings
from python_checks.checks.types._constant_annotations import (
    ConstantAnnotations,
    ConstantAnnotationsSettings,
)
from python_checks.checks.types._frozen_dataclasses import (
    FrozenDataclasses,
    FrozenDataclassesSettings,
)
from python_checks.checks.types._marker import MARKER

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
