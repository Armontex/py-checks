from __future__ import annotations

import ast

from python_checks.checks._kind import Kind, declarations


def kinds(source: str) -> dict[str, Kind]:
    return {
        declared.name: declared.kind
        for declared in declarations(tree=ast.parse(source))
        if declared.kind is not None
    }


def test_a_protocol_and_an_abstract_base_are_ports() -> None:
    source = """
from abc import ABC
from typing import Protocol

class Writer(Protocol): ...
class Reader(ABC): ...
"""

    assert kinds(source) == {"Writer": Kind.PORT, "Reader": Kind.PORT}


def test_pydantic_and_enums_and_dataclasses_are_told_apart() -> None:
    source = """
from dataclasses import dataclass
from enum import StrEnum
from pydantic import BaseModel

class Answer(BaseModel): ...
class Status(StrEnum): ...

@dataclass
class Order: ...

class Plain: ...
"""

    assert kinds(source) == {
        "Answer": Kind.MODEL,
        "Status": Kind.ENUM,
        "Order": Kind.DATACLASS,
        "Plain": Kind.CLASS,
    }


def test_a_class_whose_base_lives_elsewhere_is_not_judged() -> None:
    """`class Mismatch(ErrorResponse)` — модель, но узнать это по одному файлу нельзя."""
    source = "class Mismatch(ErrorResponse): ...\n"

    assert kinds(source) == {}


def test_a_dataclass_keeps_its_kind_even_with_a_foreign_base() -> None:
    source = """
from dataclasses import dataclass

@dataclass
class Order(Base): ...
"""

    assert kinds(source) == {"Order": Kind.DATACLASS}


def test_aliases_are_the_three_ways_of_naming_a_type() -> None:
    source = """
from typing import NewType, TypeAlias

Writer: TypeAlias = object
Money = NewType("Money", int)
Rows = dict[str, int]
Either = int | str
"""

    assert kinds(source) == {
        "Writer": Kind.ALIAS,
        "Money": Kind.ALIAS,
        "Rows": Kind.ALIAS,
        "Either": Kind.ALIAS,
    }


def test_constants_and_imports_are_not_declarations() -> None:
    """Они разрешены везде, и правилу размещения о них говорить нечего."""
    source = """
import os

LIMIT = 10
names = ["a"]
"""

    assert kinds(source) == {}


def test_functions_are_a_kind_of_their_own() -> None:
    source = "def helper(*, stake: int) -> int: ...\nasync def fetch() -> None: ...\n"

    assert kinds(source) == {"helper": Kind.FUNCTION, "fetch": Kind.FUNCTION}
