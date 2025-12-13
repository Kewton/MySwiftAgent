"""Unit tests for Job Configuration interface service - Issue #277.

Tests for interface display functionality:
- Interface fetch functions (get_interface_info, get_cached_interface)
- Task interface info rendering (render_task_interface_info)
- Interface schema expander rendering (render_interface_schema_expander)
"""

from unittest.mock import MagicMock, Mock, patch


class TestGetInterfaceInfo:
    """Test cases for get_interface_info function."""

    @patch("components.interface_service.HTTPClient")
    @patch("components.interface_service.config")
    def test_get_interface_info_success(
        self,
        mock_config: Mock,
        mock_http_client_class: Mock,
    ) -> None:
        """Test successful interface fetch from API."""
        from components.interface_service import get_interface_info

        # Setup mocks
        mock_api_config = Mock()
        mock_config.get_api_config.return_value = mock_api_config

        mock_client = Mock()
        mock_http_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_http_client_class.return_value.__exit__ = Mock(return_value=False)

        expected_interface = {
            "id": "if_01ABC",
            "name": "Test Interface",
            "input_schema": {"type": "object", "properties": {}},
        }
        mock_client.get.return_value = expected_interface

        # Call function
        result = get_interface_info("if_01ABC")

        # Verify
        assert result == expected_interface
        mock_config.get_api_config.assert_called_once_with("JobQueue")
        mock_client.get.assert_called_once_with(
            "/api/v1/interface-masters/if_01ABC",
        )

    @patch("components.interface_service.HTTPClient")
    @patch("components.interface_service.config")
    def test_get_interface_info_not_found(
        self,
        mock_config: Mock,
        mock_http_client_class: Mock,
    ) -> None:
        """Test interface fetch returns None for 404 error."""
        from components.interface_service import get_interface_info
        from core.exceptions import APIError

        # Setup mocks
        mock_api_config = Mock()
        mock_config.get_api_config.return_value = mock_api_config

        mock_client = Mock()
        mock_http_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_http_client_class.return_value.__exit__ = Mock(return_value=False)

        mock_client.get.side_effect = APIError("Not Found", status_code=404)

        # Call function
        result = get_interface_info("if_nonexistent")

        # Verify
        assert result is None

    @patch("components.interface_service.HTTPClient")
    @patch("components.interface_service.config")
    def test_get_interface_info_api_error(
        self,
        mock_config: Mock,
        mock_http_client_class: Mock,
    ) -> None:
        """Test interface fetch returns None for connection error."""
        from components.interface_service import get_interface_info

        # Setup mocks
        mock_api_config = Mock()
        mock_config.get_api_config.return_value = mock_api_config

        mock_client = Mock()
        mock_http_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_http_client_class.return_value.__exit__ = Mock(return_value=False)

        mock_client.get.side_effect = Exception("Connection refused")

        # Call function
        result = get_interface_info("if_01ABC")

        # Verify
        assert result is None

    @patch("components.interface_service.HTTPClient")
    @patch("components.interface_service.config")
    def test_get_interface_info_api_error_non_404(
        self,
        mock_config: Mock,
        mock_http_client_class: Mock,
    ) -> None:
        """Test interface fetch returns None for non-404 API error."""
        from components.interface_service import get_interface_info
        from core.exceptions import APIError

        # Setup mocks
        mock_api_config = Mock()
        mock_config.get_api_config.return_value = mock_api_config

        mock_client = Mock()
        mock_http_client_class.return_value.__enter__ = Mock(return_value=mock_client)
        mock_http_client_class.return_value.__exit__ = Mock(return_value=False)

        mock_client.get.side_effect = APIError("Server Error", status_code=500)

        # Call function
        result = get_interface_info("if_01ABC")

        # Verify
        assert result is None


