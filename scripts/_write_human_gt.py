"""사람 검수 완료된 7장의 GT 를 real_manifest.json 에 반영하는 일회성 스크립트.

Claude 멀티모달 시각 확인 결과. labeled=true + reviewer='claude-multimodal' 마킹.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent.parent / "data" / "ocr_eval" / "real_manifest.json"

HUMAN_GT: dict[str, dict[str, object]] = {
    "real_뇌_은행잎_002": {
        "language": "mixed",
        "gt_text": (
            "Dr.Lean\n"
            "WCS\n"
            "닥터린\n"
            "이노시톨 40:1\n"
            "Inositol\n"
            "이노시톨 4,000 mg (1포당)\n"
            "캐롭추출분말 100 mg (1포당)\n"
            "NOCHESTEM\n"
            "4.5 g x 30포 (135 g / 540 kcal)"
        ),
        "gt_fields": {
            "product_name": "닥터린 이노시톨 40:1",
            "ingredients": ["이노시톨", "캐롭추출분말"],
            "dosage": "4000mg",
        },
    },
    "real_비타민K_002": {
        "language": "en",
        "gt_text": (
            "LIFE EXTENSION®\n"
            "Bone Restore*\n"
            "Calcium Supplement with Vitamin K2\n"
            "GLUTEN FREE\n"
            "NON GMO LE CERTIFIED\n"
            "Supports Healthy Bones*\n"
            "120 CAPSULES\n"
            "DIETARY SUPPLEMENT"
        ),
        "gt_fields": {
            "product_name": "Bone Restore Calcium Supplement with Vitamin K2",
            "ingredients": ["Calcium", "Vitamin K2"],
            "dosage": None,
        },
    },
    "real_비타민C_002": {
        "language": "mixed",
        "gt_text": (
            "natural plus\n"
            "비타민C 1000 플러스\n"
            "VITAMIN C 1000 PLUS\n"
            "1일 섭취량 당 비타민C 1,000 mg 함유\n"
            "건강기능식품 1,100 mg x 300정 (330 g)"
        ),
        "gt_fields": {
            "product_name": "비타민C 1000 플러스",
            "ingredients": ["비타민C"],
            "dosage": "1000mg",
        },
    },
    "real_콜라겐_001": {
        "language": "mixed",
        "gt_text": (
            "CENOVIS\n"
            "콜라겐 비타민 젤리\n"
            "COLLAGEN VITAMIN JELLY\n"
            "석류맛"
        ),
        "gt_fields": {
            "product_name": "콜라겐 비타민 젤리",
            "ingredients": ["콜라겐", "비타민"],
            "dosage": None,
        },
    },
    "real_효소_소화_001": {
        "language": "mixed",
        "gt_text": (
            "natural plus\n"
            "파인애플 효소\n"
            "PINEAPPLE ENZYME\n"
            "파인애플과즙분말 10 %\n"
            "파인애플추출분말(브로멜라인 함유) 1.1 %\n"
            "15베리발효효소 2.15 %\n"
            "α-아밀라아제 680,000 unit/3g\n"
            "프로테아제 3,000 unit/3g\n"
            "효소식품\n"
            "3 g x 30포 (90 g / 351 kcal)\n"
            "HACCP\n"
            "식품안전관리인증\n"
            "식품의약품안전처"
        ),
        "gt_fields": {
            "product_name": "파인애플 효소",
            "ingredients": [
                "파인애플과즙분말",
                "파인애플추출분말",
                "15베리발효효소",
                "α-아밀라아제",
                "프로테아제",
            ],
            "dosage": None,
        },
    },
    "real_글루코사민_001": {
        "language": "mixed",
        "gt_text": (
            "natural plus\n"
            "SOMETHING SPECIAL FOR YOUR HEALTH!\n"
            "ARTICULAR CARTILAGE N GLUCOSAMINE\n"
            "VITAMIN D MANGANESE\n"
            "관절연골엔 글루코사민 비타민D 망간\n"
            "GLUCOSAMINE SULFATE\n"
            "1500mg per day\n"
            "건강기능식품\n"
            "관절 및 연골 건강에 도움을 줄 수 있음\n"
            "1일 섭취량 당 글루코사민 황산염 1,500 mg 함유\n"
            "글루코사민, 비타민D, 망간\n"
            "1,350 mg x 120정 (162 g)"
        ),
        "gt_fields": {
            "product_name": "관절연골엔 글루코사민 비타민D 망간",
            "ingredients": ["글루코사민", "비타민D", "망간"],
            "dosage": "1500mg",
        },
    },
    "real_식이섬유_001": {
        "language": "mixed",
        "gt_text": (
            "종근당\n"
            "장건강 프로젝트 365\n"
            "차전자피 식이섬유환\n"
            "INTESTINE CARE PROJECT 365\n"
            "식약처 기능성 인정 원료\n"
            "1일 섭취량 9 g당 식이섬유 5 g 함유\n"
            "배변활동 원활에 도움을 줄 수 있음\n"
            "건강기능식품\n"
            "4.5 g x 30포 (135 g)"
        ),
        "gt_fields": {
            "product_name": "장건강 프로젝트 365 차전자피 식이섬유환",
            "ingredients": ["차전자피", "식이섬유"],
            "dosage": "5g",
        },
    },
}


def main() -> int:
    """manifest 를 in-place 로 update.

    macOS HFS/외장 드라이브에서 가져온 manifest IDs 는 NFD(분해형) 한글이라
    Python literal(NFC) 와 직접 매치되지 않는다. 양쪽을 NFC 로 정규화해 비교 +
    manifest IDs 도 NFC 로 저장한다 (downstream 일관성).
    """
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    gt_by_nfc = {unicodedata.normalize("NFC", k): v for k, v in HUMAN_GT.items()}
    updated = 0
    for item in m["items"]:
        nfc_id = unicodedata.normalize("NFC", item["id"])
        item["id"] = nfc_id  # downstream 호출에서 안정된 NFC 형식 보장
        # 카테고리·source_path 도 NFC 로 정규화
        if "category" in item:
            item["category"] = unicodedata.normalize("NFC", item["category"])
        if "image_path" in item:
            item["image_path"] = unicodedata.normalize("NFC", item["image_path"])
        if nfc_id in gt_by_nfc:
            gt = gt_by_nfc[nfc_id]
            item["language"] = gt["language"]
            item["gt_text"] = gt["gt_text"]
            item["gt_fields"] = gt["gt_fields"]
            item["labeled"] = True
            item["reviewer"] = "claude-multimodal"
            updated += 1
    m["labeled_count"] = sum(1 for it in m["items"] if it.get("labeled"))
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Updated {updated} items. labeled_count={m['labeled_count']}/{m['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
