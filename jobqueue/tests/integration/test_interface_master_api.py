"""Integration tests for InterfaceMaster API endpoints."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.models.interface_master import InterfaceMaster
from app.models.task_master import TaskMaster
from app.models.task_master_interface import TaskMasterInterface


class TestInterfaceMasterAPI:
    """Test suite for InterfaceMaster API endpoints."""

    @pytest.mark.asyncio
    async def test_create_interface_master(self, client: AsyncClient) -> None:
        """Test creating a new interface master."""
        payload = {
            "name": "User Data Interface",
            "description": "Interface for user data",
            "input_schema": {
                "type": "object",
                "properties": {"user_id": {"type": "string"}},
                "required": ["user_id"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                },
                "required": ["name", "email"],
            },
        }
        response = await client.post("/api/v1/interface-masters", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "interface_id" in data
        assert data["name"] == "User Data Interface"

    @pytest.mark.asyncio
    async def test_list_interface_masters(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test listing interface masters."""
        # Create test interfaces
        for i in range(3):
            interface = InterfaceMaster(
                id=f"if_test_{i}",
                name=f"Interface {i}",
                description=f"Description {i}",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                is_active=True,
            )
            db_session.add(interface)
        await db_session.commit()

        response = await client.get("/api/v1/interface-masters?page=1&size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 3
        assert len(data["interfaces"]) >= 3

    @pytest.mark.asyncio
    async def test_get_interface_master(self, client: AsyncClient, db_session) -> None:
        """Test getting interface master details."""
        interface = InterfaceMaster(
            id="if_detail",
            name="Detail Interface",
            description="Test interface",
            input_schema={"type": "object", "properties": {"id": {"type": "string"}}},
            output_schema={
                "type": "object",
                "properties": {"result": {"type": "boolean"}},
            },
            is_active=True,
        )
        db_session.add(interface)
        await db_session.commit()

        response = await client.get("/api/v1/interface-masters/if_detail")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "if_detail"
        assert data["name"] == "Detail Interface"

    @pytest.mark.asyncio
    async def test_update_interface_master(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test updating interface master."""
        interface = InterfaceMaster(
            id="if_update",
            name="Original Name",
            description="Original description",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            is_active=True,
        )
        db_session.add(interface)
        await db_session.commit()

        update_payload = {
            "name": "Updated Name",
            "description": "Updated description",
        }
        response = await client.put(
            "/api/v1/interface-masters/if_update", json=update_payload
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_interface_master(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test logical deletion of interface master."""
        interface = InterfaceMaster(
            id="if_delete",
            name="Delete Test",
            description="To be deleted",
            is_active=True,
        )
        db_session.add(interface)
        await db_session.commit()

        response = await client.delete("/api/v1/interface-masters/if_delete")
        assert response.status_code == status.HTTP_200_OK

        await db_session.refresh(interface)
        assert interface.is_active is False

    @pytest.mark.asyncio
    async def test_associate_interface_to_task_master(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test associating an interface to a task master."""
        # Create task master
        task_master = TaskMaster(
            id="tm_assoc",
            name="Test Task",
            method="POST",
            url="https://api.example.com/test",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        # Create interface
        interface = InterfaceMaster(
            id="if_assoc",
            name="Test Interface",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            is_active=True,
        )
        db_session.add_all([task_master, interface])
        await db_session.commit()

        # Associate interface to task master
        payload = {"interface_id": "if_assoc", "required": True}
        response = await client.post(
            "/api/v1/task-masters/tm_assoc/interfaces", json=payload
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["task_master_id"] == "tm_assoc"
        assert data["interface_id"] == "if_assoc"
        assert data["required"] is True

    @pytest.mark.asyncio
    async def test_list_task_master_interfaces(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test listing interfaces associated with a task master."""
        # Create task master
        task_master = TaskMaster(
            id="tm_list_if",
            name="Test Task",
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        # Create interfaces
        if1 = InterfaceMaster(id="if1", name="Interface 1", is_active=True)
        if2 = InterfaceMaster(id="if2", name="Interface 2", is_active=True)
        db_session.add_all([task_master, if1, if2])
        await db_session.flush()

        # Create associations
        assoc1 = TaskMasterInterface(
            task_master_id="tm_list_if", interface_id="if1", required=True
        )
        assoc2 = TaskMasterInterface(
            task_master_id="tm_list_if", interface_id="if2", required=False
        )
        db_session.add_all([assoc1, assoc2])
        await db_session.commit()

        # List interfaces
        response = await client.get("/api/v1/task-masters/tm_list_if/interfaces")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert any(d["interface_id"] == "if1" and d["required"] for d in data)
        assert any(d["interface_id"] == "if2" and not d["required"] for d in data)

    @pytest.mark.asyncio
    async def test_associate_duplicate_interface_error(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test error when associating duplicate interface."""
        # Create task master and interface
        task_master = TaskMaster(
            id="tm_dup",
            name="Test",
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        interface = InterfaceMaster(id="if_dup", name="Interface", is_active=True)
        db_session.add_all([task_master, interface])
        await db_session.flush()

        # Create first association
        assoc = TaskMasterInterface(
            task_master_id="tm_dup", interface_id="if_dup", required=True
        )
        db_session.add(assoc)
        await db_session.commit()

        # Try to create duplicate association
        payload = {"interface_id": "if_dup", "required": False}
        response = await client.post(
            "/api/v1/task-masters/tm_dup/interfaces", json=payload
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already associated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_associate_to_nonexistent_task_master(
        self, client: AsyncClient
    ) -> None:
        """Test error when associating to non-existent task master."""
        payload = {"interface_id": "if_any", "required": True}
        response = await client.post(
            "/api/v1/task-masters/tm_nonexistent/interfaces", json=payload
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_associate_nonexistent_interface(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test error when associating non-existent interface."""
        task_master = TaskMaster(
            id="tm_test",
            name="Test",
            method="GET",
            url="https://api.example.com/test",
            timeout_sec=30,
            current_version=1,
            created_by="test",
            updated_by="test",
        )
        db_session.add(task_master)
        await db_session.commit()

        payload = {"interface_id": "if_nonexistent", "required": True}
        response = await client.post(
            "/api/v1/task-masters/tm_test/interfaces", json=payload
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # Phase 1.1 Tests: JSON Schema V7 Validation
    @pytest.mark.asyncio
    async def test_create_interface_master_invalid_input_schema(
        self, client: AsyncClient
    ) -> None:
        """Test creating interface with invalid input schema (Phase 1.1)."""
        payload = {
            "name": "Invalid Input Schema",
            "description": "This should fail",
            "input_schema": {
                "type": "invalid_type",  # Invalid JSON Schema type
                "properties": {"name": {"type": "string"}},
            },
            "output_schema": {"type": "object", "properties": {}},
        }
        response = await client.post("/api/v1/interface-masters", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid input_schema" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_interface_master_invalid_output_schema(
        self, client: AsyncClient
    ) -> None:
        """Test creating interface with invalid output schema (Phase 1.1)."""
        payload = {
            "name": "Invalid Output Schema",
            "description": "This should fail",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "minLength": "not_a_number",  # Should be integer
                    }
                },
            },
        }
        response = await client.post("/api/v1/interface-masters", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid output_schema" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_interface_master_valid_json_schema_v7(
        self, client: AsyncClient
    ) -> None:
        """Test creating interface with valid JSON Schema V7 (Phase 1.1)."""
        payload = {
            "name": "Valid Schema Interface",
            "description": "With proper JSON Schema V7 validation",
            "input_schema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "age": {"type": "integer", "minimum": 0, "maximum": 120},
                    "status": {
                        "type": "string",
                        "enum": ["active", "inactive", "pending"],
                    },
                },
                "required": ["user_id"],
            },
            "output_schema": {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name", "email"],
            },
        }
        response = await client.post("/api/v1/interface-masters", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "interface_id" in data
        assert data["name"] == "Valid Schema Interface"

    @pytest.mark.asyncio
    async def test_update_interface_master_invalid_input_schema(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test updating interface with invalid input schema (Phase 1.1)."""
        # Create valid interface first
        interface = InterfaceMaster(
            id="if_update_invalid_input",
            name="Original Interface",
            description="To be updated with invalid schema",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            is_active=True,
        )
        db_session.add(interface)
        await db_session.commit()

        # Try to update with invalid input schema
        update_payload = {
            "input_schema": {
                "type": "array",
                "items": "not_an_object",  # Should be a schema object
            }
        }
        response = await client.put(
            "/api/v1/interface-masters/if_update_invalid_input", json=update_payload
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid input_schema" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_interface_master_invalid_output_schema(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test updating interface with invalid output schema (Phase 1.1)."""
        # Create valid interface first
        interface = InterfaceMaster(
            id="if_update_invalid_output",
            name="Original Interface",
            description="To be updated with invalid output schema",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            is_active=True,
        )
        db_session.add(interface)
        await db_session.commit()

        # Try to update with invalid output schema
        update_payload = {
            "output_schema": {
                "type": "object",
                "properties": {"result": {"type": "unknown_type"}},  # Invalid type
            }
        }
        response = await client.put(
            "/api/v1/interface-masters/if_update_invalid_output", json=update_payload
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid output_schema" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_interface_master_valid_schemas(
        self, client: AsyncClient, db_session
    ) -> None:
        """Test updating interface with valid schemas (Phase 1.1)."""
        # Create interface first
        interface = InterfaceMaster(
            id="if_update_valid",
            name="Original Interface",
            description="Original description",
            input_schema={"type": "object", "properties": {"id": {"type": "string"}}},
            output_schema={"type": "object", "properties": {}},
            is_active=True,
        )
        db_session.add(interface)
        await db_session.commit()

        # Update with valid new schemas
        update_payload = {
            "name": "Updated Interface",
            "input_schema": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "delete"],
                    },
                },
                "required": ["user_id", "action"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "result": {"type": "object"},
                },
                "required": ["success"],
            },
        }
        response = await client.put(
            "/api/v1/interface-masters/if_update_valid", json=update_payload
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Interface"

    @pytest.mark.asyncio
    async def test_create_interface_master_without_schemas(
        self, client: AsyncClient
    ) -> None:
        """Test creating interface without schemas is allowed (Phase 1.1)."""
        payload = {
            "name": "No Schema Interface",
            "description": "Interface without input/output schemas",
        }
        response = await client.post("/api/v1/interface-masters", json=payload)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "interface_id" in data
        assert data["name"] == "No Schema Interface"
