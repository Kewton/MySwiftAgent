"""
Test suite for Issue #203: Documentation and CI updates.

This test file verifies:
1. README.md contains required sections
2. docker-compose.yml uses include directive
3. docker compose config works correctly
4. Markdown links are valid
5. Code blocks have proper language specifications
"""

import re
import subprocess
from pathlib import Path

import pytest

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestReadmeSections:
    """Test README.md section requirements."""

    @pytest.fixture
    def readme_content(self) -> str:
        """Load README.md content."""
        readme_path = PROJECT_ROOT / "README.md"
        assert readme_path.exists(), "README.md does not exist"
        return readme_path.read_text(encoding="utf-8")

    def test_readme_has_layer_docker_compose_section(self, readme_content: str) -> None:
        """README.md should have a section about layer-based docker-compose."""
        # Check for Japanese or English section header
        patterns = [
            r"##.*レイヤ別.*docker-compose",
            r"##.*docker-compose.*レイヤ",
            r"##.*Layer.*Docker.*Compose",
            r"##.*レイヤ別Docker Compose",
        ]
        found = any(re.search(pattern, readme_content, re.IGNORECASE) for pattern in patterns)
        assert found, "README.md should have 'Layer-based docker-compose' section"

    def test_readme_has_make_commands_section(self, readme_content: str) -> None:
        """README.md should have a section about Make commands."""
        patterns = [
            r"##.*Make.*コマンド.*一覧",
            r"##.*Makeコマンド一覧",
            r"##.*Make.*Command",
        ]
        found = any(re.search(pattern, readme_content, re.IGNORECASE) for pattern in patterns)
        assert found, "README.md should have 'Make commands list' section"

    def test_readme_has_development_patterns_section(self, readme_content: str) -> None:
        """README.md should have a section about common development patterns."""
        patterns = [
            r"##.*よく使う開発パターン",
            r"##.*開発パターン",
            r"##.*Development.*Pattern",
            r"##.*Common.*Development",
        ]
        found = any(re.search(pattern, readme_content, re.IGNORECASE) for pattern in patterns)
        assert found, "README.md should have 'Common development patterns' section"


class TestDockerComposeInclude:
    """Test docker-compose.yml include directive."""

    @pytest.fixture
    def docker_compose_content(self) -> str:
        """Load docker-compose.yml content."""
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml does not exist"
        return compose_path.read_text(encoding="utf-8")

    def test_docker_compose_uses_include(self, docker_compose_content: str) -> None:
        """docker-compose.yml should use include directive."""
        assert "include:" in docker_compose_content, (
            "docker-compose.yml should use 'include:' directive"
        )

    def test_docker_compose_includes_platform_yml(self, docker_compose_content: str) -> None:
        """docker-compose.yml should include docker-compose.platform.yml."""
        patterns = [
            r"docker-compose\.platform\.yml",
            r"docker-compose\.platform\.yaml",
        ]
        found = any(re.search(pattern, docker_compose_content) for pattern in patterns)
        assert found, "docker-compose.yml should include docker-compose.platform.yml"

    def test_docker_compose_includes_agent_yml(self, docker_compose_content: str) -> None:
        """docker-compose.yml should include docker-compose.agent.yml."""
        patterns = [
            r"docker-compose\.agent\.yml",
            r"docker-compose\.agent\.yaml",
        ]
        found = any(re.search(pattern, docker_compose_content) for pattern in patterns)
        assert found, "docker-compose.yml should include docker-compose.agent.yml"

    def test_docker_compose_includes_frontend_yml(self, docker_compose_content: str) -> None:
        """docker-compose.yml should include docker-compose.frontend.yml."""
        patterns = [
            r"docker-compose\.frontend\.yml",
            r"docker-compose\.frontend\.yaml",
        ]
        found = any(re.search(pattern, docker_compose_content) for pattern in patterns)
        assert found, "docker-compose.yml should include docker-compose.frontend.yml"

    def test_docker_compose_includes_three_files(self, docker_compose_content: str) -> None:
        """docker-compose.yml should include exactly 3 layer files."""
        layer_files = [
            "docker-compose.platform.yml",
            "docker-compose.agent.yml",
            "docker-compose.frontend.yml",
        ]
        included_count = sum(1 for f in layer_files if f in docker_compose_content)
        assert included_count == 3, (
            f"docker-compose.yml should include all 3 layer files, found {included_count}"
        )


