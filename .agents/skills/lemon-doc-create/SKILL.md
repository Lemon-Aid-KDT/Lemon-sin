# Lemon 문서 생성

사용자가 Lemon Aid 문서 생성, 이동, 재구성을 요청했을 때 이 skill을 사용합니다.

## 워크플로

1. 문서 목적, 독자, 사용 시점을 파악합니다.
2. 목적 기준으로 위치를 정합니다.
   - 제품 또는 개발 기준: `docs/guide/`
   - 도메인 학습: `docs/domain/`
   - 리서치 또는 근거: `docs/research/`
   - 검토 또는 의사결정 보고서: `docs/reports/`
   - 실행 부록: `docs/appendices/`
   - 발표 산출물: `docs/presentations/<topic>/`
3. 파일명은 kebab-case를 사용합니다.
4. `docs/README.md`와 대상 폴더의 `README.md`를 갱신합니다.
5. 기존 문서를 이동하기 전에는 `rg`로 참조를 검색합니다.

## 가드레일

- 기존 문서 카테고리가 명확히 맞지 않을 때만 새 카테고리를 제안합니다.
- `guide.html`은 직접 수정하지 않습니다.
- 전체 체크아웃에서 `PROJECT_GUIDE.md`를 바꿨다면 변경 후
  `python scripts/sync_guide.py --check`를 실행합니다.
