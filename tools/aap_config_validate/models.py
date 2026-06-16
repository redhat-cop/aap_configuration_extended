"""Core data models shared across the validator."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field as dc_field
from typing import Any, Dict, List, Optional, Sequence

VALID_STATES = frozenset({"present", "absent", "exists", "enabled", "disabled"})


class Severity(enum.Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class Issue:
    severity: Severity
    path: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class Field:
    type: str = "any"
    required: bool = False
    choices: Optional[Sequence[Any]] = None
    aliases: Optional[List[str]] = None
    xref: Optional[str] = None


@dataclass
class ResourceSchema:
    var: str
    roles: List[str]
    aliases: Optional[List[str]] = None
    component: str = "controller"
    is_list: bool = True
    item_id_field: str = "name"
    item_schema: Dict[str, Field] = dc_field(default_factory=dict)


@dataclass
class DispatchEntry:
    role: str
    var: str
    tags: List[str]
    extras: Dict[str, Any] = dc_field(default_factory=dict)
