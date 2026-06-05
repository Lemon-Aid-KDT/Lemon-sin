"""누락 이미지 gap-fill 워크플로 생성 (기존 _ssclassify_chunk1.wf.js 템플릿 재사용, ITEMS만 교체).

순차 실행 전제(병렬 실패 회피). 청크당 <=700 에이전트.
"""
import json
import re
from pathlib import Path

OUTDIR = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review")
MISSING = OUTDIR / "_ssclassify_missing.txt"
TEMPLATE = OUTDIR / "_ssclassify_chunk1.wf.js"
BATCH = 18
CHUNK_IMG = BATCH * 700  # 12600

items = [l.strip() for l in MISSING.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"누락 {len(items)}장")
tpl = TEMPLATE.read_text(encoding="utf-8")

chunks = [items[i:i + CHUNK_IMG] for i in range(0, len(items), CHUNK_IMG)]
for i, ch in enumerate(chunks, 1):
    arr = "[\n" + ",".join(json.dumps(s, ensure_ascii=False) for s in ch) + "\n]"
    js = re.sub(r"const ITEMS = \[[^\]]*\]", "const ITEMS = " + arr, tpl, count=1)
    js = js.replace("ss-classify-1", f"ss-gapfill-{i}")
    js = js.replace("(chunk 1/3)", f"(gapfill {i}/{len(chunks)})")
    p = OUTDIR / f"_ssgapfill_chunk{i}.wf.js"
    p.write_text(js, encoding="utf-8")
    print(f"  gapfill{i}: {len(ch)}장, {(len(ch)+BATCH-1)//BATCH} 에이전트 -> {p.name} ({len(js)//1024}KB)")