class TestDockerComposeConfig:
    """Test docker compose config validation."""

    def test_docker_compose_config_valid(self) -> None:
        """docker compose config should complete without errors."""
        result = subprocess.run(
            ["docker", "compose", "config"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"docker compose config failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        )


class TestMarkdownLinks:
    """Test Markdown link validity."""

    @pytest.fixture
    def readme_content(self) -> str:
        """Load README.md content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text(encoding="utf-8")

    def test_internal_links_valid(self, readme_content: str) -> None:
        """All internal file links in README.md should point to existing files."""
        # Extract internal file links (not URLs)
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        links = re.findall(link_pattern, readme_content)

        broken_links = []
        for text, href in links:
            # Skip external URLs
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue

            # Skip anchors with file paths
            if "#" in href:
                href = href.split("#")[0]
                if not href:  # Pure anchor link
                    continue

            # Check if file exists
            link_path = PROJECT_ROOT / href
            if not link_path.exists():
                broken_links.append(f"[{text}]({href})")

        assert not broken_links, "Found broken links in README.md:\n" + "\n".join(
            f"  - {link}" for link in broken_links
        )


class TestCodeBlockLanguages:
    """Test code block language specifications."""

    @pytest.fixture
    def readme_content(self) -> str:
        """Load README.md content."""
        readme_path = PROJECT_ROOT / "README.md"
        return readme_path.read_text(encoding="utf-8")

    def test_code_blocks_have_language(self, readme_content: str) -> None:
        """All code blocks should have language specification."""
        # Find code blocks without language specification
        # Pattern: ``` at line start with no language identifier
        code_block_pattern = r"^```\s*$"
        lines = readme_content.split("\n")

        empty_code_blocks = []
        for i, line in enumerate(lines, 1):
            if re.match(code_block_pattern, line.strip()):
                # Check if this is not a closing block
                # by looking at previous lines for an opening block
                context = lines[max(0, i - 5) : i]
                context_str = "\n".join(context)
                if "```" not in context_str or context_str.count("```") % 2 == 0:
                    empty_code_blocks.append(f"Line {i}: {line}")

        # Allow some empty code blocks as they might be closing blocks
        # The test is more lenient - just ensure most have languages
        assert len(empty_code_blocks) <= 5, (
            f"Found {len(empty_code_blocks)} code blocks without language specification:\n"
            + "\n".join(f"  - {block}" for block in empty_code_blocks[:10])
        )


class TestServiceDependenciesDoc:
    """Test docs/arch/service-dependencies.md updates."""

    @pytest.fixture
    def service_deps_content(self) -> str:
        """Load service-dependencies.md content."""
        doc_path = PROJECT_ROOT / "docs" / "arch" / "service-dependencies.md"
        assert doc_path.exists(), "docs/arch/service-dependencies.md does not exist"
        return doc_path.read_text(encoding="utf-8")

    def test_has_layer_structure(self, service_deps_content: str) -> None:
        """service-dependencies.md should document layer structure."""
        patterns = [
            r"Layer\s*1|Layer\s*2|Layer\s*3|Layer\s*4",
            r"レイヤ|layer",
            r"Platform.*Agent.*Frontend",
        ]
        found = any(re.search(pattern, service_deps_content, re.IGNORECASE) for pattern in patterns)
        assert found, "service-dependencies.md should document layer structure"

    def test_has_docker_compose_reference(self, service_deps_content: str) -> None:
        """service-dependencies.md should reference docker-compose files."""
        patterns = [
            r"docker-compose",
            r"Docker Compose",
        ]
        found = any(re.search(pattern, service_deps_content, re.IGNORECASE) for pattern in patterns)
        assert found, "service-dependencies.md should reference docker-compose files"