class TestGetCachedInterface:
    """Test cases for get_cached_interface function."""

    @patch("components.interface_service.st")
    def test_get_cached_interface_cache_hit(self, mock_st: Mock) -> None:
        """Test returning cached interface without API call."""
        from components.interface_service import get_cached_interface

        # Setup cache with existing interface
        cached_interface = {
            "id": "if_01ABC",
            "name": "Cached Interface",
            "input_schema": {"type": "object"},
        }
        mock_st.session_state = MagicMock()
        mock_st.session_state.interface_cache = {"if_01ABC": cached_interface}

        # Call function
        result = get_cached_interface("if_01ABC")

        # Verify - should return cached value without API call
        assert result == cached_interface

    @patch("components.interface_service.get_interface_info")
    @patch("components.interface_service.st")
    def test_get_cached_interface_cache_miss(
        self,
        mock_st: Mock,
        mock_get_interface_info: Mock,
    ) -> None:
        """Test fetching interface on cache miss and storing in cache."""
        from components.interface_service import get_cached_interface

        # Setup empty cache
        mock_st.session_state = MagicMock()
        mock_st.session_state.interface_cache = {}

        fetched_interface = {
            "id": "if_01XYZ",
            "name": "Fetched Interface",
            "input_schema": {"type": "object"},
        }
        mock_get_interface_info.return_value = fetched_interface

        # Call function
        result = get_cached_interface("if_01XYZ")

        # Verify
        assert result == fetched_interface
        mock_get_interface_info.assert_called_once_with("if_01XYZ")
        # Verify it was added to cache
        assert mock_st.session_state.interface_cache["if_01XYZ"] == fetched_interface

    @patch("components.interface_service.get_interface_info")
    @patch("components.interface_service.st")
    def test_get_cached_interface_none_id(
        self,
        mock_st: Mock,
        mock_get_interface_info: Mock,
    ) -> None:
        """Test returning None for None interface_id."""
        from components.interface_service import get_cached_interface

        mock_st.session_state = MagicMock()
        mock_st.session_state.interface_cache = {}

        # Call function
        result = get_cached_interface(None)

        # Verify
        assert result is None
        mock_get_interface_info.assert_not_called()

    @patch("components.interface_service.get_interface_info")
    @patch("components.interface_service.st")
    def test_get_cached_interface_initializes_cache(
        self,
        mock_st: Mock,
        mock_get_interface_info: Mock,
    ) -> None:
        """Test that cache is initialized if not present."""
        from components.interface_service import get_cached_interface

        # Setup session_state without interface_cache
        mock_st.session_state = MagicMock(spec=[])

        fetched_interface = {"id": "if_01ABC", "name": "Test"}
        mock_get_interface_info.return_value = fetched_interface

        # Call function
        result = get_cached_interface("if_01ABC")

        # Verify
        assert result == fetched_interface


class TestGetInterfaceName:
    """Test cases for get_interface_name function."""

    @patch("components.interface_service.get_cached_interface")
    def test_get_interface_name_with_interface(
        self,
        mock_get_cached_interface: Mock,
    ) -> None:
        """Test getting interface name when interface exists."""
        from components.interface_service import get_interface_name

        mock_get_cached_interface.return_value = {
            "id": "if_01ABC",
            "name": "My Interface",
        }

        result = get_interface_name("if_01ABC")

        assert result == "My Interface"

    @patch("components.interface_service.get_cached_interface")
    def test_get_interface_name_none_id(
        self,
        mock_get_cached_interface: Mock,
    ) -> None:
        """Test getting interface name for None ID."""
        from components.interface_service import get_interface_name

        result = get_interface_name(None)

        assert result == "Not Set"
        mock_get_cached_interface.assert_not_called()

    @patch("components.interface_service.get_cached_interface")
    def test_get_interface_name_not_found(
        self,
        mock_get_cached_interface: Mock,
    ) -> None:
        """Test getting interface name when interface not found."""
        from components.interface_service import get_interface_name

        mock_get_cached_interface.return_value = None

        result = get_interface_name("if_01ABC123")

        assert "Unknown" in result
        assert "if_01ABC" in result

    @patch("components.interface_service.get_cached_interface")
    def test_get_interface_name_unnamed(
        self,
        mock_get_cached_interface: Mock,
    ) -> None:
        """Test getting interface name when interface has no name."""
        from components.interface_service import get_interface_name

        mock_get_cached_interface.return_value = {"id": "if_01ABC123"}

        result = get_interface_name("if_01ABC123")

        assert "Unnamed" in result


