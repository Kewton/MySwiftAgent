"""WorkflowPatternLibrary for standard workflow patterns.

Issue #342 Task 3.1: WorkflowPatternLibrary implementation.

This module provides standard workflow patterns that can be used as
templates for common use cases:
- search_and_summarize: Search and summarize results
- search_fetch_summarize: Search, fetch articles, and summarize
- api_transform_output: API call with data transformation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Default path to pattern templates
TEMPLATES_DIR = Path(__file__).parent / "templates"


class WorkflowPatternLibrary:
    """Library of standard workflow patterns.

    Provides:
    - Pattern definitions with metadata
    - Full workflow templates
    - Pattern suggestion based on requirements
    """

    def __init__(self, templates_dir: str | Path | None = None):
        """Initialize pattern library.

        Args:
            templates_dir: Directory containing pattern YAML templates.
                          Defaults to patterns/templates/
        """
        self.templates_dir = Path(templates_dir) if templates_dir else TEMPLATES_DIR
        self.patterns = self._load_patterns()
        self._templates_cache: dict[str, dict[str, Any]] = {}

    def _load_patterns(self) -> dict[str, dict[str, Any]]:
        """Load pattern definitions.

        Returns:
            Dictionary mapping pattern names to their metadata
        """
        return {
            "search_and_summarize": {
                "description": "Google検索結果を要約するワークフロー",
                "use_cases": [
                    "検索結果の要約",
                    "キーワード検索とまとめ",
                    "ニュース検索と要約",
                ],
                "nodes": [
                    "fetch_search_results",
                    "stringify_results",
                    "build_prompt",
                    "call_llm",
                ],
                "apis_used": [
                    "/utility/google_search",
                    "/utility/json_stringify",
                    "/aiagent/utility/jsonoutput",
                ],
            },
            "search_fetch_summarize": {
                "description": "検索後に記事本文を取得して要約するワークフロー",
                "use_cases": [
                    "記事の内容を要約",
                    "Webページの分析",
                    "詳細な情報収集と要約",
                ],
                "nodes": [
                    "fetch_search_results",
                    "extract_urls",
                    "fetch_content",
                    "stringify_content",
                    "build_prompt",
                    "call_llm",
                ],
                "apis_used": [
                    "/utility/google_search",
                    "/utility/extract_article_urls",
                    "/utility/fetch_web_content",
                    "/utility/json_stringify",
                    "/aiagent/utility/jsonoutput",
                ],
            },
            "api_transform_output": {
                "description": "API呼び出しとデータ変換のワークフロー",
                "use_cases": [
                    "データ変換",
                    "API連携",
                    "データパイプライン",
                ],
                "nodes": [
                    "api_call",
                    "transform",
                    "output",
                ],
                "apis_used": [],
            },
        }

    def get_pattern(self, pattern_name: str) -> dict[str, Any] | None:
        """Get pattern metadata by name.

        Args:
            pattern_name: Name of the pattern

        Returns:
            Pattern metadata dictionary or None if not found
        """
        return self.patterns.get(pattern_name)

    def list_patterns(self) -> list[str]:
        """List all available pattern names.

        Returns:
            List of pattern name strings
        """
        return list(self.patterns.keys())

    def suggest_pattern(self, requirements: str) -> str:
        """Suggest a pattern based on requirements text.

        Args:
            requirements: User requirements description

        Returns:
            Suggested pattern name
        """
        req_lower = requirements.lower()

        # Check for article/content fetch indicators
        article_keywords = [
            "記事",
            "本文",
            "コンテンツ",
            "ページ",
            "article",
            "content",
            "web",
        ]
        if any(kw in req_lower for kw in article_keywords):
            return "search_fetch_summarize"

        # Check for search + summarize
        search_keywords = ["検索", "search", "google", "調べ"]
        summarize_keywords = ["要約", "まとめ", "summarize", "summary"]

        has_search = any(kw in req_lower for kw in search_keywords)
        has_summarize = any(kw in req_lower for kw in summarize_keywords)

        if has_search and has_summarize:
            return "search_and_summarize"

        if has_search:
            return "search_and_summarize"

        # Default pattern
        return "api_transform_output"

    def get_template(self, pattern_name: str) -> dict[str, Any] | None:
        """Get full workflow template for a pattern.

        Args:
            pattern_name: Name of the pattern

        Returns:
            Workflow template dictionary or None if not found
        """
        if pattern_name in self._templates_cache:
            return self._templates_cache[pattern_name]

        # Try to load from YAML file
        template_path = self.templates_dir / f"{pattern_name}.yaml"
        if template_path.exists():
            try:
                with open(template_path, "r", encoding="utf-8") as f:
                    template: dict[str, Any] = yaml.safe_load(f)
                    self._templates_cache[pattern_name] = template
                    return template
            except (yaml.YAMLError, OSError):
                pass

        # Return hardcoded templates
        templates = self._get_default_templates()
        default_template = templates.get(pattern_name)

        if default_template:
            self._templates_cache[pattern_name] = default_template

        return default_template

    def _get_default_templates(self) -> dict[str, dict[str, Any]]:
        """Get default hardcoded templates.

        Returns:
            Dictionary mapping pattern names to workflow templates
        """
        return {
            "search_and_summarize": {
                "version": "0.5",
                "nodes": {
                    "source": {},
                    "fetch_search_results": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": "http://localhost:8004/aiagent-api/v1/utility/google_search",
                            "method": "POST",
                            "body": {
                                "queries": ":source.user_input.queries",
                                "num": 3,
                            },
                        },
                        "timeout": 30000,
                    },
                    "stringify_results": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": "http://localhost:8004/aiagent-api/v1/utility/json_stringify",
                            "method": "POST",
                            "body": {
                                "data": ":fetch_search_results.search_results",
                            },
                        },
                        "timeout": 30000,
                    },
                    "build_prompt": {
                        "agent": "stringTemplateAgent",
                        "inputs": {
                            "results": ":stringify_results.json_string",
                        },
                        "params": {
                            "template": "以下の検索結果を日本語で要約してください:\\n\\n${results}",
                        },
                    },
                    "call_llm": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": "http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput",
                            "method": "POST",
                            "body": {
                                "user_input": ":build_prompt",
                                "model_name": "gemini-2.0-flash",
                                "force_json": True,
                            },
                        },
                        "timeout": 120000,
                        "isResult": True,
                    },
                },
            },
            "search_fetch_summarize": {
                "version": "0.5",
                "nodes": {
                    "source": {},
                    "fetch_search_results": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": "http://localhost:8004/aiagent-api/v1/utility/google_search",
                            "method": "POST",
                            "body": {
                                "queries": ":source.user_input.queries",
                                "num": 2,
                            },
                        },
                        "timeout": 30000,
                    },
                    "extract_urls": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": "http://localhost:8004/aiagent-api/v1/utility/extract_article_urls",
                            "method": "POST",
                            "body": {
                                "search_results": ":fetch_search_results.search_results",
                                "max_urls": 2,
                            },
                        },
                        "timeout": 30000,
                    },
                    "fetch_content": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": "http://localhost:8004/aiagent-api/v1/utility/fetch_web_content",
                            "method": "POST",
                            "body": {
                                "url": ":extract_urls.article_url_1",
                            },
                        },
                        "timeout": 60000,
                    },
                    "stringify_content": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": "http://localhost:8004/aiagent-api/v1/utility/json_stringify",
                            "method": "POST",
                            "body": {
                                "data": ":fetch_content.markdown_content",
                            },
                        },
                        "timeout": 30000,
                    },
                    "build_prompt": {
                        "agent": "stringTemplateAgent",
                        "inputs": {
                            "content": ":stringify_content.json_string",
                        },
                        "params": {
                            "template": "以下の記事を日本語で要約してください:\\n\\n${content}",
                        },
                    },
                    "call_llm": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": "http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput",
                            "method": "POST",
                            "body": {
                                "user_input": ":build_prompt",
                                "model_name": "gemini-2.0-flash",
                                "force_json": True,
                            },
                        },
                        "timeout": 120000,
                        "isResult": True,
                    },
                },
            },
            "api_transform_output": {
                "version": "0.5",
                "nodes": {
                    "source": {},
                    "api_call": {
                        "agent": "fetchAgent",
                        "inputs": {
                            "url": ":source.user_input.api_url",
                            "method": ":source.user_input.method",
                            "body": ":source.user_input.body",
                        },
                        "timeout": 30000,
                    },
                    "transform": {
                        "agent": "stringTemplateAgent",
                        "inputs": {
                            "result": ":api_call",
                        },
                        "params": {
                            "template": "Result: ${result}",
                        },
                    },
                    "output": {
                        "agent": "copyAgent",
                        "inputs": {
                            "data": ":transform",
                        },
                        "isResult": True,
                    },
                },
            },
        }


# Export
__all__ = ["WorkflowPatternLibrary"]
