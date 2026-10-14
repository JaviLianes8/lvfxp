"""Packaging promises: pyproject metadata, README links and the version agree."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

import lvfxp

_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT = _ROOT / "pyproject.toml"
needs_tomllib = pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib is 3.11+")


def _project() -> dict[str, object]:
    if sys.version_info >= (3, 11):
        import tomllib

        data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
        project = data["project"]
        assert isinstance(project, dict)
        return project
    raise AssertionError("tomllib is 3.11+")


@needs_tomllib
def test_metadata_is_stable_and_dependency_free() -> None:
    project = _project()
    assert project["version"] == lvfxp.__version__ == "1.0.0"
    assert project["dependencies"] == []
    classifiers = project["classifiers"]
    assert isinstance(classifiers, list)
    assert "Development Status :: 5 - Production/Stable" in classifiers
    minors = [
        c for c in classifiers if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", c)
    ]
    assert [c.rsplit(".", 1)[1] for c in minors] == ["10", "11", "12", "13", "14"]
    assert project["requires-python"] == ">=3.10"
    urls = project["urls"]
    assert isinstance(urls, dict)
    assert {"Homepage", "Source", "Issues", "Changelog"} <= set(urls)


def test_readme_links_are_absolute_and_point_at_the_guide_and_changelog() -> None:
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"\]\(([^)]+)\)", readme)
    assert links and all(link.startswith("https://") for link in links)
    assert "https://github.com/JaviLianes8/lvfxp/blob/main/GUIDE.md" in links
    assert "https://github.com/JaviLianes8/lvfxp/blob/main/CHANGELOG.md" in links


def test_changelog_has_a_dated_section_for_this_version() -> None:
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(
        rf"^## \[{re.escape(lvfxp.__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.M
    )


def test_no_source_file_exceeds_two_hundred_lines() -> None:
    for path in [*(_ROOT / "src").rglob("*.py"), *(_ROOT / "tests").rglob("*.py")]:
        assert len(path.read_text(encoding="utf-8").splitlines()) <= 200, path
