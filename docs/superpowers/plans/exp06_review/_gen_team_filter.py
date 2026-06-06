"""team_collected 실데이터 단일요리+taxo59 매칭 필터 워크플로 생성 (per-image 비전)."""
import glob, json, os
from pathlib import Path

BASE = Path(r"C:\Lemon-sin\data\food_images\raw\team_collected")
OUT = Path(r"C:\Lemon-sin\docs\superpowers\plans\exp06_review\_team_filter.wf.js")
files = sorted(os.path.basename(p) for p in glob.glob(str(BASE / "*.jpg")) if not os.path.basename(p).startswith("._"))
print(f"이미지 {len(files)}장")

TEMPLATE = r'''export const meta = {
  name: 'team-collected-filter',
  description: 'team_collected 실데이터: 단일요리+taxo59 매칭만 KEEP (per-image 비전)',
  phases: [{ title: 'Classify', detail: 'agents view each image, judge single-dish + class match' }],
}
const BASE = 'C:/Lemon-sin/data/food_images/raw/team_collected'
const CLASSES = `barbecue-ribs(갈비), black-bean-noodles(짜장면), braised-chicken(찜닭), braised-pork-hock(족발), bread(빵), bulgogi(불고기), cake(케이크), cold-noodles(냉면), curry(카레), dim-sum(딤섬·찐만두), dumplings(군/물만두), fish-cake(어묵), fried-chicken(후라이드·양념치킨), fried-food-platter(튀김모둠), fried-rice(볶음밥), grilled-beef(소고기구이), grilled-fish(생선구이), grilled-pork-belly(삼겹살), hamburger(햄버거), hot-pot(전골), korean-blood-sausage(순대), mixed-rice-bowl(비빔밥), pasta(파스타), pizza(피자), raw-fish(회·사시미), rice-bowl(덮밥), rice-porridge(죽), rice-soup(국밥), salad(샐러드), sandwich(샌드위치), savory-pancake(전·부침개), seaweed-rice-roll(김밥), shrimp-dish(새우요리), spicy-mixed-noodles(비빔국수), squid-dish(오징어요리), sushi(초밥), takoyaki(타코야키), udon(우동), korean-clear-soup(맑은국), korean-red-soup(빨간국), western-cream-soup(양식수프), japanese-ramen(일본라멘), korean-ramyeon-red(라면·인스턴트), cold-ramen(냉라멘), tteokbokki-red(떡볶이), tteokbokki-cream-rose(로제떡볶이), tteokbokki-jajang(짜장떡볶이), pork-cutlet-dry(돈가스), pork-cutlet-sauced(소스돈가스), seafood-spicy-tang(해물매운탕), seafood-clear-tang(해물맑은탕), seafood-jjim(해물찜), kalguksu(칼국수), rice-noodle-soup(쌀국수), noodle-plain(국수), jjigae-red(빨간찌개), doenjang-jjigae(된장찌개), jjamppong(짬뽕), nagasaki-champon(나가사끼짬뽕)`
const SCHEMA = {
  type: 'object',
  properties: { results: { type: 'array', items: { type: 'object', properties: {
    file: { type: 'string' },
    foods: { type: 'string', description: '실제 보이는 음식(한국어)' },
    matched_class: { type: 'string', description: '단일 메인이 맞는 taxo59 en명, 아니면 none' },
    category: { type: 'string', enum: ['single_in', 'multi', 'ood', 'scene_nonfood', 'borderline_dropped'] },
    keep: { type: 'boolean' },
    note: { type: 'string' },
  }, required: ['file', 'foods', 'matched_class', 'category', 'keep', 'note'] } } },
  required: ['results'],
}
const ITEMS = __ITEMS__
const BATCH = 6
const batches = []
for (let i = 0; i < ITEMS.length; i += BATCH) batches.push(ITEMS.slice(i, i + BATCH))
phase('Classify')
log(`${ITEMS.length}장 -> ${batches.length} 배치 단일요리+클래스 필터`)
const rows = await parallel(batches.map((batch, bi) => () => {
  const list = batch.map((f, j) => `  ${j + 1}. ${BASE}/${f}   (file=${f})`).join('\n')
  const prompt = `team_collected 실환경 사진을 한식탐지 모델 **학습용**으로 골라낸다. 기준: **① 한 사진에 메인요리 1개(단일) ② 그게 아래 59클래스에 맞음**. (파일명 믿지 말고 이미지로 판단 — 파일명이 음식과 다른 경우 많음)

taxo59 en(ko):
${CLASSES}

각 이미지를 Read로 보고:
- foods: 실제 보이는 음식(한국어)
- matched_class: 메인요리 정확히 1개가 59클래스와 맞으면 그 en명, 아니면 "none"
- category: single_in(메인1개+59클래스=유일 KEEP) / multi(메인2접시+·한상) / ood(음식이나 59에 없음, 예 오므라이스·잡채·디저트) / scene_nonfood(조리중·불판생고기·사람·비음식·흐림) / borderline_dropped(애매·드랍클래스)
- keep: single_in일 때만 true
- note: 한 줄 사유
규칙: 곁들이 반찬(김치·단무지·쌈채소)은 무시하고 메인1개 뚜렷하면 single_in. 같은음식 한접시(회모둠·초밥)도 single_in. 서로다른 메인 2접시+면 multi.

이미지 ${batch.length}장:
${list}
각 이미지 Read 후 StructuredOutput results[] (이미지당1개, file=주어진 file 그대로) 반환.`
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
js = TEMPLATE.replace("__ITEMS__", json.dumps(files, ensure_ascii=False))
OUT.write_text(js, encoding="utf-8")
print(f"WROTE {OUT} ({len(js)//1024}KB, 배치 {(len(files)+5)//6} 에이전트)")
