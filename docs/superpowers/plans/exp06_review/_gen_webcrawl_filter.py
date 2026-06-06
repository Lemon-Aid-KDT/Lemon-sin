"""web_crawl 실데이터 단일요리+taxo59 실제검증 필터 워크플로 생성 (폴더명 노이즈 가능)."""
import glob, json, os
from pathlib import Path
BASE = Path(r"C:\Lemon-sin\data\food_images\raw\web_crawl")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\_webcrawl_filter.wf.js")
items = []
for d in sorted(p.name for p in BASE.iterdir() if p.is_dir()):
    for p in sorted(glob.glob(str(BASE / d / "*"))):
        if os.path.splitext(p)[1].lower() in (".jpg", ".jpeg", ".png", ".webp") and not os.path.basename(p).startswith("._"):
            items.append(f"{d}/{os.path.basename(p)}")
print(f"이미지 {len(items)}장")

TEMPLATE = r'''export const meta = {
  name: 'webcrawl-filter',
  description: 'web_crawl 실데이터: 단일요리+taxo59 실제검증만 KEEP (폴더명 노이즈 가능)',
  phases: [{ title: 'Classify', detail: 'agents verify each image: real class + single-dish' }],
}
const BASE = 'C:/Lemon-sin/data/food_images/raw/web_crawl'
const CLASSES = `barbecue-ribs(갈비), black-bean-noodles(짜장면), braised-chicken(찜닭), braised-pork-hock(족발), bread(빵), bulgogi(불고기), cake(케이크), cold-noodles(냉면), curry(카레), dim-sum(딤섬·찐만두), dumplings(군/물만두), fish-cake(어묵), fried-chicken(후라이드·양념치킨), fried-food-platter(튀김모둠), fried-rice(볶음밥), grilled-beef(소고기구이), grilled-fish(생선구이), grilled-pork-belly(삼겹살), hamburger(햄버거), hot-pot(전골), korean-blood-sausage(순대), mixed-rice-bowl(비빔밥), pasta(파스타), pizza(피자), raw-fish(회·사시미), rice-bowl(덮밥), rice-porridge(죽), rice-soup(국밥), salad(샐러드), sandwich(샌드위치), savory-pancake(전·부침개), seaweed-rice-roll(김밥), shrimp-dish(새우요리), spicy-mixed-noodles(비빔국수), squid-dish(오징어요리), sushi(초밥), takoyaki(타코야키), udon(우동), korean-clear-soup(맑은국), korean-red-soup(빨간국), western-cream-soup(양식수프), japanese-ramen(일본라멘), korean-ramyeon-red(라면·인스턴트), cold-ramen(냉라멘·차가운라멘), tteokbokki-red(떡볶이), tteokbokki-cream-rose(로제떡볶이), tteokbokki-jajang(짜장떡볶이), pork-cutlet-dry(돈가스), pork-cutlet-sauced(소스돈가스), seafood-spicy-tang(해물매운탕), seafood-clear-tang(해물맑은탕), seafood-jjim(해물찜), kalguksu(칼국수), rice-noodle-soup(쌀국수), noodle-plain(국수), jjigae-red(빨간찌개), doenjang-jjigae(된장찌개), jjamppong(짬뽕), nagasaki-champon(나가사끼짬뽕)`
const SCHEMA = {
  type: 'object',
  properties: { results: { type: 'array', items: { type: 'object', properties: {
    file: { type: 'string', description: 'folder/filename 그대로' },
    folder: { type: 'string', description: '경로의 폴더명(의도된 클래스)' },
    foods: { type: 'string' },
    matched_class: { type: 'string', description: '실제 보이는 메인이 맞는 taxo59 en명, 아니면 none' },
    category: { type: 'string', enum: ['single_in', 'multi', 'ood', 'scene_nonfood', 'borderline_dropped'] },
    keep: { type: 'boolean' },
    folder_match: { type: 'boolean', description: 'matched_class가 폴더명과 같은가(크롤 노이즈 측정)' },
    note: { type: 'string' },
  }, required: ['file', 'folder', 'foods', 'matched_class', 'category', 'keep', 'folder_match', 'note'] } } },
  required: ['results'],
}
const ITEMS = __ITEMS__
const BATCH = 6
const batches = []
for (let i = 0; i < ITEMS.length; i += BATCH) batches.push(ITEMS.slice(i, i + BATCH))
phase('Classify')
log(`${ITEMS.length}장 -> ${batches.length} 배치`)
const rows = await parallel(batches.map((batch, bi) => () => {
  const list = batch.map((f, j) => `  ${j + 1}. ${BASE}/${f}   (file=${f})`).join('\n')
  const prompt = `web_crawl 실데이터를 학습용으로 검증한다. 기준: **① 한 사진 메인요리 1개(단일) ② 그게 taxo59 클래스에 맞음**. ⚠️ 폴더명은 검색어(의도된 클래스)이나 **크롤 노이즈가 많아**(예: 'cold-ramen' 폴더에 일반 라멘 다수) **반드시 이미지로 실제 판단**.

taxo59 en(ko):
${CLASSES}

각 이미지 Read 후:
- folder: 경로의 폴더명(파일 id의 / 앞부분)
- foods: 실제 보이는 음식(한국어)
- matched_class: 실제 메인 1개가 맞는 taxo59 en명(폴더명과 달라도 진짜로 보이는 것), 아니면 none. (냉라멘은 차가운/얼음 있는 라멘; 그냥 뜨거운 라멘이면 japanese-ramen)
- category: single_in(메인1개+59클래스=KEEP) / multi / ood(콜라주·텍스트카드·워터마크·비음식·딴음식) / scene_nonfood / borderline_dropped
- keep: single_in일 때만 true
- folder_match: matched_class가 폴더명과 동일하면 true (노이즈 측정용)
- note: 한 줄
규칙: 곁들이 반찬 무시 메인1개면 single_in. 콜라주/여러접시 합성/텍스트 박힌 레시피카드 = ood.

이미지 ${batch.length}장:
${list}
StructuredOutput results[] (이미지당1개, file=주어진 id 그대로) 반환.`
  return agent(prompt, { label: `cls:b${bi + 1}`, phase: 'Classify', schema: SCHEMA })
}))
const all = []
rows.forEach((r) => { if (r) for (const x of r.results || []) all.push(x) })
const keep = all.filter((x) => x.keep)
const byCat = {}
for (const x of all) byCat[x.category] = (byCat[x.category] || 0) + 1
log(`완료 ${all.length} / KEEP ${keep.length} / ${JSON.stringify(byCat)}`)
return { count: all.length, keep_count: keep.length, by_category: byCat, rows: all }
'''
js = TEMPLATE.replace("__ITEMS__", json.dumps(items, ensure_ascii=False))
OUT.write_text(js, encoding="utf-8")
print(f"WROTE {OUT} ({len(js)//1024}KB, 배치 {(len(items)+5)//6})")
