import uuid
from datetime import datetime
from typing import Any

from pydantic import AwareDatetime, Field

from octopoes.models import Reference, PotatoModel
from octopoes.models.types import OOIType


class ServiceHealth(PotatoModel):
    service: str
    healthy: bool = False
    version: str | None = None
    additional: Any = None
    results: list["ServiceHealth"] = Field(default_factory=list)


ServiceHealth.model_rebuild()


class _BaseObservation(PotatoModel):
    method: str
    source: Reference
    result: list[OOIType]
    valid_time: AwareDatetime
    task_id: uuid.UUID


# Connector models (more generic)
class Observation(_BaseObservation):
    """Used by Octopoes Connector to describe request body"""

    result: list[OOIType]
    valid_time: datetime


class Declaration(PotatoModel):
    """Used by Octopoes Connector to describe request body"""

    ooi: OOIType
    valid_time: datetime
    method: str | None = None
    task_id: uuid.UUID | None = None


class ScanProfileDeclaration(PotatoModel):
    reference: Reference
    level: int
    valid_time: datetime


# API models (timezone validation and pydantic parsing)
class ValidatedObservation(_BaseObservation):
    """Used by Octopoes API to validate and parse correctly"""

    result: list[OOIType]
    valid_time: AwareDatetime


class ValidatedDeclaration(PotatoModel):
    """Used by Octopoes API to validate and parse correctly"""

    ooi: OOIType
    valid_time: AwareDatetime
    method: str | None = "manual"
    task_id: uuid.UUID | None = Field(default_factory=lambda: uuid.uuid4())