class TestRenderTaskInterfaceInfo:
    """Test cases for render_task_interface_info function."""

    @patch("components.interface_service.render_interface_schema_expander")
    @patch("components.interface_service.get_cached_interface")
    @patch("components.interface_service.st")
    def test_render_task_interface_info_with_interfaces(
        self,
        mock_st: Mock,
        mock_get_cached_interface: Mock,
        mock_render_expander: Mock,
    ) -> None:
        """Test rendering when both input and output interfaces are set."""
        from components.interface_service import render_task_interface_info

        # Setup task with both interfaces
        task = {
            "id": "tm_01ABC",
            "name": "Test Task",
            "input_interface_id": "if_input",
            "output_interface_id": "if_output",
        }

        input_interface = {"id": "if_input", "name": "Input Interface"}
        output_interface = {"id": "if_output", "name": "Output Interface"}

        mock_get_cached_interface.side_effect = lambda x: {
            "if_input": input_interface,
            "if_output": output_interface,
        }.get(x)

        # Setup columns mock
        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=False)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=False)

        # Call function
        render_task_interface_info(task)

        # Verify st.markdown called for header
        mock_st.markdown.assert_called()
        # Verify expander rendering called for both interfaces
        assert mock_render_expander.call_count == 2

    @patch("components.interface_service.render_interface_schema_expander")
    @patch("components.interface_service.get_cached_interface")
    @patch("components.interface_service.st")
    def test_render_task_interface_info_input_only(
        self,
        mock_st: Mock,
        mock_get_cached_interface: Mock,
        mock_render_expander: Mock,
    ) -> None:
        """Test rendering when only input interface is set."""
        from components.interface_service import render_task_interface_info

        task = {
            "id": "tm_01ABC",
            "name": "Test Task",
            "input_interface_id": "if_input",
            "output_interface_id": None,
        }

        input_interface = {"id": "if_input", "name": "Input Interface"}
        mock_get_cached_interface.side_effect = lambda x: (
            input_interface if x == "if_input" else None
        )

        # Setup columns mock
        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=False)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=False)

        # Call function
        render_task_interface_info(task)

        # Verify expander called only for input
        assert mock_render_expander.call_count == 1

    @patch("components.interface_service.render_interface_schema_expander")
    @patch("components.interface_service.get_cached_interface")
    @patch("components.interface_service.st")
    def test_render_task_interface_info_output_only(
        self,
        mock_st: Mock,
        mock_get_cached_interface: Mock,
        mock_render_expander: Mock,
    ) -> None:
        """Test rendering when only output interface is set."""
        from components.interface_service import render_task_interface_info

        task = {
            "id": "tm_01ABC",
            "name": "Test Task",
            "input_interface_id": None,
            "output_interface_id": "if_output",
        }

        output_interface = {"id": "if_output", "name": "Output Interface"}
        mock_get_cached_interface.side_effect = lambda x: (
            output_interface if x == "if_output" else None
        )

        # Setup columns mock
        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=False)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=False)

        # Call function
        render_task_interface_info(task)

        # Verify expander called only for output
        assert mock_render_expander.call_count == 1

    @patch("components.interface_service.render_interface_schema_expander")
    @patch("components.interface_service.get_cached_interface")
    @patch("components.interface_service.st")
    def test_render_task_interface_info_none(
        self,
        mock_st: Mock,
        mock_get_cached_interface: Mock,
        mock_render_expander: Mock,
    ) -> None:
        """Test rendering when both interfaces are not set."""
        from components.interface_service import render_task_interface_info

        task = {
            "id": "tm_01ABC",
            "name": "Test Task",
            "input_interface_id": None,
            "output_interface_id": None,
        }

        mock_get_cached_interface.return_value = None

        # Setup columns mock
        mock_col1, mock_col2 = MagicMock(), MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]
        mock_col1.__enter__ = Mock(return_value=mock_col1)
        mock_col1.__exit__ = Mock(return_value=False)
        mock_col2.__enter__ = Mock(return_value=mock_col2)
        mock_col2.__exit__ = Mock(return_value=False)

        # Call function
        render_task_interface_info(task)

        # Verify expander not called
        mock_render_expander.assert_not_called()


