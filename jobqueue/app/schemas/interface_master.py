"""Interface master schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class InterfaceMasterCreate(BaseModel):
    """Interface master creation schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Interface name")
    description: str | None = Field(None, description="Interface description")
    input_schema: dict[str, Any] | None = Field(
        None, description="JSON Schema V7 for input validation"
    )
    output_schema: dict[str, Any] | None = Field(
        None, description="JSON Schema V7 for output validation"
    )


class InterfaceMasterUpdate(BaseModel):
    """Interface master update schema."""

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Interface name"
    )
    description: str | None = Field(None, description="Interface description")
    input_schema: dict[str, Any] | None = Field(
        None, description="JSON Schema V7 for input validation"
    )
    output_schema: dict[str, Any] | None = Field(
        None, description="JSON Schema V7 for output validation"
    )
    is_active: bool | None = Field(None, description="Active status")


class InterfaceMasterResponse(BaseModel):
    """Interface master response schema.

    Note: Both 'id' and 'interface_id' are provided for API consistency.
    - 'id': Standard field name for consistency with detail/list responses
    - 'interface_id': Legacy field name for backward compatibility
    """

    interface_id: str
    id: str | None = Field(None, description="Interface ID (same as interface_id)")
    name: str

    @model_validator(mode="after")
    def set_id_from_interface_id(self) -> "InterfaceMasterResponse":
        """Ensure 'id' field is set from 'interface_id' for consistency."""
        if self.id is None:
            self.id = self.interface_id
        return self


class InterfaceMasterDetail(BaseModel):
    """Interface master detail schema."""

    id: str
    name: str
    description: str | None
    input_schema: dict[str, Any] | None
    output_schema: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InterfaceMasterList(BaseModel):
    """Interface master list schema."""

    interfaces: list[InterfaceMasterDetail]
    total: int
    page: int
    size: int


class InterfaceAssociationCreate(BaseModel):
    """Interface association creation schema."""

    interface_id: str = Field(..., description="Interface master ID")
    required: bool = Field(True, description="Whether this interface is required")


class InterfaceAssociationResponse(BaseModel):
    """Interface association response schema."""

    id: int
    task_master_id: str
    interface_id: str
    required: bool
    created_at: datetime

    model_config = {"from_attributes": True}
