"""Types and annotations.

What a value is declared with, and what the signature shows of it. There are
almost no ready-made rules here: `typing.Literal` is covered by a `banned-api`
line in ruff, a bare generic by pyright's strict mode, the rest is the
project's own convention.
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
