#!/usr/bin/env python3
"""
sync_guide.py — PROJECT_GUIDE.md 본문을 guide.html 안의 <script id="md-source">
블록에 주입하여 두 파일을 자동 동기화한다.

사용법:
    python scripts/sync_guide.py            # 동기화 + 변경 시 종료 코드 0 / 변경 없으면 0
    python scripts/sync_guide.py --check    # 검증만 (동기화 안 됨이면 종료 코드 1)

자동 검증:
    - PG.md 안에 </script> 가 있으면 거부 (HTML 깨짐 방지)
    - PG.md 안에 진짜 ---SPLIT--- 외에 의도치 않은 게 있으면 경고
    - guide.html에 NULL 바이트가 끼어들면 자동 제거
    - 동기화 후 SPLIT 카운트 양쪽 일치 검증
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD_PATH = ROOT / "PROJECT_GUIDE.md"
HTML_PATH = ROOT / "guide.html"

MD_SOURCE_RE = re.compile(
    r'(<script id="md-source" type="text/plain">\n)(.*?)(\n</script>)',
    re.DOTALL,
)


def fail(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def info(msg: str) -> None:
    print(f"  {msg}")


def ok(msg: str) -> None:
    print(f"✓ {msg}")


def load_md() -> str:
    if not MD_PATH.exists():
        fail(f"PROJECT_GUIDE.md 없음: {MD_PATH}")
    text = MD_PATH.read_text(encoding="utf-8")
    return text


def load_html() -> str:
    if not HTML_PATH.exists():
        fail(f"guide.html 없음: {HTML_PATH}")
    raw = HTML_PATH.read_bytes()
    if b"\x00" in raw:
        info("guide.html에 NULL 바이트 발견 → 자동 제거")
        raw = raw.replace(b"\x00", b"")
        HTML_PATH.write_bytes(raw)
    return raw.decode("utf-8")


def validate_md(md: str) -> None:
    """동기화 전 안전 검증."""
    if "</script>" in md:
        fail(
            "PROJECT_GUIDE.md 안에 </script> 가 있습니다. "
            "guide.html이 깨지므로 다른 표현으로 우회해주세요."
        )

    splits = re.findall(r"^---SPLIT---$", md, re.MULTILINE)
    info(f"PG.md SPLIT 카운트: {len(splits)} (sections {len(splits) + 1})")

    # 표 안 인라인 코드에 SPLIT 마커가 들어가면 split이 망가짐
    inline_split = re.findall(r"`---SPLIT---`", md)
    if inline_split:
        fail(
            f"PG.md 인라인 코드 안에 ---SPLIT--- 패턴 {len(inline_split)}건 발견. "
            "표나 본문 안에서 이 마커를 직접 표기하지 마세요 (다른 표현으로 우회)."
        )


def sync(md: str, html: str) -> tuple[str, bool]:
    """md를 html의 md-source에 주입. 반환: (새 html, 변경 여부)."""
    m = MD_SOURCE_RE.search(html)
    if not m:
        fail('guide.html에서 <script id="md-source"> 블록을 찾을 수 없습니다.')

    current_md = m.group(2)
    if current_md == md:
        return html, False

    new_html = html[: m.start()] + m.group(1) + md + m.group(3) + html[m.end() :]
    return new_html, True


def verify_after(html: str, md: str) -> None:
    """동기화 후 검증."""
    md_splits = len(re.findall(r"^---SPLIT---$", md, re.MULTILINE))
    html_splits = len(re.findall(r"^---SPLIT---$", html, re.MULTILINE))
    if md_splits != html_splits:
        fail(
            f"SPLIT 카운트 불일치: PG.md {md_splits} vs guide.html {html_splits}. "
            "동기화 로직 버그일 수 있습니다."
        )

    # </script> 정확히 3개여야 정상 (mermaid CDN + md-source + JS)
    close_count = html.count("</script>")
    if close_count != 3:
        fail(
            f"guide.html의 </script> 카운트가 {close_count}개입니다 (정상: 3). "
            "HTML 구조가 깨졌을 수 있습니다."
        )

    # 닫는 태그 정상
    if not html.rstrip().endswith("</html>"):
        fail("guide.html이 </html>로 끝나지 않습니다.")


def main() -> int:
    parser = argparse.ArgumentParser(description="PG.md → guide.html 자동 동기화")
    parser.add_argument(
        "--check",
        action="store_true",
        help="검증만 실행 (동기화 필요 시 종료 코드 1)",
    )
    args = parser.parse_args()

    md = load_md()
    html = load_html()

    validate_md(md)

    new_html, changed = sync(md, html)
    verify_after(new_html, md)

    if not changed:
        ok("이미 동기화 상태입니다 (변경 없음).")
        return 0

    if args.check:
        fail(
            "guide.html이 PROJECT_GUIDE.md와 동기화돼 있지 않습니다. "
            "scripts/sync_guide.py 를 실행하고 다시 commit 해주세요."
        )

    HTML_PATH.write_bytes(new_html.encode("utf-8"))
    ok(f"guide.html 동기화 완료 ({len(new_html):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
