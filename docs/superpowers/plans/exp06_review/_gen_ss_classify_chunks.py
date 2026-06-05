"""selectstar 관련 ~35폴더 전수 per-image 분류 워크플로를 청크로 생성.

per-image: 각 이미지를 비전으로 보고 taxo59 클래스(or none) 판정 → 정제+채굴 자동.
스크립트 크기·에이전트상한(1000/wf) 때문에 청크 분할.
"""
import glob
import json
import os
from pathlib import Path

SS = Path(r"C:\Lemon-sin\data\food_images\raw\selectstar")
OUTDIR = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review")

# per-image 분류 대상 = taxo59 가능성 있는 폴더(매핑31 + 채굴4). 순수 OOD 57폴더 제외.
RELEVANT = [
    "jajangmyeon", "baguette", "bulgogi", "cake", "curry", "dim_sum", "chicken", "burger",
    "ramen", "kimchi_stew", "pasta", "pizza", "rice_noodle", "salad", "sandwich",
    "korean_pancake", "gimbap", "sushi", "takoyaki", "tteokbokki", "udon", "soup",
    "pound_cake", "nasi_goreng", "seaweed_soup", "bibimbap", "sashimi", "banh_mi",
    "croissant", "caprese", "croque_monsieur",  # 매핑 31
    "BBQ", "galbi", "steak", "soba",            # 채굴 4
]
BATCH = 18
MAX_AGENTS = 750  # workflow당 안전 상한(<1000)
CHUNK_IMG = BATCH * MAX_AGENTS  # 청크당 최대 이미지 = 13500

items = []
for f in RELEVANT:
    pngs = sorted(os.path.basename(p) for p in glob.glob(str(SS / f / "png" / "*.png"))
                  if not os.path.basename(p).startswith("._"))
    for fn in pngs:
        items.append(f"{f}/{fn}")
print(f"대상 폴더 {len(RELEVANT)} / 총 이미지 {len(items)}")

chunks = [items[i:i + CHUNK_IMG] for i in range(0, len(items), CHUNK_IMG)]
print(f"청크 {len(chunks)}개 (청크당 최대 {CHUNK_IMG}장)")

