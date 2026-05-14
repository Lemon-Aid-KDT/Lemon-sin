# Evidence Tags

이 폴더는 Lemon Aid 자료를 구현 기준으로 쓸 수 있는지, 팀 학습용으로만 써야 하는지
구분하기 위한 태그별 정리 문서입니다.

## 읽는 순서

| 문서 | 태그 | 목적 |
|------|------|------|
| [01-kr-official.md](./01-kr-official.md) | `KR_OFFICIAL` | 구현 기준 가능 자료 |
| [02-kr-clinical-guide.md](./02-kr-clinical-guide.md) | `KR_CLINICAL_GUIDE` | 팀 학습/전문가 검토용 자료 |
| [03-kr-research.md](./03-kr-research.md) | `KR_RESEARCH` | 한국 사용자 맥락/배경 근거 |
| [04-global-review.md](./04-global-review.md) | `GLOBAL_REVIEW` | 최신 동향/배경 근거 |
| [05-global-tech.md](./05-global-tech.md) | `GLOBAL_TECH` | AI, OCR, 추천 시스템 구현 참고 |
| [06-not-for-rule.md](./06-not-for-rule.md) | `NOT_FOR_RULE` | 사용자별 건강 판단 규칙화 금지 |

## 태그 선택 기준

- `KR_OFFICIAL`: DB, 알고리즘 기준값, 앱 내 출처 표시에 사용할 수 있는 국내 공식 자료
- `KR_CLINICAL_GUIDE`: 질환 이해와 전문가 검토 기준으로 참고하되, 앱이 치료·처방 판단을 하지 않도록 제한할 자료
- `KR_RESEARCH`: 한국 사용자, 한식, 고령자, 만성질환 맥락을 설명하는 배경 자료
- `GLOBAL_REVIEW`: 정밀영양, 디지털 헬스, AI 의료 안전성의 최신 동향을 이해하기 위한 자료
- `GLOBAL_TECH`: OCR, 음식 인식, LLM 평가, human-in-the-loop 설계에 참고할 기술 자료
- `NOT_FOR_RULE`: 논문·진료지침·LLM 추론 결과를 사용자별 건강 판단 규칙으로 오용하지 않기 위한 금지 목록

## 공통 원칙

- 구현 기준은 `KR_OFFICIAL` 자료를 우선합니다.
- 논문과 진료지침은 사용자별 진단, 치료, 처방, 복용량 변경 지시로 바꾸지 않습니다.
- 원문 접근이 제한된 자료는 `원문 확인 필요`로 표시하고 구현 기준으로 사용하지 않습니다.
- 사용자 화면 문구는 [Compliance & Safety Guide](../../guide/08-compliance-safety.md)를 통과해야 합니다.
