"""selectstar 92폴더 비전-검증 워크플로 스크립트 생성 (폴더당 대표 5장 샘플 주입)."""
import glob
import json
import os
from pathlib import Path

SS = Path(r"C:\Lemon-sin\data\food_images\raw\selectstar")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\_verify_ss_mapping.wf.js")
N = 10

folders = []
for d in sorted(p.name for p in SS.iterdir() if p.is_dir()):
    pngs = [p for p in sorted(glob.glob(str(SS / d / "png" / "*.png")))
            if not os.path.basename(p).startswith("._")]
    if not pngs:
        continue
    n = len(pngs)
    picks = [pngs[n * k // (N + 1)] for k in range(1, N + 1)]
    folders.append({"folder": d, "paths": [p.replace("\\", "/") for p in picks]})
print(f"{len(folders)} 폴더, 폴더당 {N}장 샘플")

TEMPLATE = r'''export const meta = {
  name: 'verify-selectstar-taxo59-mapping',
  description: 'Vision-verify selectstar 92 folders -> taxo59 mapping (look at images, not just names)',
  phases: [{ title: 'Verify', detail: 'agents view sample images per folder and decide taxo59 match' }],
}

const CLASSES = `barbecue-ribs(갈비), black-bean-noodles(짜장면), braised-chicken(찜닭), braised-pork-hock(족발), bread(빵), bulgogi(불고기), cake(케이크), cold-noodles(냉면), curry(카레), dim-sum(딤섬·찐만두), dumplings(군/물만두), fish-cake(어묵), fried-chicken(후라이드·양념치킨), fried-food-platter(튀김모둠), fried-rice(볶음밥), grilled-beef(소고기구이·한식), grilled-fish(생선구이), grilled-pork-belly(삼겹살), hamburger(햄버거), hot-pot(전골·한국식 국물전골), korean-blood-sausage(순대), mixed-rice-bowl(비빔밥), pasta(파스타), pizza(피자), raw-fish(회·생선회/사시미), rice-bowl(덮밥), rice-porridge(죽), rice-soup(국밥), salad(샐러드), sandwich(샌드위치), savory-pancake(전·부침개), seaweed-rice-roll(김밥), shrimp-dish(새우요리), spicy-mixed-noodles(비빔국수), squid-dish(오징어요리), sushi(초밥), takoyaki(타코야키), udon(우동), korean-clear-soup(맑은국), korean-red-soup(빨간국), western-cream-soup(양식수프), japanese-ramen(일본라멘), korean-ramyeon-red(라면·인스턴트), cold-ramen(냉라멘), tteokbokki-red(떡볶이), tteokbokki-cream-rose(로제떡볶이), tteokbokki-jajang(짜장떡볶이), pork-cutlet-dry(돈가스·소스따로), pork-cutlet-sauced(소스돈가스), seafood-spicy-tang(해물매운탕), seafood-clear-tang(해물맑은탕), seafood-jjim(해물찜), kalguksu(칼국수), rice-noodle-soup(쌀국수), noodle-plain(국수·잔치/일반국수), jjigae-red(빨간찌개·김치/순두부), doenjang-jjigae(된장찌개), jjamppong(짬뽕), nagasaki-champon(나가사끼짬뽕)`

const SCHEMA = {
  type: 'object',
  properties: {
    results: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          folder: { type: 'string' },
          food_seen: { type: 'string', description: '이미지에서 실제로 본 음식(한국어)' },
          taxo59_match: { type: 'string', description: 'taxo59 en 클래스명 or "none"' },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          caveat: { type: 'string', description: 'cuisine/시각 차이 주의(예: 중식 맑은핫팟이라 전골과 다름), 없으면 빈문자열' },
          consistent: { type: 'boolean', description: '5장이 한 음식으로 일관되나' },
          note: { type: 'string' },
        },
        required: ['folder', 'food_seen', 'taxo59_match', 'confidence', 'caveat', 'consistent', 'note'],
      },
    },
  },
  required: ['results'],
}

const FOLDERS = __FOLDERS__
const BATCH = 2
const batches = []
for (let i = 0; i < FOLDERS.length; i += BATCH) batches.push(FOLDERS.slice(i, i + BATCH))

phase('Verify')
log(`${FOLDERS.length}개 폴더 -> ${batches.length}개 배치 비전 검증`)

const rows = await parallel(
  batches.map((batch, bi) => () => {
    const block = batch
      .map((f) => `[폴더 ${f.folder}] 샘플 ${f.paths.length}장:\n` + f.paths.map((p, j) => `  ${j + 1}. ${p}`).join('\n'))
      .join('\n\n')
    const prompt = `selectstar 데이터셋의 폴더를 우리 한식탐지 모델의 59클래스에 **매핑할지** 검증합니다. 목적: 그 폴더 음식을 해당 taxo59 클래스의 **학습 보강용**으로 써도 되는지.

taxo59 클래스 en(ko):
${CLASSES}

각 폴더의 샘플 이미지를 **Read 도구로 직접 보고**, 폴더 전체가 어떤 음식인지 판단해 매핑:
- food_seen: 실제로 본 음식(한국어)
- taxo59_match: **시각+의미가 명확히 맞는** taxo59 en 클래스명. 애매하거나 cuisine이 다르면 "none".
- confidence: high(거의 동일)/medium(대체로 맞음)/low(불확실)
- caveat: 주의점. 예) 폴더명은 같아도 내용이 다른 음식, cuisine 차이(중식 맑은핫팟≠한식 전골, 독일 슈바인스학세≠족발, 양식 스테이크 vs 한식 소고기구이), 박스 라벨로 부적합 등. 없으면 "".
- consistent: 5장이 한 음식으로 일관되는지(아니면 false + note)
- note: 한 줄 사유

**보수적으로**: 폴더이름만 믿지 말고 이미지를 보고 판단. 한식 클래스에 타cuisine을 억지로 끼우지 말 것(필요하면 none/low). 우리에게 없는 음식(잡채·마파두부·라따뚜이·티라미수 등)은 "none".

폴더 ${batch.length}개:
${block}

각 폴더를 이미지로 확인 후 StructuredOutput으로 results[] (폴더당 1개, folder명 그대로) 반환.`
    return agent(prompt, { label: `verify:b${bi + 1}`, phase: 'Verify', schema: SCHEMA })
  })
)

const all = []
rows.forEach((r) => {
  if (!r) return
  for (const x of r.results || []) all.push(x)
})
const mapped = all.filter((x) => x.taxo59_match && x.taxo59_match !== 'none')
return { count: all.length, mapped: mapped.length, rows: all }
'''

js = TEMPLATE.replace("__FOLDERS__", json.dumps(folders, ensure_ascii=False))
OUT.write_text(js, encoding="utf-8")
print(f"WROTE {OUT}  (배치 {(len(folders)+3)//4})")
