"""Unit tests for merge utilities."""

from app.core.merge import merge_dict_deep, merge_dict_shallow, merge_tags


class TestMergeDictShallow:
    """Tests for merge_dict_shallow function."""

    def test_merge_both_none(self) -> None:
        """Test merging when both dictionaries are None."""
        result = merge_dict_shallow(None, None)
        assert result is None

    def test_merge_base_none(self) -> None:
        """Test merging when base is None."""
        result = merge_dict_shallow(None, {"a": 1})
        assert result == {"a": 1}

    def test_merge_override_none(self) -> None:
        """Test merging when override is None."""
        result = merge_dict_shallow({"a": 1}, None)
        assert result == {"a": 1}

    def test_merge_empty_dicts(self) -> None:
        """Test merging empty dictionaries."""
        result = merge_dict_shallow({}, {})
        assert result is None

    def test_merge_base_empty_override_nonempty(self) -> None:
        """Test merging when base is empty and override is not."""
        result = merge_dict_shallow({}, {"a": 1})
        assert result == {"a": 1}

    def test_merge_base_nonempty_override_empty(self) -> None:
        """Test merging when base is not empty and override is."""
        result = merge_dict_shallow({"a": 1}, {})
        assert result == {"a": 1}

    def test_merge_no_overlap(self) -> None:
        """Test merging when keys don't overlap."""
        result = merge_dict_shallow({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_with_override(self) -> None:
        """Test merging with overlapping keys (override wins)."""
        result = merge_dict_shallow({"a": 1, "b": 2}, {"a": 99, "c": 3})
        assert result == {"a": 99, "b": 2, "c": 3}

    def test_merge_headers_example(self) -> None:
        """Test realistic header merging scenario."""
        base = {"Authorization": "Bearer token1", "Content-Type": "application/json"}
        override = {"Authorization": "Bearer token2", "X-Custom": "value"}
        result = merge_dict_shallow(base, override)
        assert result == {
            "Authorization": "Bearer token2",
            "Content-Type": "application/json",
            "X-Custom": "value",
        }


class TestMergeDictDeep:
    """Tests for merge_dict_deep function."""

    def test_merge_both_none(self) -> None:
        """Test merging when both dictionaries are None."""
        result = merge_dict_deep(None, None)
        assert result is None

    def test_merge_base_none(self) -> None:
        """Test merging when base is None."""
        result = merge_dict_deep(None, {"a": 1})
        assert result == {"a": 1}

    def test_merge_override_none(self) -> None:
        """Test merging when override is None."""
        result = merge_dict_deep({"a": 1}, None)
        assert result == {"a": 1}

    def test_merge_no_overlap(self) -> None:
        """Test merging when keys don't overlap."""
        result = merge_dict_deep({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_with_override(self) -> None:
        """Test merging with overlapping keys (override wins)."""
        result = merge_dict_deep({"a": 1, "b": 2}, {"a": 99, "c": 3})
        assert result == {"a": 99, "b": 2, "c": 3}

    def test_merge_nested_dicts(self) -> None:
        """Test deep merge with nested dictionaries."""
        base = {"user": {"name": "Alice", "age": 30}, "settings": {"theme": "dark"}}
        override = {"user": {"age": 31}, "settings": {"lang": "ja"}}
        result = merge_dict_deep(base, override)
        assert result == {
            "user": {"name": "Alice", "age": 31},
            "settings": {"theme": "dark", "lang": "ja"},
        }

    def test_merge_deeply_nested(self) -> None:
        """Test deep merge with deeply nested dictionaries."""
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"d": 99, "e": 3}}}
        result = merge_dict_deep(base, override)
        assert result == {"a": {"b": {"c": 1, "d": 99, "e": 3}}}

    def test_merge_array_replacement(self) -> None:
        """Test that arrays are replaced, not merged."""
        base = {"data": [1, 2, 3]}
        override = {"data": [4, 5]}
        result = merge_dict_deep(base, override)
        assert result == {"data": [4, 5]}

    def test_merge_dict_replaces_non_dict(self) -> None:
        """Test that dict replaces non-dict value."""
        base = {"a": 1}
        override = {"a": {"b": 2}}
        result = merge_dict_deep(base, override)
        assert result == {"a": {"b": 2}}

    def test_merge_non_dict_replaces_dict(self) -> None:
        """Test that non-dict replaces dict value."""
        base = {"a": {"b": 1}}
        override = {"a": 2}
        result = merge_dict_deep(base, override)
        assert result == {"a": 2}

    def test_merge_complex_body(self) -> None:
        """Test realistic request body merging scenario."""
        base = {
            "user": {"name": "Alice", "age": 30, "settings": {"theme": "dark"}},
            "data": [1, 2, 3],
            "metadata": {"version": "1.0"},
        }
        override = {
            "user": {"age": 31, "settings": {"lang": "ja"}},
            "data": [4, 5],
        }
        result = merge_dict_deep(base, override)
        assert result == {
            "user": {
                "name": "Alice",
                "age": 31,
                "settings": {"theme": "dark", "lang": "ja"},
            },
            "data": [4, 5],
            "metadata": {"version": "1.0"},
        }


class TestMergeTags:
    """Tests for merge_tags function."""

    def test_merge_both_none(self) -> None:
        """Test merging when both tag lists are None."""
        result = merge_tags(None, None)
        assert result is None

    def test_merge_base_none(self) -> None:
        """Test merging when base is None."""
        result = merge_tags(None, ["a", "b"])
        assert result == ["a", "b"]

    def test_merge_override_none(self) -> None:
        """Test merging when override is None."""
        result = merge_tags(["a", "b"], None)
        assert result == ["a", "b"]

    def test_merge_empty_lists(self) -> None:
        """Test merging empty lists."""
        result = merge_tags([], [])
        assert result is None

    def test_merge_base_empty_override_nonempty(self) -> None:
        """Test merging when base is empty and override is not."""
        result = merge_tags([], ["a", "b"])
        assert result == ["a", "b"]

    def test_merge_no_overlap(self) -> None:
        """Test merging when tags don't overlap."""
        result = merge_tags(["a", "b"], ["c", "d"])
        assert result == ["a", "b", "c", "d"]

    def test_merge_with_duplicates(self) -> None:
        """Test merging with duplicate tags (deduplication)."""
        result = merge_tags(["a", "b", "c"], ["b", "c", "d"])
        assert result == ["a", "b", "c", "d"]

    def test_merge_unsorted_input(self) -> None:
        """Test that result is sorted."""
        result = merge_tags(["z", "a"], ["m", "b"])
        assert result == ["a", "b", "m", "z"]

    def test_merge_single_duplicate(self) -> None:
        """Test merging with same tags in both lists."""
        result = merge_tags(["tag1"], ["tag1"])
        assert result == ["tag1"]

    def test_merge_realistic_scenario(self) -> None:
        """Test realistic tag merging scenario."""
        base = ["webhook", "notification", "prod"]
        override = ["urgent", "notification"]
        result = merge_tags(base, override)
        assert result == ["notification", "prod", "urgent", "webhook"]
