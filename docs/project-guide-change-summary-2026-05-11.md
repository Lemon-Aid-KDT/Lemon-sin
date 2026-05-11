# PROJECT_GUIDE.md 개발 범위 확정 반영 요약

팀 공유용 변경 요약입니다. 이번 변경은 코드 구현이 아니라 기획서와 브라우저용 가이드 동기화 변경입니다.

관련 커밋: `7ff06bd`

변경 파일:
- `PROJECT_GUIDE.md`
- `guide.html`

## 핵심 변경

- 기존 4개 Agent 구조를 `분석 알고리즘 + 3개 Agent` 구조로 수정했습니다.
- 분석은 Agent가 아니라 OCR/라벨링/CSV DB/API 매칭 기반 알고리즘 흐름으로 정리했습니다.
- 개인화·평가·챗봇 Agent는 분리하되 하나의 통합 흐름으로 작동하도록 정리했습니다.
- 이메일·구글·카카오·간편 로그인 범위를 반영했습니다.
- iOS HealthKit 우선, Android Health Connect는 검토 예정으로 정리했습니다.
- 영양제 CSV DB 우선 + API 보조 구조를 반영했습니다.
- Google Cloud Vision, YOLOv8은 확정 기술이 아니라 후보/논문 조사 대상으로 정리했습니다.
- 병원 데이터 연동과 민감정보 세부 기준은 멘토 질문으로 유지했습니다.
- 사진 분석 화면에는 출처를 직접 표시하지 않고, 챗봇/LLM 대화 안에서 출처를 표시하도록 정리했습니다.
- 건강 관련 이미지는 엄격 처리 대상으로 반영했습니다.
- 삭제 정책은 전체 삭제 요청 + 3개월 복구 가능 기간 후 완전 삭제로 정리했습니다.

## 검증

- `PYTHONIOENCODING=utf-8 python scripts/sync_guide.py --check` 통과
- `PROJECT_GUIDE.md`와 `guide.html` 동기화 확인
- 기존 충돌 표현 제거 확인:
  - `4개 Agent`
  - `분석 Agent`
  - `Kaggle`
  - `30일 grace`
  - `백업 90일`
  - `출처 페이지`
  - `중복 사진 차단`

## 참고

`guide.html`은 직접 HTML/CSS/JS를 수정하지 않고, `PROJECT_GUIDE.md` 내용을 `md-source` 블록에 동기화하는 방식으로 갱신했습니다.
