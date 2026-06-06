"""Ingest the local LLM-WIKI into pgvector tables for semantic RAG.

Walks the Obsidian wiki (``--root``, default = the project LLM-WIKI), parses each
markdown page (frontmatter title/category/tags), chunks it by heading section,
embeds each chunk with an Ollama embedding model (default ``bge-m3``, 1024-dim),
and upserts ``wiki_documents`` / ``wiki_chunks`` / ``wiki_chunk_embeddings``.

Idempotent by document ``content_hash``: unchanged documents are skipped; changed
documents have their chunks/embeddings replaced. Dotfolders (``.smart-env``,
``.obsidian`` …) are skipped — only human-authored markdown is indexed.

Dry-run by default; pass ``--apply`` to write. Connection via ``--dsn`` (asyncpg
URL, password may come from the ``PGPASSWORD`` env var).

References:
    https://github.com/pgvector/pgvector
    https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from uuid import uuid4

import asyncpg

DEFAULT_ROOT = Path("/Volumes/Corsair EX400U Media/LLM-WIKI")
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "bge-m3"
DEFAULT_DIMENSIONS = 1024
SOURCE_MANIFEST_VERSION = "llm-wiki-rag-v1"

MAX_CHUNK_CHARS = 1600
MIN_CHUNK_CHARS = 40
MAX_CHUNKS_PER_DOC = 60
MAX_SUMMARY_CHARS = 600
EMBED_MAX_RETRIES = 3
_HEADING_RE = re.compile(r"^#{1,6}\s+(.*)$")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _nfc(text: str) -> str:
    """Return NFC-normalized text (macOS filenames/content are often NFD)."""
    return unicodedata.normalize("NFC", text)


def _sha256(text: str) -> str:
    """Return a hex SHA-256 digest of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def iter_markdown(root: Path) -> list[Path]:
    """Return visible markdown files under the wiki root (dotfolders excluded)."""
    return sorted(
        p
        for p in root.rglob("*.md")
        if p.is_file() and not any(part.startswith(".") for part in p.relative_to(root).parts)
    )


