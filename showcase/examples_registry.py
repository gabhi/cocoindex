"""Reads example metadata directly from the real examples/ directory.

Single source of truth: nothing here is duplicated by hand, so the gallery
can never drift from the actual example code and READMEs.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TITLE_ATTR_RE = re.compile(r'<a\s[^>]*\btitle="([^"]+)"', re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")

EXAMPLES_ROOT = Path(__file__).resolve().parent.parent / "examples"

# Preferred entry-file names to look for, in order, before falling back to
# a recursive search for the first .py file in the example directory.
_ENTRY_CANDIDATES = ("main.py", "api.py", "app.py", "download.py")

_CODE_EXCERPT_LINES = 60


@dataclass(frozen=True)
class ExampleInfo:
    slug: str
    title: str
    description: str
    code_filename: str
    code_excerpt: str
    code_truncated: bool
    github_url: str


def _find_entry_file(example_dir: Path) -> Path | None:
    for name in _ENTRY_CANDIDATES:
        candidate = example_dir / name
        if candidate.is_file():
            return candidate
    for path in sorted(example_dir.rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "__init__.py":
            continue
        return path
    return None


def _clean_inline_html(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


def _parse_readme_html_header(readme_text: str) -> tuple[str, str] | None:
    """Most example READMEs open with a badge banner, then an <h1> title and
    an <a title="..."> attribute holding a one-line description. Handles
    that convention; returns None if the README doesn't follow it."""
    h1_match = _H1_RE.search(readme_text)
    title_match = _TITLE_ATTR_RE.search(readme_text)
    if h1_match is None or title_match is None:
        return None
    title = _clean_inline_html(h1_match.group(1))
    description = _clean_inline_html(title_match.group(1))
    if not title or not description:
        return None
    return title, description


def _parse_readme_plain_markdown(
    readme_text: str, fallback_title: str
) -> tuple[str, str]:
    title = fallback_title
    lines = readme_text.splitlines()
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped.removeprefix("# ").strip()
            body_start = i + 1
            break

    paragraph: list[str] = []
    for line in lines[body_start:]:
        stripped = line.strip()
        if not stripped:
            if paragraph:
                break
            continue
        if stripped.startswith("#") or stripped.startswith("```"):
            if paragraph:
                break
            continue
        paragraph.append(stripped)
    description = " ".join(paragraph)
    description = re.sub(r"[`*_]", "", description)
    return title, description


def _parse_readme(readme_text: str, fallback_title: str) -> tuple[str, str]:
    return _parse_readme_html_header(readme_text) or _parse_readme_plain_markdown(
        readme_text, fallback_title
    )


def _load_example(example_dir: Path) -> ExampleInfo | None:
    readme_path = example_dir / "README.md"
    if not readme_path.is_file():
        return None

    fallback_title = example_dir.name.replace("_", " ").title()
    title, description = _parse_readme(
        readme_path.read_text(encoding="utf-8"), fallback_title
    )

    entry_file = _find_entry_file(example_dir)
    code_filename = "(no code file found)"
    code_excerpt = ""
    code_truncated = False
    if entry_file is not None:
        code_filename = str(entry_file.relative_to(example_dir))
        lines = entry_file.read_text(encoding="utf-8").splitlines()
        code_truncated = len(lines) > _CODE_EXCERPT_LINES
        code_excerpt = "\n".join(lines[:_CODE_EXCERPT_LINES])

    return ExampleInfo(
        slug=example_dir.name,
        title=title,
        description=description or "See the README for details.",
        code_filename=code_filename,
        code_excerpt=code_excerpt,
        code_truncated=code_truncated,
        github_url=f"https://github.com/cocoindex-io/cocoindex/tree/main/examples/{example_dir.name}",
    )


def load_examples() -> list[ExampleInfo]:
    if not EXAMPLES_ROOT.is_dir():
        return []

    examples = []
    for child in sorted(EXAMPLES_ROOT.iterdir()):
        if not child.is_dir() or child.name in ("rust", "__pycache__"):
            continue
        info = _load_example(child)
        if info is not None:
            examples.append(info)
    return examples
