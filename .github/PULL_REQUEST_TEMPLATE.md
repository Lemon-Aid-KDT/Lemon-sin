<!--
Commit title suggestion:
Use Conventional Commits, for example:
- feat(backend): add KDRI validation endpoint
- fix(data): prevent stale nutrition reference ingestion
- docs(ci): document PR validation gates

Explain why the change is needed in the commit body when committing.
-->

## Summary
- 변경 요약을 작성합니다.

## Change Type
- [ ] feat
- [ ] fix
- [ ] docs
- [ ] refactor
- [ ] test
- [ ] chore

## Validation
- [ ] Tests or smoke checks were run locally
- [ ] Documentation was updated, or no documentation change is needed
- [ ] No secrets or private health data were committed

## Lemon Healthcare P1 Gates
<!-- Check affected areas under 03_lemon_healthcare/Lemon-Aid. -->
- [ ] Backend changes keep Pydantic validation and API error handling explicit
- [ ] Nutrition/KDRIs/reference data changes include source and schema validation notes
- [ ] OCR/AI-agent changes preserve user-confirmation boundaries and avoid direct regulated advice
- [ ] Config changes are reflected in `.env.example` and docs

## Screenshots / Evidence
- 검증 로그, 스크린샷, 또는 재현 근거를 첨부합니다.