TEMPLATE = r'''export const meta = {
  name: 'ss-classify-CHUNKID',
  description: 'Per-image classify selectstar images -> taxo59 class or none (chunk CHUNKID/NCHUNK)',
  phases: [{ title: 'Classify', detail: 'agents label each image with taxo59 class' }],
}

const BASE = 'C:/Lemon-sin/data/food_images/raw/selectstar'
const CLASSES = `barbecue-ribs(갈비구이), black-bean-noodles(짜장면), braised-chicken(찜닭), braised-pork-hock(족발), bread(빵·식빵/바게트), bulgogi(불고기), cake(케이크), cold-noodles(냉면), curry(카레), dim-sum(딤섬·찐만두), dumplings(군/물만두), fish-cake(어묵), fried-chicken(후라이드·양념치킨), fried-food-platter(튀김모둠), fried-rice(볶음밥), grilled-beef(소고기구이·한식), grilled-fish(생선구이), grilled-pork-belly(삼겹살구이), hamburger(햄버거), hot-pot(전골·한국식국물전골), korean-blood-sausage(순대), mixed-rice-bowl(비빔밥), pasta(파스타), pizza(피자), raw-fish(생선회·사시미), rice-bowl(덮밥), rice-porridge(죽), rice-soup(국밥), salad(샐러드), sandwich(샌드위치), savory-pancake(전·부침개), seaweed-rice-roll(김밥), shrimp-dish(새우요리), spicy-mixed-noodles(비빔국수), squid-dish(오징어요리), sushi(초밥), takoyaki(타코야키), udon(우동), korean-clear-soup(맑은국), korean-red-soup(빨간국), western-cream-soup(양식크림수프), japanese-ramen(일본라멘), korean-ramyeon-red(라면·인스턴트), cold-ramen(냉라멘), tteokbokki-red(떡볶이), tteokbokki-cream-rose(로제떡볶이), tteokbokki-jajang(짜장떡볶이), pork-cutlet-dry(돈가스), pork-cutlet-sauced(소스돈가스), seafood-spicy-tang(해물매운탕), seafood-clear-tang(해물맑은탕), seafood-jjim(해물찜), kalguksu(칼국수), rice-noodle-soup(쌀국수·국물), noodle-plain(잔치/일반국수), jjigae-red(빨간찌개), doenjang-jjigae(된장찌개), jjamppong(짬뽕), nagasaki-champon(나가사끼짬뽕)`

const SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string', description: '주어진 folder/filename 그대로' },
          cls: { type: 'string', description: 'taxo59 en 클래스명 or "none"' },
          conf: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['file', 'cls', 'conf'],
      },
    },
  },
  required: ['results'],
}

const ITEMS = __ITEMS__
const BATCH = 18
const batches = []
for (let i = 0; i < ITEMS.length; i += BATCH) batches.push(ITEMS.slice(i, i + BATCH))

phase('Classify')
log(`chunk CHUNKID: ${ITEMS.length}장 -> ${batches.length} 배치`)

const rows = await parallel(
  batches.map((batch, bi) => () => {
    const list = batch.map((it, j) => {
      const slash = it.indexOf('/')
      const folder = it.slice(0, slash), file = it.slice(slash + 1)
      return `  ${j + 1}. ${BASE}/${folder}/png/${file}   (id=${it})`
    }).join('\n')
    const prompt = `selectstar 이미지를 우리 한식탐지 모델의 59클래스에 **이미지 단위로** 분류합니다(폴더명 무시, 각 사진만 보고 판단).

taxo59 en(ko):
${CLASSES}

각 이미지를 **Read로 직접 보고**:
- file: 주어진 id(folder/filename) 그대로
- cls: 그 사진의 음식이 **명확히 맞는** taxo59 en 클래스명. 애매하거나 cuisine이 다르거나(양식 스테이크/크루아상/디저트 등) 59클래스에 없으면 "none".
- conf: high(거의 동일)/medium/low

판단 규칙:
- 폴더명에 휘둘리지 말 것. 같은 폴더라도 사진마다 다를 수 있음(예: bbq 폴더에 삼겹살 사진→grilled-pork-belly, 소고기→grilled-beef, 소시지→none).
- 한식 클래스에 타cuisine 억지 매핑 금지(서양 스테이크≠grilled-beef→none, 크루아상은 bread로 줄지 디저트성 강하면 none, 육회≠raw-fish→none).
- barbecue-ribs=양념갈비구이, grilled-pork-belly=삼겹살구이, grilled-beef=소불고기 아닌 한식 소고기구이.
- 곁들이 없이 메인이 뚜렷한 그 음식이면 해당 클래스.

이미지 ${batch.length}장:
${list}

각 이미지 Read 후 StructuredOutput으로 results[] (이미지당 1개, file=id 그대로) 반환.`
    return agent(prompt, { label: `cls:c${bi + 1}`, phase: 'Classify', schema: SCHEMA })
  })
)

const all = []
rows.forEach((r) => {
  if (!r) return
  for (const x of r.results || []) all.push(x)
})
const mapped = all.filter((x) => x.cls && x.cls !== 'none')
return { count: all.length, mapped: mapped.length, rows: all }
'''

for i, ch in enumerate(chunks, 1):
    js = (TEMPLATE
          .replace("CHUNKID", str(i))
          .replace("NCHUNK", str(len(chunks)))
          .replace("__ITEMS__", json.dumps(ch, ensure_ascii=False)))
    p = OUTDIR / f"_ssclassify_chunk{i}.wf.js"
    p.write_text(js, encoding="utf-8")
    print(f"  chunk{i}: {len(ch)}장, {(len(ch)+BATCH-1)//BATCH} 에이전트 -> {p.name} ({len(js)//1024}KB)")
