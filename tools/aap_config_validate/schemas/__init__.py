"""Schema definitions for all AAP resource types."""

from __future__ import annotations

from typing import Dict

from aap_config_validate.models import ResourceSchema
from aap_config_validate.schemas.controller import CONTROLLER_SCHEMAS
from aap_config_validate.schemas.eda import EDA_SCHEMAS
from aap_config_validate.schemas.gateway import GATEWAY_SCHEMAS
from aap_config_validate.schemas.hub import HUB_SCHEMAS


def get_all_schemas() -> Dict[str, ResourceSchema]:
    """Return a mapping of dispatch variable name to schema.

    When multiple roles share the same var, the schema for the *primary*
    role (the first one that creates/manages the resource) is returned.
    """
    combined: Dict[str, ResourceSchema] = {}
    for collection in (GATEWAY_SCHEMAS, HUB_SCHEMAS, CONTROLLER_SCHEMAS, EDA_SCHEMAS):
        for schema in collection:
            if schema.var not in combined:
                combined[schema.var] = schema
    return combined


def get_schemas_by_component(component: str) -> list[ResourceSchema]:
    return {
        "gateway": GATEWAY_SCHEMAS,
        "hub": HUB_SCHEMAS,
        "controller": CONTROLLER_SCHEMAS,
        "eda": EDA_SCHEMAS,
    }.get(component, [])
