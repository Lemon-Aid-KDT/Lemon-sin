# Supplement label fixtures

영양제 라벨 사진 fixture 디렉토리. PaddleOCR + Ollama LLM 통합 테스트, M-3-V.B
sim 매뉴얼 사이클, M-3-V.C 오류 시나리오 검증에 사용한다.

---

## 명명 규칙

| 접두사 | 출처 | 예 |
|---|---|---|
| `local-` | 사용자가 직접 촬영 (저작권 자체 보유) | `local-multivitamin-0001.jpg` |
| `naver-live-` | 네이버 라이브 커머스 스크린샷 (참고용, 라이선스 검토 필요) | `naver-live-0001.jpg` |
| `synthetic-` | 합성/AI 생성 라벨 (실제 제품과 무관) | `synthetic-omega3-0001.png` |

파일명: `<출처접두사>-<카테고리>-<NNNN>.<확장자>`
- 카테고리 예: `multivitamin`, `omega3`, `probiotics`, `vitamin-d`, `calcium`
- NNNN: 4자리 순번 (0001 부터)

---

## 권장 fixture 세트 (M-3-V.B 5 시나리오)

| 시나리오 | 파일명 (제안) | 용도 |
|---|---|---|
| A | `local-multivitamin-0001.jpg` | 일반 OCR + 다성분 파싱 |
| B | `local-omega3-0001.jpg` | 영문/한글 혼합 라벨 |
| C | `local-probiotics-0001.jpg` | **긴 OCR text — M-3-V.A read_timeout 검증 핵심** |
| D | `local-vitamin-d-0001.jpg` | 작은 라벨 (OCR 신뢰도 낮음 케이스) |
| E | `local-calcium-0001.jpg` | 영문 비중 높은 라벨 |

각 이미지는 **JPEG / 5MB 이하 / 라벨 영역이 명확히 잡힌** 사진을 권장.

---

## 라이선스 / 개인정보 가이드

### ✅ 허용
- 본인이 구입한 제품을 직접 촬영한 사진 (저작권 자체 보유)
- 합성 라벨 (LLM 생성 가짜 라벨 — 실 제품과 무관)
- public domain / CC0 라이선스 이미지

### ⚠️ 검토 후 사용
- 쇼핑몰 상세페이지 스크린샷 — 공정사용 범위 내에서만 (테스트 fixture 한정,
  유출/재배포 금지)
- 제조사 공식 제품 이미지 — 라이선스 확인 후

### ❌ 금지
- 타인 SNS / 블로그 게시 사진 (사적 저작물)
- 의약품 (식약처 일반의약품 분류 — 영양제 외)
- 약사법상 광고 제한 카테고리 (의약외품 중 효능 주장 포함)

### 개인정보 제거
- 사진에 사람 / 손가락 / 배경 인물이 보이면 **반드시 모자이크 또는 크롭**
- 메타데이터 (EXIF GPS 등) 는 commit 전 제거:
  ```bash
  exiftool -all= local-*.jpg
  ```

---

## 사용 예

### Python 통합 테스트
```python
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "supplement_labels"
image_path = FIXTURE_DIR / "local-multivitamin-0001.jpg"
with image_path.open("rb") as f:
    image_bytes = f.read()
```

### M-3-V.C shell script
```bash
curl -F "image=@tests/fixtures/supplement_labels/local-multivitamin-0001.jpg" ...
```

---

## 디렉토리 보존

이미지 commit 전이라도 디렉토리 자체는 보존되어야 한다 (이 README.md 가 그
역할). 새 fixture 를 추가할 때마다 위 명명 규칙 + 라이선스 출처를
[FIXTURES_LOG.md](./FIXTURES_LOG.md) (선택, 추후 도입) 또는 commit 메시지에 명시.

## 참조

- M-3-V.A 통합 테스트: [test_ollama_timeout_e2e.py](../../integration/llm/test_ollama_timeout_e2e.py)
- M-3-V.B sim cycle guide: [docs/track-d/m3v-sim-cycle-guide.md](../../../../docs/track-d/m3v-sim-cycle-guide.md) (생성 예정)
- M-3-V.C error scenarios: [docs/track-d/m3v-c-error-scenarios.md](../../../../docs/track-d/m3v-c-error-scenarios.md) (생성 예정)
