<!-- PR 제목은 Conventional Commits 형식 권장: feat(scope): subject -->

## 📝 작업 요약 (Summary)

<!-- 이 PR이 무엇을 하는지 1~3문장으로 요약 -->

## 🎯 작업 유형 (Type)

<!-- 해당하는 항목에 [x] 체크 -->

- [ ] ✨ feat: 새 기능
- [ ] 🐛 fix: 버그 수정
- [ ] 📝 docs: 문서 변경
- [ ] 🎨 style: 코드 스타일 (포매터)
- [ ] ♻️ refactor: 리팩토링
- [ ] ⚡ perf: 성능 개선
- [ ] ✅ test: 테스트 추가/수정
- [ ] 🔧 chore: 빌드, 설정
- [ ] 👷 ci: CI 설정

## 🔗 관련 이슈 (Related Issues)

<!-- 머지 시 자동 close 시키려면 Closes / Fixes / Resolves 키워드 사용 -->

Closes #

## 📋 변경 사항 상세 (Changes)

<!-- 무엇을 변경했는지 구체적으로 -->

-
-
-

## 🧪 테스트 (Testing)

<!-- 어떻게 테스트했는지 -->

- [ ] 단위 테스트 추가/수정
- [ ] 로컬에서 수동 테스트 완료
- [ ] CI 통과 확인

### 테스트 시나리오

<!-- 주요 시나리오 나열 -->

1.
2.

## ✅ 공통 체크리스트 (Checklist)

<!-- 머지 전 확인 -->

- [ ] 대상 브랜치 최신화 (rebase or merge)
- [ ] 커밋 메시지가 컨벤션을 따름
- [ ] 코드 린터·포매터 통과
- [ ] 단위 테스트 통과
- [ ] 새로운 의존성을 추가했다면 lockfile 또는 dependency 파일 업데이트
- [ ] 환경 변수가 추가되었다면 예시 env 문서 업데이트
- [ ] 관련 문서를 함께 업데이트 (필요 시)
- [ ] 민감정보(API 키, 비밀번호)를 커밋하지 않음

## 🧱 Lemon Healthcare P1 안정화 게이트 (해당 시)

<!-- 03_lemon_healthcare/yeong-Vision-Nutrition의 backend/data/config/AI/OCR/YOLO/학습 변경이면 확인 -->

- [ ] KDRIs/data/reference/config 변경 시 `python scripts/validate_kdris_dataset.py --require-approved` 통과
- [ ] JWT/OIDC/security 변경 시 production-path 테스트 통과
- [ ] 만성질환 우선순위 또는 사용자 노출 문구 변경 시 금지 표현 테스트 통과
- [ ] feature flag를 `true`로 바꾼 경우 sign-off 문서 링크와 production guard 테스트 포함
- [ ] OCR/LLM/이미지 변경 시 raw image/raw OCR text 저장 금지 확인

## 💬 리뷰어에게 (For Reviewers)

<!-- 리뷰어가 특별히 봐줬으면 하는 부분 -->

-

## 📌 추가 참고사항 (Notes)

<!-- 필요한 경우 추가 -->

-