class TestRenderInterfaceSchemaExpander:
    """Test cases for render_interface_schema_expander function."""

    @patch("components.interface_service.st")
    def test_render_interface_schema_expander_with_properties(
        self,
        mock_st: Mock,
    ) -> None:
        """Test rendering expander with JSON schema properties."""
        from components.interface_service import render_interface_schema_expander

        interface = {
            "id": "if_01ABC",
            "name": "Test Interface",
            "input_schema": {
                "type": "object",
                "properties": {
                    "field1": {"type": "string", "description": "Field 1"},
                    "field2": {"type": "integer"},
                },
                "required": ["field1"],
            },
        }

        # Setup expander mock
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = Mock(return_value=False)

        # Call function
        render_interface_schema_expander(interface, "Input Interface", "input_schema")

        # Verify expander was created
        mock_st.expander.assert_called_once()
        # Verify markdown and code were called for schema display
        assert mock_st.markdown.called or mock_st.code.called

    @patch("components.interface_service.st")
    def test_render_interface_schema_expander_empty_schema(
        self,
        mock_st: Mock,
    ) -> None:
        """Test rendering expander with empty JSON schema."""
        from components.interface_service import render_interface_schema_expander

        interface = {
            "id": "if_01ABC",
            "name": "Test Interface",
            "input_schema": {},
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = Mock(return_value=False)

        # Call function
        render_interface_schema_expander(interface, "Test Interface", "input_schema")

        # Verify expander was still created
        mock_st.expander.assert_called_once()
        # Verify info message shown for empty schema
        mock_st.info.assert_called_once()

    @patch("components.interface_service.st")
    def test_render_interface_schema_expander_no_schema(
        self,
        mock_st: Mock,
    ) -> None:
        """Test rendering expander when schema key is not present."""
        from components.interface_service import render_interface_schema_expander

        interface = {
            "id": "if_01ABC",
            "name": "Test Interface",
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = Mock(return_value=False)

        # Call function
        render_interface_schema_expander(interface, "Test Interface", "input_schema")

        # Verify expander was created
        mock_st.expander.assert_called_once()
        # Verify info message shown for no schema
        mock_st.info.assert_called_once()

    @patch("components.interface_service.st")
    def test_render_interface_schema_expander_with_description(
        self,
        mock_st: Mock,
    ) -> None:
        """Test rendering expander with property descriptions."""
        from components.interface_service import render_interface_schema_expander

        interface = {
            "id": "if_01ABC",
            "name": "Test Interface",
            "input_schema": {
                "type": "object",
                "properties": {
                    "field1": {
                        "type": "string",
                        "description": "This is field 1 description",
                    },
                },
                "required": [],
            },
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = Mock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = Mock(return_value=False)

        # Call function
        render_interface_schema_expander(interface, "Test Interface", "input_schema")

        # Verify caption was called for description
        mock_st.caption.assert_called()


class TestRenderInterfaceSchemaExpanderStNone:
    """Test cases for render functions when st is None."""

    def test_render_interface_schema_expander_st_none(self) -> None:
        """Test render_interface_schema_expander returns early when st is None."""
        import components.interface_service as service

        original_st = service.st
        try:
            service.st = None  # type: ignore[assignment]
            # Should not raise any errors
            service.render_interface_schema_expander({"id": "test"}, "Title")
        finally:
            service.st = original_st

    def test_render_task_interface_info_st_none(self) -> None:
        """Test render_task_interface_info returns early when st is None."""
        import components.interface_service as service

        original_st = service.st
        try:
            service.st = None  # type: ignore[assignment]
            # Should not raise any errors
            service.render_task_interface_info({"id": "test"})
        finally:
            service.st = original_st