def parse_frontmatter(text: str) -> tuple[dict[str, str | list[str]], str]:
    """Split YAML-ish frontmatter from markdown body.

    Args:
        text: Full markdown file content.

    Returns:
        (frontmatter dict with str/list values, body text without frontmatter).
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    front: dict[str, str | list[str]] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        value = raw.strip()
        if value.startswith("[") and value.endswith("]"):
            front[key] = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        else:
            front[key] = value.strip("'\"")
    return front, text[match.end():]


def _title(body: str, front: dict, slug: str) -> str:
    """Return the document title (frontmatter > first H1 > slug)."""
    if isinstance(front.get("title"), str) and front["title"]:
        return str(front["title"])
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return slug.replace("-", " ")


def _summary(body: str) -> str | None:
    """Return a bounded summary from the takeaway/요약 area near the top."""
    collapsed = " ".join(body.split())
    return collapsed[:MAX_SUMMARY_CHARS] or None


def chunk_sections(body: str) -> list[tuple[str | None, str]]:
    """Chunk markdown body into (heading, content) sections, bounded in size.

    Args:
        body: Markdown body without frontmatter.

    Returns:
        List of (heading-or-None, chunk-text) tuples.
    """
    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in body.splitlines():
        heading = _HEADING_RE.match(line.strip())
        if heading:
            sections.append((heading.group(1).strip(), []))
        else:
            sections[-1][1].append(line)
    chunks: list[tuple[str | None, str]] = []
    for heading, lines in sections:
        text = "\n".join(lines).strip()
        if not text:
            continue
        prefix = f"{heading}\n" if heading else ""
        # Bound each section; split oversize sections on blank lines.
        buf = prefix
        for para in re.split(r"\n\s*\n", text):
            candidate = (buf + "\n\n" + para).strip() if buf.strip() else para
            if len(candidate) > MAX_CHUNK_CHARS and buf.strip():
                chunks.append((heading, buf.strip()))
                buf = (f"{heading}\n" if heading else "") + para
            else:
                buf = candidate
        if buf.strip() and len(buf.strip()) >= MIN_CHUNK_CHARS:
            chunks.append((heading, buf.strip()))
    return chunks[:MAX_CHUNKS_PER_DOC]


def embed_text(text: str, *, ollama_url: str, model: str, dimensions: int) -> list[float]:
    """Return an Ollama embedding for text.

    Args:
        text: Text to embed.
        ollama_url: Ollama base URL.
        model: Embedding model name.
        dimensions: Expected embedding dimension (validated).

    Returns:
        Embedding vector.

    Raises:
        ValueError: If the response dimension does not match the expected one.
    """
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(EMBED_MAX_RETRIES):
        try:
            req = urllib.request.Request(
                f"{ollama_url}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as exc:
            # Transient (server busy / connection reset): back off and retry.
            last_error = exc
            if attempt < EMBED_MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise RuntimeError(f"ollama embeddings failed after retries: {exc}") from exc
        vector = data.get("embedding") or []
        if len(vector) != dimensions:
            raise ValueError(
                f"embedding dim {len(vector)} != expected {dimensions} for model {model}"
            )
        return [float(x) for x in vector]
    raise RuntimeError(f"ollama embeddings failed: {last_error}")


def _vector_literal(vector: list[float]) -> str:
    """Return a pgvector text literal like ``[0.1,0.2,...]``."""
    return "[" + ",".join(repr(round(x, 6)) for x in vector) + "]"


async def ingest(
    *, dsn: str, root: Path, ollama_url: str, model: str, dimensions: int, limit: int | None
) -> dict:
    """Ingest wiki markdown into the RAG tables. Returns a count-only summary."""
    files = iter_markdown(root)
    if limit is not None:
        files = files[:limit]
    conn = await asyncpg.connect(dsn=dsn)
    stats: Counter[str] = Counter()
    try:
        failures: list[dict[str, str]] = []
        for path in files:
            slug = _nfc(path.stem)
            try:
                raw = _nfc(path.read_text(encoding="utf-8", errors="replace"))
                front, body = parse_frontmatter(raw)
                rel_path = path.relative_to(root).as_posix()
                content_hash = _sha256(raw)
                existing = await conn.fetchrow(
                    "select id, content_hash from wiki_documents where slug=$1", slug
                )
                if existing and existing["content_hash"] == content_hash:
                    stats["skipped_unchanged"] += 1
                    continue
                chunks = chunk_sections(body)
                if not chunks:
                    stats["skipped_empty"] += 1
                    continue
                category = front.get("category") if isinstance(front.get("category"), str) else None
                tags = front.get("tags") if isinstance(front.get("tags"), list) else []
                title = _title(body, front, slug)
                async with conn.transaction():
                    if existing:
                        await conn.execute("delete from wiki_documents where id=$1", existing["id"])
                        stats["replaced"] += 1
                    doc_id = uuid4()
                    await conn.execute(
                        """insert into wiki_documents
                           (id, slug, title, category, rel_path, tags, summary, content_hash,
                            source_manifest_version)
                           values ($1,$2,$3,$4,$5,$6::jsonb,$7,$8,$9)""",
                        doc_id, slug, title[:300], (category or None) and category[:40], rel_path,
                        json.dumps(tags, ensure_ascii=False), _summary(body), content_hash,
                        SOURCE_MANIFEST_VERSION,
                    )
                    stats["documents"] += 1
                    for index, (heading, content) in enumerate(chunks):
                        chunk_id = uuid4()
                        await conn.execute(
                            """insert into wiki_chunks
                               (id, document_id, heading, chunk_index, content, content_hash,
                                token_count)
                               values ($1,$2,$3,$4,$5,$6,$7)""",
                            chunk_id, doc_id, (heading or None) and heading[:300], index,
                            content, _sha256(content), len(content.split()),
                        )
                        vector = embed_text(
                            content, ollama_url=ollama_url, model=model, dimensions=dimensions
                        )
                        await conn.execute(
                            """insert into wiki_chunk_embeddings
                               (id, chunk_id, embedding, embedding_model, embedding_dimensions)
                               values ($1,$2,$3::extensions.vector,$4,$5)""",
                            uuid4(), chunk_id, _vector_literal(vector), model, dimensions,
                        )
                        stats["chunks"] += 1
            except Exception as exc:
                # Per-document isolation: a failed doc is rolled back, reported, and
                # retried on the next idempotent run (its content_hash is not stored).
                stats["failed_docs"] += 1
                failures.append({"slug": slug, "error": f"{type(exc).__name__}: {str(exc)[:140]}"})
        totals = {
            "documents_in_db": await conn.fetchval("select count(*) from wiki_documents"),
            "chunks_in_db": await conn.fetchval("select count(*) from wiki_chunks"),
            "embeddings_in_db": await conn.fetchval("select count(*) from wiki_chunk_embeddings"),
        }
    finally:
        await conn.close()
    return {"processed_files": len(files), **dict(stats), **totals, "failures": failures[:50]}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--dsn", required=True)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dimensions", type=int, default=DEFAULT_DIMENSIONS)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--summary", type=Path, default=None)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.expanduser()
    if not root.is_dir():
        raise SystemExit(f"ERROR: wiki root not found: {root}")
    if not args.apply:
        files = iter_markdown(root)
        if args.limit is not None:
            files = files[: args.limit]
        summary = {"apply_requested": False, "markdown_files": len(files), "root_name": root.name}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    summary = asyncio.run(
        ingest(
            dsn=args.dsn, root=root, ollama_url=args.ollama_url, model=args.model,
            dimensions=args.dimensions, limit=args.limit,
        )
    )
    summary["apply_requested"] = True
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
