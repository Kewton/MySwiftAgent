"""APISchemaInjector for injecting API specifications into prompts.

Issue #342 Task 2.1: APISchemaInjector implementation.

This module loads API specifications and injects them into LLM prompts
to help the model generate correct API calls in workflows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Default path to API specs YAML
DEFAULT_SPECS_PATH = Path(__file__).parent.parent / "schemas" / "available_apis.yaml"


class APISchemaInjector:
    """Injector that adds API specifications to prompts.

    Loads API specifications from YAML and provides methods to:
    - Get individual API specs
    - Inject specs into prompts
    - Format specs as markdown
    """

    def __init__(self, specs_path: str | Path | None = None):
        """Initialize with API specifications.

        Args:
            specs_path: Path to YAML file with API specs.
                       Defaults to schemas/available_apis.yaml
        """
        self.specs_path = Path(specs_path) if specs_path else DEFAULT_SPECS_PATH
        self.specs = self._load_specs()

    def _load_specs(self) -> dict[str, dict[str, Any]]:
        """Load API specifications from YAML file.

        Returns:
            Dictionary mapping API paths to their specifications
        """
        if not self.specs_path.exists():
            # Return default specs if file doesn't exist
            return self._get_default_specs()

        try:
            with open(self.specs_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return self._normalize_specs(data)
        except (yaml.YAMLError, OSError):
            return self._get_default_specs()

    def _normalize_specs(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Normalize loaded specs into consistent format.

        Args:
            data: Raw YAML data

        Returns:
            Normalized specs dictionary
        """
        specs = {}

        # Handle different YAML structures
        apis = data.get("apis", data.get("endpoints", data))

        if isinstance(apis, list):
            for api in apis:
                path = api.get("path", api.get("endpoint", ""))
                if path:
                    specs[path] = api
        elif isinstance(apis, dict):
            specs = apis

        return specs

    def _get_default_specs(self) -> dict[str, dict[str, Any]]:
        """Get default API specifications.

        Returns:
            Dictionary with hardcoded API specs for utility endpoints
        """
        return {
            "/utility/google_search": {
                "path": "/utility/google_search",
                "endpoint": "/utility/google_search",
                "method": "POST",
                "description": "Google検索を実行し結果を返す",
                "request_schema": {
                    "queries": {
                        "type": "array",
                        "items": "string",
                        "description": "検索クエリの配列",
                        "required": True,
                    },
                    "num": {
                        "type": "integer",
                        "max": 3,
                        "default": 3,
                        "description": "結果件数（タイムアウト防止のため最大3）",
                    },
                },
                "response_schema": {
                    "search_results": {
                        "type": "array",
                        "description": "検索結果の配列",
                    },
                    "search_results_count": {
                        "type": "integer",
                        "description": "結果件数",
                    },
                    "status": {
                        "type": "string",
                        "description": "ステータス",
                    },
                },
            },
            "/utility/json_stringify": {
                "path": "/utility/json_stringify",
                "endpoint": "/utility/json_stringify",
                "method": "POST",
                "description": "任意のデータをJSON文字列に変換",
                "request_schema": {
                    "data": {
                        "type": "any",
                        "description": "JSONシリアライズ可能な任意のデータ",
                        "required": True,
                    },
                },
                "response_schema": {
                    "json_string": {
                        "type": "string",
                        "description": "JSON文字列化されたデータ",
                    },
                },
            },
            "/utility/fetch_web_content": {
                "path": "/utility/fetch_web_content",
                "endpoint": "/utility/fetch_web_content",
                "method": "POST",
                "description": "WebページのコンテンツをMarkdown形式で取得",
                "request_schema": {
                    "url": {
                        "type": "string",
                        "description": "取得するURL",
                        "required": True,
                    },
                    "upload_to_drive": {
                        "type": "boolean",
                        "default": False,
                        "description": "Google Driveにアップロードするか",
                    },
                },
                "response_schema": {
                    "markdown_content": {
                        "type": "string",
                        "description": "Markdown形式のコンテンツ",
                    },
                    "status": {
                        "type": "string",
                        "description": "success または failed",
                    },
                    "error": {
                        "type": "string",
                        "description": "エラーメッセージ（失敗時）",
                    },
                },
            },
            "/utility/extract_article_urls": {
                "path": "/utility/extract_article_urls",
                "endpoint": "/utility/extract_article_urls",
                "method": "POST",
                "description": "検索結果から記事URLを抽出",
                "request_schema": {
                    "search_results": {
                        "type": "array",
                        "description": "Google検索の結果配列",
                        "required": True,
                    },
                    "max_urls": {
                        "type": "integer",
                        "default": 2,
                        "max": 5,
                        "description": "抽出する最大URL数",
                    },
                },
                "response_schema": {
                    "article_url_1": {
                        "type": "string",
                        "description": "1番目の記事URL",
                    },
                    "article_url_2": {
                        "type": "string",
                        "description": "2番目の記事URL",
                    },
                    "article_url_3": {
                        "type": "string",
                        "description": "3番目の記事URL",
                    },
                    "urls": {
                        "type": "array",
                        "description": "全URLの配列",
                    },
                    "count": {
                        "type": "integer",
                        "description": "抽出されたURL数",
                    },
                },
            },
            "/aiagent/utility/jsonoutput": {
                "path": "/aiagent/utility/jsonoutput",
                "endpoint": "/aiagent/utility/jsonoutput",
                "method": "POST",
                "description": "LLMを使用してJSON出力を生成",
                "request_schema": {
                    "user_input": {
                        "type": "string",
                        "description": "プロンプト文字列（string型のみ）",
                        "required": True,
                    },
                    "model_name": {
                        "type": "string",
                        "default": "gemini-2.0-flash",
                        "description": "使用するLLMモデル",
                    },
                    "force_json": {
                        "type": "boolean",
                        "default": True,
                        "description": "JSON形式を強制するか",
                    },
                },
                "response_schema": {
                    "result": {
                        "type": "object",
                        "description": "LLMの出力結果",
                    },
                },
            },
        }

    def get_spec(self, api_path: str) -> dict[str, Any] | None:
        """Get specification for a single API.

        Args:
            api_path: API path like "/utility/google_search"

        Returns:
            API specification dictionary or None if not found
        """
        # Try exact match first
        if api_path in self.specs:
            return self.specs[api_path]

        # Try with/without leading slash
        alt_path = api_path.lstrip("/") if api_path.startswith("/") else f"/{api_path}"
        if alt_path in self.specs:
            return self.specs[alt_path]

        return None

    def inject(
        self,
        prompt: str,
        required_apis: list[str],
    ) -> str:
        """Inject API specifications into a prompt.

        Args:
            prompt: Original prompt text
            required_apis: List of API paths to include

        Returns:
            Enhanced prompt with API specifications
        """
        api_docs: list[str] = []

        for api_path in required_apis:
            spec = self.get_spec(api_path)
            if spec:
                api_docs.append(self.format_to_markdown(spec))

        if not api_docs:
            return prompt

        api_section = "\n\n## 利用可能なAPI仕様\n\n" + "\n\n".join(api_docs)
        return prompt + api_section

    def format_to_markdown(self, spec: dict[str, Any]) -> str:
        """Format API specification as markdown.

        Args:
            spec: API specification dictionary

        Returns:
            Markdown formatted string
        """
        lines: list[str] = []

        path = spec.get("path", spec.get("endpoint", "Unknown"))
        method = spec.get("method", "POST")
        description = spec.get("description", "")

        lines.append(f"### {method} {path}")
        if description:
            lines.append(f"\n{description}\n")

        # Request schema
        request_schema = spec.get("request_schema", spec.get("request", {}))
        if request_schema:
            lines.append("\n**Request Parameters:**")
            lines.append("```")
            for param, param_spec in request_schema.items():
                if isinstance(param_spec, dict):
                    ptype = param_spec.get("type", "any")
                    required = param_spec.get("required", False)
                    default = param_spec.get("default")
                    desc = param_spec.get("description", "")
                    max_val = param_spec.get("max")

                    req_str = " (required)" if required else ""
                    default_str = f", default={default}" if default is not None else ""
                    max_str = f", max={max_val}" if max_val is not None else ""

                    lines.append(f"  {param}: {ptype}{req_str}{default_str}{max_str}")
                    if desc:
                        lines.append(f"    # {desc}")
                else:
                    lines.append(f"  {param}: {param_spec}")
            lines.append("```")

        # Response schema
        response_schema = spec.get("response_schema", spec.get("response", {}))
        if response_schema:
            lines.append("\n**Response Fields:**")
            lines.append("```")
            for field, field_spec in response_schema.items():
                if isinstance(field_spec, dict):
                    ftype = field_spec.get("type", "any")
                    desc = field_spec.get("description", "")
                    lines.append(f"  {field}: {ftype}")
                    if desc:
                        lines.append(f"    # {desc}")
                else:
                    lines.append(f"  {field}: {field_spec}")
            lines.append("```")

        return "\n".join(lines)

    def get_all_api_paths(self) -> list[str]:
        """Get all available API paths.

        Returns:
            List of API path strings
        """
        return list(self.specs.keys())


# Export
__all__ = ["APISchemaInjector"]
