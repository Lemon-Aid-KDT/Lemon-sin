"""Local Markdown WIKI retrieval for safe Ollama explanation context."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from src.config import Settings

MAX_WIKI_FILE_BYTES = 1_000_000
MAX_QUERY_TERMS = 24
MIN_QUERY_TERM_CHARS = 2
TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣_.+/-]*")
STOP_TERMS = {
    "and",
    "the",
    "with",
    "기준",
    "내용",
    "사용자",
    "설명",
    "정보",
    "섭취",
    "주의",
    "확인",
}


@dataclass(frozen=True)
class LlmWikiCitation:
    """One sanitized source citation retrieved from local Markdown WIKI.

    Attributes:
        title: Human-readable Markdown document title.
        source_path: Relative path from the configured WIKI root.
        heading: Nearest matching heading, when available.
        excerpt: Bounded excerpt used as local LLM grounding context.
        score: Deterministic lexical relevance score.
    """

    title: str
    source_path: str
    heading: str | None
    excerpt: str
    score: float


@dataclass(frozen=True)
class LlmWikiRetrievalResult:
    """Sanitized WIKI retrieval result.

    Attributes:
        query: Bounded query string derived from structured analysis fields.
        citations: Retrieved source citations.
    """

    query: str
    citations: tuple[LlmWikiCitation, ...]


def retrieve_llm_wiki_context(query: str, settings: Settings) -> LlmWikiRetrievalResult:
    """Retrieve local Markdown WIKI excerpts for Gemma 4 explanations.

    Args:
        query: Structured, sanitized text assembled by the caller.
        settings: Runtime settings with WIKI retrieval controls.

    Returns:
        Bounded citations from local Markdown files. Missing or disabled WIKI
        configuration returns an empty result instead of failing the explanation.
    """
    bounded_query = _collapse_whitespace(query)[:800]
    if (
        not settings.llm_wiki_retrieval_enabled
        or settings.llm_wiki_max_sources <= 0
        or not bounded_query
    ):
        return LlmWikiRetrievalResult(query=bounded_query, citations=())

    wiki_root = settings.llm_wiki_path
    if not wiki_root.is_dir():
        return LlmWikiRetrievalResult(query=bounded_query, citations=())

    terms = _query_terms(bounded_query)
    if not terms:
        return LlmWikiRetrievalResult(query=bounded_query, citations=())

    citations: list[LlmWikiCitation] = []
    for markdown_path in _iter_markdown_files(wiki_root):
        content = _read_markdown(markdown_path)
        if content is None:
            continue
        citation = _score_markdown(
            path=markdown_path,
            root=wiki_root,
            content=content,
            terms=terms,
            excerpt_chars=settings.llm_wiki_excerpt_chars,
        )
        if citation is not None:
            citations.append(citation)

    citations.sort(key=lambda item: (-item.score, item.source_path, item.heading or ""))
    return LlmWikiRetrievalResult(
        query=bounded_query,
        citations=tuple(citations[: settings.llm_wiki_max_sources]),
    )


def _iter_markdown_files(root: Path) -> list[Path]:
    """Return visible Markdown files below a WIKI root.

    Args:
        root: Configured WIKI root.

    Returns:
        Sorted visible Markdown file paths.
    """
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
    )


def _read_markdown(path: Path) -> str | None:
    """Read one bounded Markdown file.

    Args:
        path: Markdown file path.

    Returns:
        File text, or None when it cannot be safely read.
    """
    try:
        if path.stat().st_size > MAX_WIKI_FILE_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _score_markdown(
    *,
    path: Path,
    root: Path,
    content: str,
    terms: tuple[str, ...],
    excerpt_chars: int,
) -> LlmWikiCitation | None:
    """Score one Markdown document against query terms.

    Args:
        path: Markdown file path.
        root: WIKI root used to compute relative source path.
        content: Markdown content.
        terms: Normalized query terms.
        excerpt_chars: Maximum excerpt length.

    Returns:
        Citation when the document has a positive lexical score.
    """
    title = _title(content) or path.stem.replace("-", " ")
    heading = _matching_heading(content, terms)
    lower_title = title.casefold()
    lower_heading = (heading or "").casefold()
    lower_content = content.casefold()
    score = 0.0
    for term in terms:
        if term in lower_title:
            score += 8.0
        if term in lower_heading:
            score += 5.0
        score += min(lower_content.count(term), 12) * 1.0
    if score <= 0:
        return None
    return LlmWikiCitation(
        title=_collapse_whitespace(title)[:120],
        source_path=_relative_source_path(path, root),
        heading=_collapse_whitespace(heading)[:120] if heading else None,
        excerpt=_excerpt(content, terms, excerpt_chars),
        score=round(score, 3),
    )


def _query_terms(query: str) -> tuple[str, ...]:
    """Extract bounded lexical retrieval terms.

    Args:
        query: Sanitized query text.

    Returns:
        Unique terms in first-seen order.
    """
    terms: list[str] = []
    seen: set[str] = set()
    for match in TOKEN_RE.finditer(query.casefold()):
        term = match.group(0).strip("._/-")
        if len(term) < MIN_QUERY_TERM_CHARS or term in STOP_TERMS or term in seen:
            continue
        terms.append(term)
        seen.add(term)
        if len(terms) >= MAX_QUERY_TERMS:
            break
    return tuple(terms)


def _title(content: str) -> str | None:
    """Return the first H1 title from Markdown content."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def _matching_heading(content: str, terms: tuple[str, ...]) -> str | None:
    """Return the first heading that matches a query term."""
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        heading = stripped.lstrip("#").strip()
        lower_heading = heading.casefold()
        if any(term in lower_heading for term in terms):
            return heading
    return None


def _excerpt(content: str, terms: tuple[str, ...], max_chars: int) -> str:
    """Return a bounded excerpt around the first matching term."""
    collapsed = _collapse_whitespace(content)
    lower_content = collapsed.casefold()
    first_index = min(
        (index for term in terms if (index := lower_content.find(term)) >= 0),
        default=0,
    )
    start = max(first_index - max_chars // 3, 0)
    end = min(start + max_chars, len(collapsed))
    return collapsed[start:end].strip()


def _relative_source_path(path: Path, root: Path) -> str:
    """Return a POSIX relative source path for API citations."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _collapse_whitespace(value: str) -> str:
    """Collapse whitespace for bounded prompts and excerpts."""
    return " ".join(value.split())
