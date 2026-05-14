# Research 자료 정리

> 문서 정보
>
> - 작성일: 2026-05-11
> - 목적: Lemon Aid 기획, DB 설계, AI Agent, OCR/이미지 처리, 알고리즘, UI/UX, 멘토 질문에 사용한 근거 자료를 안전하게 분류한다.
> - 성격: 최종 논문 리뷰가 아니라, 후속 분석과 구현 판단을 위한 근거 관리 문서다.

## 1. 정리 원칙

이 문서는 참고 자료를 단순 목록으로 모으지 않고, **우리 프로젝트에서 어디에 쓸 수 있고 어디에 쓰면 안 되는지**를 기준으로 분류한다.

핵심 원칙:

- 논문과 특허는 LLM 파인튜닝 학습 데이터로 쓰지 않는다.
- 논문 속 상관관계를 사용자 맞춤 건강 판단 규칙으로 바로 쓰지 않는다.
- DB에는 논문 전문이 아니라 출처 메타데이터, 공식 기준, 검증된 룩업 데이터만 저장한다.
- 사용자에게 보이는 건강 판단은 공식 기준, 사용자 입력, 검증된 DB, 안전 문구를 우선한다.
- 이미지 처리는 참고자료로 모델을 학습시키는 것이 아니라, OCR 결과를 어떤 DB와 매칭하고 어떤 상태값으로 관리할지 정하는 데 사용한다.

주의: 아래 자료는 Lemon Aid의 기획·기술 근거로 사용하되, 질병 진단, 치료, 처방, 복용량 변경 지시의 근거로 사용하지 않는다.

## 2. 근거 등급

| 등급 | 의미 | 사용 가능 | 사용 금지 |
|------|------|-----------|-----------|
| A. 공식 기준 | KDRIs, 식약처, 농진청 등 공공·공식 데이터 | DB 저장, 알고리즘 기준, 사용자 화면 출처 | 공식 범위를 넘어 질환 치료 효과로 확장 |
| A-2. 공식 건강정보 | 질병관리청 국가건강정보포털 등 공공 건강정보 | 팀 내부 학습용 질환 정의, 질환 기본 설명, 사용자 문구 안전선 참고 | 사용자 상태 진단, 치료·처방 판단, 질환별 식단 처방 규칙 |
| B. 구현 참고 | 연구보고서, 특허, UI/UX 논문 | DB 구조·화면 흐름·알고리즘 설계 참고 | 특허/논문 알고리즘을 그대로 복제하거나 의료 판단 규칙으로 사용 |
| C. 배경 근거 | 보건영양, 정밀영양 리뷰, 문제 정의 논문 | 기획 배경, 멘토 설명, 필요성 근거 | 사용자별 건강 권고의 직접 기준 |
| D. 검토 필요 | 메타데이터 불완전 자료, 본문 미확인 PDF | 후속 분석 후보 | 구현·DB·LLM 프롬프트에 반영 |

## 3. 핵심 결론

| 결론 | 안전한 프로젝트 반영 |
|------|----------------------|
| 만성질환 예방과 관리는 식생활 개선과 밀접하다. | 서비스 배경과 문제 정의에 사용한다. 특정 질환 치료 효과로 표현하지 않는다. |
| 개인별 식이 반응과 건강 상태가 달라 일괄 권장만으로는 부족하다. | 개인화 Agent의 필요성 근거로 사용한다. LLM이 독자적으로 건강 판단을 내리는 근거로 쓰지 않는다. |
| 한식 기반 균형식단 추천과 식품영양 DB 표준화 연구가 있다. | 식품 DB 정규화, 식품군 분류, 후보 식단 UX 참고로 사용한다. 자동 식단 처방으로 구현하지 않는다. |
| 고령자와 만성질환자는 영양소 섭취 상태와 질환 유병의 관계를 함께 봐야 한다. | 1차 페르소나와 멘토 질문 근거로 사용한다. 질환별 영양소 룰로 바로 저장하지 않는다. |
| 기존 AI 식단·운동 앱은 단순 인식·기록에 머무는 경우가 많다. | Lemon Aid의 차별화와 UI/UX 설계 근거로 사용한다. OCR 결과를 사용자 확인 없이 확정하지 않는다. |

## 4. 프로젝트 적용 매핑

| 자료 | 등급 | DB | LLM/RAG | 이미지/OCR | 알고리즘 | UI/UX | 안전/검증 |
|------|------|----|---------|------------|----------|-------|-----------|
| 질병관리청 국가건강정보포털 질환 정의 자료 | A-2 | 문헌 메타데이터만 | 팀 학습·내부 설명 참고 | 해당 없음 | 직접 규칙화 금지 | 사용자 표현 안전선 참고 | 진단·치료 표현 방지 기준 |
| 서울대학교 보건영양연구실 | C | 문헌 메타데이터만 | 배경 설명 참고 | 해당 없음 | 직접 사용 안 함 | 해당 없음 | 예방·관리 표현 근거 |
| Precision nutrition for cardiometabolic diseases | C | 문헌 메타데이터만 | 개인화 필요성 설명 참고 | 해당 없음 | 직접 규칙화 금지 | 해당 없음 | 정밀영양 한계 설명 |
| 빅데이터 기반 건강 식단 추천 시스템 연구 | B | 식품군·영양 DB 구조 참고 | 식단 설명 근거 후보 | 음식명 매칭 구조 간접 참고 | 식단 추천 구조 참고 | 후보/교체 흐름 참고 | 자동 추천 제한 근거 |
| 체중조절 개인 맞춤형 균형식단 추천 특허 | B | 문헌 메타데이터만 | 직접 사용 안 함 | 해당 없음 | 에너지필요량·식품군 흐름 참고 | 후보 식단 승인 UX 참고 | 복제 금지·범위 제한 |
| 고령자의 만성질환과 영양소 섭취 관계 | C | 문헌 메타데이터만 | 설명 톤 참고 가능 | 해당 없음 | 직접 규칙화 금지 | 해당 없음 | 상관관계 오용 방지 |
| 한국 노인의 영양성 빈혈과 만성질환 관련 연구 | C | 문헌 메타데이터만 | 설명 톤 참고 가능 | 해당 없음 | 직접 규칙화 금지 | 해당 없음 | 진단 표현 금지 근거 |
| 인공지능 기반 식단·운동 UI/UX 연구 | B | 문헌 메타데이터만 | 직접 사용 안 함 | OCR 입력 흐름 참고 | 직접 사용 안 함 | 정보구조·대시보드 참고 | 사용성 검증 참고 |
| KoreaScience / ScienceON DIKO / 미확인 PDF | D | 반영 금지 | 반영 금지 | 반영 금지 | 반영 금지 | 반영 금지 | 제목·초록 확인 전 사용 금지 |

## 5. DB 반영 기준

DB에 넣어도 되는 것:

- 식품명, 식품군, 영양소, 1회 제공량, 출처 코드
- 건강기능식품 성분, 함량, 단위, 식약처 인정 기능성
- KDRIs 권장 섭취량, 상한섭취량, 연령·성별 기준
- 사용자 입력 식단·영양제·프로필·동의 이력
- 근거 문헌의 제목, URL, 자료 성격, 근거 등급, 사용 목적

DB에 바로 넣지 않는 것:

- 논문 전문
- 논문 속 질환-영양소 상관관계
- 특허의 상세 알고리즘
- "당뇨에는 어떤 영양소가 좋다" 같은 미검증 규칙
- 의료자문위 검토 전 질환별 복용량·섭취량 보정 규칙

권장 DB 관점:

- `foods`, `supplements`, `supplement_ingredients`에는 공식·공공 데이터만 우선 저장한다.
- `agent_memory`에는 사용자별 요약만 저장하고, 논문 결론을 사용자 맞춤 판단처럼 저장하지 않는다.
- 별도 근거 관리가 필요하면 `evidence_sources` 같은 문헌 메타데이터 테이블을 두되, 본문 전문이 아니라 출처와 사용 목적만 저장한다.

## 6. LLM/RAG 사용 기준

본 자료들은 LLM 파인튜닝 학습 데이터가 아니다. Lemon Aid에서 LLM은 OCR·텍스트 구조화와 설명 보조에 사용하며, 건강 판단 기준은 공식 DB와 검증된 알고리즘에 둔다.

허용:

- OCR 텍스트를 정해진 Pydantic JSON으로 구조화
- 식품명·성분명 후보 정규화
- 공식 DB와 KDRIs 결과를 쉬운 말로 설명
- 사용자 승인 전 미리보기 문구 생성
- 자료의 제목·URL·근거 등급을 RAG 후보 메타데이터로 참조

금지:

- 논문을 기반으로 새로운 건강 권고 생성
- 질환별 복용량 또는 섭취량 추천
- 특정 영양제·의약품 추천
- "이 성분이 질환을 개선한다" 같은 치료 효과 단정
- 사용자가 입력하지 않은 검사값·질환·복약 정보 추정

프롬프트 원칙:

- "논문에 따르면"을 사용자 화면에 직접 노출하지 않는다.
- "진단", "처방", "치료", "개선 보장" 표현은 금지한다.
- LLM 응답은 `08-compliance-safety.md`의 표현 가이드를 통과해야 한다.

## 7. 이미지/OCR 사용 기준

MVP에서 하는 것:

- Google Vision / CLOVA OCR로 영양제 라벨·음식 관련 텍스트 추출
- OCR 결과를 식약처·농진청·영양제 DB와 매칭
- confidence가 낮으면 사용자 수정 요청
- 원본 이미지, OCR 원문, 정규화 결과, 사용자 승인 상태를 분리 관리

MVP에서 하지 않는 것:

- 논문 PDF나 참고자료로 이미지 모델 학습
- 음식 사진만 보고 섭취량 확정
- OCR 결과를 사용자 확인 없이 최종 식단·영양제 기록으로 저장
- 처방전·검사표 이미지를 멘토 확인 없이 정식 입력 범위에 포함

자료 사용 방식:

- UI/UX 논문은 카메라 입력, 미리보기, 사용자 수정 흐름의 참고 자료로만 쓴다.
- 식단 추천 연구는 OCR로 얻은 음식명을 어떤 식품 DB와 매칭할지 정하는 간접 근거로 쓴다.
- 공식 식품·영양 DB만 실제 매칭 기준으로 쓴다.

## 8. 자료별 정리

### 8.1 서울대학교 보건영양연구실

- 출처: <https://sites.google.com/view/snuphn/home>
- 등급: C. 배경 근거
- 자료 성격: 보건영양 연구실 소개 및 보건영양학 설명 자료
- 핵심 내용: 보건영양은 영양학 지식을 보건 분야에 활용하는 학문이며, 만성질환 증가 이후 식생활 개선과 예방적 접근의 중요성이 커졌다고 설명한다.
- 프로젝트 적용:
  - DB: 문헌 메타데이터만 저장 가능
  - LLM/RAG: 기획 배경 설명 참고 가능
  - 이미지/OCR: 사용 안 함
  - 알고리즘: 사용 안 함
  - UI/UX: 사용 안 함
  - 안전/검증: "예방·관리 중심" 서비스 배경 설명에 사용
- 사용하면 안 되는 방식: 특정 기능, 알고리즘, 건강 판단의 정량 근거로 쓰지 않는다.
- MVP 반영: 멘토용 기획서의 배경 설명
- v2 이후 검토: 보건영양 관점의 교육 콘텐츠 근거로 확장 가능

### 8.2 Precision nutrition for cardiometabolic diseases

- 출처: <https://pubmed.ncbi.nlm.nih.gov/40307513/>
- 등급: C. 배경 근거
- 논문 정보: Guasch-Ferre et al., Nature Medicine, 2025, PMID 40307513, DOI 10.1038/s41591-025-03669-9
- 자료 성격: 심혈관대사질환 영역의 정밀영양 리뷰 논문
- 핵심 내용: 디지털 도구와 AI 발전으로 개인별 식이 반응 차이를 더 세밀하게 이해할 수 있게 되었고, 전통적인 일괄 식이지침을 보완하는 정밀영양 접근이 논의되고 있다.
- 프로젝트 적용:
  - DB: 문헌 메타데이터만 저장 가능
  - LLM/RAG: 개인화 필요성 설명 참고 가능
  - 이미지/OCR: 사용 안 함
  - 알고리즘: 직접 규칙화 금지, 개인화 방향성 근거로만 사용
  - UI/UX: 사용 안 함
  - 안전/검증: 정밀영양도 한계가 있다는 설명 근거
- 사용하면 안 되는 방식: LLM이 이 논문을 근거로 사용자별 식단·영양제 권고를 새로 만들게 하지 않는다.
- MVP 반영: 개인화 Agent의 필요성 설명
- v2 이후 검토: 의료자문위 검토 후 개인화 근거 수준 분류에 활용

### 8.3 빅데이터 기반 건강 식단 추천 시스템 연구

- 출처:
  - ScienceON 원문: <https://scienceon.kisti.re.kr/commons/util/originalView.do?cn=TRKO202300028164&dbt=TRKO&rn=>
  - NTIS 상세: <https://www.ntis.go.kr/outcomes/popup/srchTotlRschRpt.do?cmd=get_contents&rstId=REP-2022-01113017257>
- 등급: B. 구현 참고
- 자료 성격: 농촌진흥청 지원 연구보고서
- 기본 정보: 등록번호 TRKO202300028164, 발행년월 2022-12, 발행기관 성신여자대학교
- 핵심 내용: 식품·영양 관련 빅데이터 표준화, 생애주기별 맞춤형 식단모형, 질환별 개인 맞춤형 AI 식단추천 시스템 알고리즘 개발을 목표로 한다.
- 프로젝트 적용:
  - DB: 식품·영양 DB 표준화와 식품군 분류 구조 참고
  - LLM/RAG: 식단 설명 근거 후보로만 사용, 판단 생성 금지
  - 이미지/OCR: OCR로 얻은 음식명을 식품 DB에 매칭할 때 간접 참고
  - 알고리즘: 한식 기반 식단 추천 구조와 입력·출력 설계 참고
  - UI/UX: 후보 식단, 교체, 사용자 확인 흐름 참고
  - 안전/검증: 자동 추천보다 사용자 확인형 추천으로 제한하는 근거
- 사용하면 안 되는 방식: 연구보고서의 질환별 식단 추천 기준을 검토 없이 Lemon Aid 룰 테이블로 저장하지 않는다.
- MVP 반영: 식품 DB 매칭, 식품군 분류, 식단 분석 근거 설명
- v2 이후 검토: 자동 식단 후보, 음식 교체 추천, 질환위험인자별 고도화

### 8.4 체중조절 개인 맞춤형 균형식단 추천 방법 및 장치

- 출처:
  - ScienceON 특허: <https://scienceon.kisti.re.kr/srch/selectPORSrchPatent.do?cn=KOR1020190039019>
  - Google Patents: <https://patents.google.com/patent/KR102422591B1/ko>
- 등급: B. 구현 참고
- 자료 성격: 개인 맞춤형 균형식단 추천 특허
- 기본 정보: KR102422591B1, 성신여자대학교 연구 산학협력단, 공개/등록 2022-07-20
- 핵심 내용: 사용자 정보로 1일 에너지필요량을 결정하고, 아침식사 유형, 후보 균형식단, 교체 가능 음식 리스트, 최종 균형식단 제공 흐름을 포함한다.
- 프로젝트 적용:
  - DB: 문헌 메타데이터만 저장 가능
  - LLM/RAG: 사용 안 함
  - 이미지/OCR: 사용 안 함
  - 알고리즘: 에너지필요량, 식품군, 후보 식단 흐름 참고
  - UI/UX: 후보 식단 제시 후 사용자 승인·교체 흐름 참고
  - 안전/검증: 동일 구현 복제 금지, 참고 범위 제한
- 사용하면 안 되는 방식: 특허 청구항의 상세 알고리즘을 그대로 구현하거나 서비스 차별화 문구로 과장하지 않는다.
- MVP 반영: 사용자 확인/교체 UX 원칙
- v2 이후 검토: 식단 후보 추천 기능 검토 시 특허 회피와 법적 검토 필요

### 8.5 고령자의 만성질환과 영양소 섭취 관계 연구

- 출처: <https://www.dbpia.co.kr/journal/detail?nodeId=T16984706>
- 등급: C. 배경 근거
- 자료 성격: 학위논문
- 기본 정보: 김연정, 숙명여자대학교 교육대학원, 2024
- 핵심 내용: 제8기 국민건강영양조사 2021년 자료를 활용해 65세 이상 노인의 고혈압, 이상지질혈증, 뇌졸중, 골다공증, 당뇨병 유병 여부와 영양소 섭취량의 관계를 분석했다.
- 프로젝트 적용:
  - DB: 문헌 메타데이터만 저장 가능
  - LLM/RAG: 만성질환자 설명 톤 참고 가능
  - 이미지/OCR: 사용 안 함
  - 알고리즘: 직접 규칙화 금지, 문제 정의 근거로만 사용
  - UI/UX: 사용 안 함
  - 안전/검증: 상관관계와 인과관계를 구분해야 한다는 근거
- 사용하면 안 되는 방식: 특정 영양소를 특정 질환 개선·예방 규칙으로 저장하지 않는다.
- MVP 반영: 만성질환자 맞춤 관리 필요성 설명
- v2 이후 검토: 의료자문위 검토 후 주의 영양소 룰 후보로 검토 가능

### 8.6 한국 노인의 영양성 빈혈 유병 여부에 따른 영양소 섭취 상태와 만성질환 관련성 연구

- 출처: <https://www.dbpia.co.kr/journal/detail?nodeId=T15096410>
- 등급: C. 배경 근거
- 자료 성격: 학위논문
- 기본 정보: 한소희, 인하대학교 대학원, 2019
- 핵심 내용: 제6기 국민건강영양조사 2013-2015 자료를 활용해 65세 이상 노인의 영양성 빈혈 여부에 따른 영양소 섭취 상태와 만성질환 관련성을 분석했다.
- 프로젝트 적용:
  - DB: 문헌 메타데이터만 저장 가능
  - LLM/RAG: 영양 취약성 설명 참고 가능
  - 이미지/OCR: 사용 안 함
  - 알고리즘: 직접 규칙화 금지, 고령자 영양 취약성 근거로만 사용
  - UI/UX: 사용 안 함
  - 안전/검증: "빈혈 진단" 표현 금지 근거
- 사용하면 안 되는 방식: 앱 화면에서 "빈혈 위험"을 판정하거나 질환 위험도를 계산하는 근거로 쓰지 않는다.
- MVP 반영: "섭취량이 낮을 가능성", "전문가 상담 권장" 표현 근거
- v2 이후 검토: 의료자문위 검토 후 영양 취약성 체크리스트 후보로 검토 가능

### 8.7 인공지능 기반의 식단과 운동 코칭 기획 모델 모바일 애플리케이션 UI/UX디자인 연구

- 로컬 파일: `C:\Users\KDS13\OneDrive\문서\카카오톡 받은 파일\인공지능 기반의 식단과 운동 코칭 기획 모델.pdf`
- 공개 메타데이터:
  - Google Books: <https://books.google.com/books/about/%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5_%EA%B8%B0%EB%B0%98%EC%9D%98_%EC%8B%9D%EB%8B%A8%EA%B3%BC_%EC%9A%B4%EB%8F%99.html?id=sbClzwEACAAJ>
  - 국회도서관: <https://dl.nanet.go.kr/detail/KDMT12021000034845>
- 등급: B. 구현 참고
- 자료 성격: 박사학위논문, AI 식단·운동 앱 UI/UX 설계 연구
- 기본 정보: 정다희, 한양대학교 대학원, 2021
- 핵심 내용: 기존 AI 식단·운동 앱은 음식 인식, 칼로리 계산, 기록 기능에 머무는 경우가 많고, 개인 맞춤형 목표·식단·운동 코칭과 사용성 설계가 중요하다고 본다.
- 프로젝트 적용:
  - DB: 문헌 메타데이터만 저장 가능
  - LLM/RAG: 사용 안 함
  - 이미지/OCR: OCR 기반 건강정보 입력과 사용자 수정 흐름 참고
  - 알고리즘: 직접 사용 안 함
  - UI/UX: 대시보드, 시각화, 사용성 평가 항목 참고
  - 안전/검증: 사용성 검증 기준 참고
- 사용하면 안 되는 방식: 운동 처방, 자세 교정, 인바디 기반 코칭을 Lemon Aid MVP 범위에 끌어오지 않는다.
- MVP 반영: 분석 결과 미리보기, 사용자 수정, 한 화면 요약 UX
- v2 이후 검토: 동기부여 UI, 모션·시각화 고도화

### 8.8 KoreaScience 자료

- 출처: <https://koreascience.kr/article/CFKO202233649334366.pub?lang=ko&orgId=kips>
- 등급: D. 검토 필요
- 자료 성격: 학술발표 또는 논문 페이지로 추정
- 현재 상태: 웹 메타데이터 추가 확인 필요
- 프로젝트 적용:
  - DB: 반영 금지
  - LLM/RAG: 반영 금지
  - 이미지/OCR: 반영 금지
  - 알고리즘: 반영 금지
  - UI/UX: 반영 금지
  - 안전/검증: 반영 금지
- 사용하면 안 되는 방식: 제목·저자·초록 확인 전 Lemon Aid 근거로 인용하지 않는다.
- MVP 반영: 없음
- v2 이후 검토: 메타데이터 확인 후 등급 재분류

### 8.9 ScienceON DIKO0016085589

- 출처: <https://scienceon.kisti.re.kr/srch/selectPORSrchArticle.do?cn=DIKO0016085589>
- 등급: D. 검토 필요
- 자료 성격: 학위논문 페이지로 추정
- 현재 상태: 제목·초록·원문 메타데이터 확인 필요
- 프로젝트 적용:
  - DB: 반영 금지
  - LLM/RAG: 반영 금지
  - 이미지/OCR: 반영 금지
  - 알고리즘: 반영 금지
  - UI/UX: 반영 금지
  - 안전/검증: 반영 금지
- 사용하면 안 되는 방식: 로컬 PDF와 동일 자료인지 확인 전 근거로 사용하지 않는다.
- MVP 반영: 없음
- v2 이후 검토: DBpia, RISS, 국회도서관 등 대체 메타데이터와 교차 확인

### 8.10 빅데이터기반건강식단추천시스템연구.pdf

- 로컬 파일: `C:\Users\KDS13\OneDrive\문서\카카오톡 받은 파일\빅데이터기반건강식단추천시스템연구.pdf`
- 등급: B. 구현 참고
- 자료 성격: `TRKO202300028164` 연구보고서 원문 PDF로 추정
- 프로젝트 적용:
  - DB: 식품·영양 DB 종류, 식품군 분류, 표준화 방식 확인 후 참고
  - LLM/RAG: 식단 설명 근거 후보로만 사용
  - 이미지/OCR: 음식명-식품 DB 매칭 구조 간접 참고
  - 알고리즘: 입력값·출력값·추천 흐름 분석 후 참고
  - UI/UX: 후보 식단 제시 흐름 참고 가능
  - 안전/검증: 자동 추천을 사용자 확인형으로 제한
- 사용하면 안 되는 방식: 원문 확인 전 세부 알고리즘을 이미 확정된 구현 기준처럼 쓰지 않는다.
- MVP 반영: 식품 DB 매칭과 식단 분석 근거
- v2 이후 검토: 식단 후보 추천, 음식 교체 추천

### 8.11 05 (특집_정성근).pdf

- 로컬 파일: `C:\Users\KDS13\OneDrive\문서\카카오톡 받은 파일\05 (특집_정성근).pdf`
- 등급: D. 검토 필요
- 자료 성격: 특집 PDF
- 현재 상태: 본문 제목·초록 확인 필요
- 프로젝트 적용:
  - DB: 반영 금지
  - LLM/RAG: 반영 금지
  - 이미지/OCR: 반영 금지
  - 알고리즘: 반영 금지
  - UI/UX: 반영 금지
  - 안전/검증: 반영 금지
- 사용하면 안 되는 방식: 제목·저자·발행처 확인 전 기획 근거로 사용하지 않는다.
- MVP 반영: 없음
- v2 이후 검토: PDF 첫 페이지 확인 후 배경·정책·기술 동향 중 하나로 재분류

### 8.12 내부 기준 문서: API 및 논문 근거 정리와 알고리즘 수정 방안

- 로컬 파일: `C:\MyWorkspace\lemon_aid\changmin-plan\docs\research\17-api-paper-algorithm-rationale.html`
- 등급: B. 구현 참고
- 자료 성격: 내부 기술 설계 및 알고리즘 근거 문서
- 핵심 내용: API, SDK, 공식 데이터, 논문 근거를 사용 이유·수정 사유·적용 방안 중심으로 정리한다.
- 프로젝트 적용:
  - DB: 공식 데이터와 문헌 메타데이터 분리 원칙 참고
  - LLM/RAG: 구조화 출력, 프롬프트 거버넌스, 외부 모델 제한 원칙 참고
  - 이미지/OCR: OCR adapter, fallback, confidence 관리 참고
  - 알고리즘: 논문 근거와 프로젝트 계수 분리 원칙 참고
  - UI/UX: 사용자 확인 흐름 참고
  - 안전/검증: 의료·영양 표현 완화 원칙 참고
- 사용하면 안 되는 방식: 기존 HTML의 결론을 현재 MVP에 검토 없이 그대로 이식하지 않는다.
- MVP 반영: `research.md` 분류 방식과 안전 기준
- v2 이후 검토: `../guide/04-backend-api.md`, `../guide/06-ai-agents.md`, `../guide/07-algorithms.md` 보강

### 8.13 질환 기본 정의 출처: 질병관리청 국가건강정보포털

아래 자료는 팀 도메인 학습 문서에서 만성질환의 기본 정의를 설명하기 위한 공식 건강정보 출처다. 기존 조사 자료는 만성질환자와 영양소 섭취 관계, 식단 구성, 개인화 필요성을 설명하는 데 쓰고, 질환이 무엇인지에 대한 기본 정의는 이 공식 건강정보로 보강한다.

#### 고혈압

- 출처:
  - 질병관리청 국가건강정보포털, 고혈압의 진단: <https://health.kdca.go.kr/healthinfo/biz/health/ntcnInfo/healthSourc/thtimtCntnts/thtimtCntntsView.do?thtimt_cntnts_sn=28>
  - 질병관리청 국가건강정보포털, 노인 고혈압: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=6698>
- 등급: A-2. 공식 건강정보
- 팀 학습 자료에서 사용할 내용:
  - 고혈압은 혈관 속 압력이 높은 상태다.
  - 성인에서는 일반적으로 수축기 혈압 140 mmHg 이상 또는 이완기 혈압 90 mmHg 이상을 기준으로 설명한다.
  - 나이가 들수록 흔하고, 심뇌혈관질환 위험요인으로 관리가 필요하다.
  - 식단 학습에서는 나트륨, 체중, 활동량, 복약 맥락과 연결해 이해한다.
- 연결되는 기존 조사 자료:
  - `8.5 고령자의 만성질환과 영양소 섭취 관계 연구`
- 사용하면 안 되는 방식:
  - 사용자 혈압 상태를 진단하거나 식단만으로 혈압 개선을 보장하지 않는다.

#### 당뇨병

- 출처: 질병관리청 국가건강정보포털, 당뇨병: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5305>
- 등급: A-2. 공식 건강정보
- 팀 학습 자료에서 사용할 내용:
  - 당뇨병은 혈액 속 포도당이 세포에서 에너지원으로 제대로 이용되지 못해 혈당이 비정상적으로 높아지는 질환이다.
  - 인슐린 부족 또는 인슐린 저항성과 관련된다.
  - 식단 학습에서는 탄수화물, 당류, 총 에너지, 식사 패턴과 연결해 이해한다.
- 연결되는 기존 조사 자료:
  - `8.5 고령자의 만성질환과 영양소 섭취 관계 연구`
  - `8.2 Precision nutrition for cardiometabolic diseases`
- 사용하면 안 되는 방식:
  - 당뇨병 여부를 판정하거나 특정 식품·영양소가 당뇨병을 개선한다고 단정하지 않는다.

#### 이상지질혈증

- 출처: 질병관리청 국가건강정보포털, 이상지질혈증: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=6054>
- 등급: A-2. 공식 건강정보
- 팀 학습 자료에서 사용할 내용:
  - 이상지질혈증은 LDL 콜레스테롤이나 중성지방이 높거나 HDL 콜레스테롤이 낮은 등 혈액 지질 농도에 이상이 있는 상태다.
  - 죽상경화와 심혈관질환의 중요한 위험요인으로 설명할 수 있다.
  - 식단 학습에서는 포화지방, 지방 섭취 균형, 탄수화물 과다, 음주, 체중 관리와 연결해 이해한다.
- 연결되는 기존 조사 자료:
  - `8.5 고령자의 만성질환과 영양소 섭취 관계 연구`
- 사용하면 안 되는 방식:
  - 지질 수치나 심혈관질환 위험도를 앱이 진단하는 근거로 쓰지 않는다.

#### 뇌졸중

- 출처: 질병관리청 국가건강정보포털, 뇌졸중: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5495>
- 등급: A-2. 공식 건강정보
- 팀 학습 자료에서 사용할 내용:
  - 뇌졸중은 뇌혈관이 막히거나 터져 뇌 영역이 손상되고 신경학적 증상이 나타나는 질환이다.
  - 고혈압, 당뇨병, 비만, 음주, 흡연 등 위험요인 관리가 중요하다.
  - 식단 학습에서는 직접 식단 처방이 아니라 위험요인 관리의 넓은 맥락으로 연결한다.
- 연결되는 기존 조사 자료:
  - `8.5 고령자의 만성질환과 영양소 섭취 관계 연구`
- 사용하면 안 되는 방식:
  - 뇌졸중 예방·재발 방지 효과를 식단 분석 결과로 보장하지 않는다.

#### 골다공증

- 출처: 질병관리청 국가건강정보포털, 골다공증: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5833>
- 등급: A-2. 공식 건강정보
- 팀 학습 자료에서 사용할 내용:
  - 골다공증은 뼈 강도가 약해져 쉽게 부러질 수 있는 질환이다.
  - 고령자와 폐경 이후 여성에게 특히 중요하게 다룰 수 있다.
  - 식단 학습에서는 칼슘, 비타민 D, 단백질, 신체활동과 연결해 이해한다.
- 연결되는 기존 조사 자료:
  - `8.5 고령자의 만성질환과 영양소 섭취 관계 연구`
- 사용하면 안 되는 방식:
  - 골다공증을 진단하거나 특정 식단·영양제가 골절을 예방한다고 단정하지 않는다.

#### 빈혈

- 출처: 질병관리청 국가건강정보포털, 빈혈: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=1104>
- 등급: A-2. 공식 건강정보
- 팀 학습 자료에서 사용할 내용:
  - 빈혈은 적혈구와 혈색소, 산소 운반 기능과 관련해 이해할 수 있다.
  - 혈색소와 적혈구 생성에는 음식에서 얻는 철분, 단백질, 비타민 등이 필요하다.
  - 식단 학습에서는 철, 단백질, 비타민 섭취 상태를 확인하는 맥락으로 연결한다.
- 연결되는 기존 조사 자료:
  - `8.6 한국 노인의 영양성 빈혈 유병 여부에 따른 영양소 섭취 상태와 만성질환 관련성 연구`
- 사용하면 안 되는 방식:
  - 앱 화면에서 "빈혈입니다" 또는 "빈혈 위험입니다"처럼 판정하지 않는다.

#### 심혈관대사질환

- 출처: `8.2 Precision nutrition for cardiometabolic diseases`
- 등급: C. 배경 근거
- 팀 학습 자료에서 사용할 내용:
  - 심혈관질환과 대사질환을 함께 보는 넓은 맥락으로 사용한다.
  - 개인별 식이 반응 차이와 정밀영양 필요성을 설명하는 배경으로 쓴다.
- 사용하면 안 되는 방식:
  - 개별 질환 정의나 질환별 식단 처방 기준처럼 쓰지 않는다.

## 9. Lemon Aid 문서에 반영할 위치

| 반영 문서 | 반영할 내용 |
|-----------|-------------|
| `01-product-overview.md` | 기획 배경, 만성질환자 페르소나, 차별화 포인트 근거 |
| `02-product-spec.md` | 사용자 확인 흐름, 식단·영양제 분석 결과의 표현 방식 |
| `05-data-model.md` | 공식 DB와 문헌 메타데이터 분리, 사용자 건강 데이터 저장 범위 |
| `06-ai-agents.md` | LLM은 판단자가 아니라 구조화·설명 보조자라는 원칙 |
| `07-algorithms.md` | 공식 기준, 논문 근거, 프로젝트 가정, 멘토 확인 필요 구분 |
| `08-compliance-safety.md` | 진단·치료 표현 금지, 참고·관리 중심 표현 근거 |
| 팀 도메인 학습 문서 | 질환 종류와 정의, 만성질환자 영양·식단 기초, 자료별 학습 포인트 |
| 멘토용 요약 기획서 | 조사 자료 요약, 멘토 질문, MVP 범위 결정 근거 |

## 10. 팀 도메인 학습 문서 근거 매핑

| 학습 내용 | 사용할 근거 |
|-----------|-------------|
| 질환 종류와 기본 정의 | `8.13 질환 기본 정의 출처: 질병관리청 국가건강정보포털` |
| 고령자와 만성질환자의 영양소 섭취 관계 | `8.5 고령자의 만성질환과 영양소 섭취 관계 연구`, `8.6 한국 노인의 영양성 빈혈 유병 여부에 따른 영양소 섭취 상태와 만성질환 관련성 연구` |
| 심혈관대사질환과 개인화 영양 필요성 | `8.2 Precision nutrition for cardiometabolic diseases` |
| 균형식단, 식품군, 한식 식단 구성 | `8.3 빅데이터 기반 건강 식단 추천 시스템 연구`, `8.4 체중조절 개인 맞춤형 균형식단 추천 방법 및 장치`, `8.10 빅데이터기반건강식단추천시스템연구.pdf` |
| 식단 관리 지표 | `8.3 빅데이터 기반 건강 식단 추천 시스템 연구`, `8.10 빅데이터기반건강식단추천시스템연구.pdf` |
| AI/OCR 입력과 사용자 확인 흐름 | `8.7 인공지능 기반의 식단과 운동 코칭 기획 모델 모바일 애플리케이션 UI/UX디자인 연구`, `8.12 내부 기준 문서` |

주의: 팀 도메인 학습 문서는 내부 이해를 위한 자료다. 질환 정의와 영양·식단 지식을 사용자 화면에 직접 노출하려면 별도 표현 검수와 `08-compliance-safety.md` 기준 확인이 필요하다.

## 11. 후속 분석 체크리스트

- [ ] 모든 자료를 A/B/C/D 등급 중 하나로 분류한다.
- [ ] 각 자료의 "사용하면 안 되는 방식"을 유지한다.
- [ ] 각 PDF 첫 페이지에서 제목, 저자, 발행처, 발행연도 확인
- [ ] 팀 도메인 학습 문서의 질환 정의가 `8.13` 출처와 연결되는지 확인
- [ ] 팀 도메인 학습 문서의 식품군·식단 지표가 `8.3`, `8.4`, `8.10` 출처와 연결되는지 확인
- [ ] `빅데이터기반건강식단추천시스템연구.pdf`에서 알고리즘 입력/출력 구조 추출
- [ ] `인공지능 기반의 식단과 운동 코칭 기획 모델.pdf`에서 UI/UX 평가 항목 추출
- [ ] KoreaScience 자료의 제목·저자·초록 확인
- [ ] ScienceON DIKO 자료와 로컬 PDF의 동일 여부 확인
- [ ] `07-algorithms.md`에 근거 수준을 `공식 기준`, `논문 근거`, `프로젝트 가정`, `멘토 확인 필요`로 표시
- [ ] 멘토용 기획서에는 조사 자료를 1쪽 표로 압축
- [ ] `08-compliance-safety.md` 기준으로 사용자 노출 문구를 점검

## 12. 기존 조사 출처 목록

- 서울대학교 보건영양연구실: <https://sites.google.com/view/snuphn/home>
- PubMed, Precision nutrition for cardiometabolic diseases: <https://pubmed.ncbi.nlm.nih.gov/40307513/>
- ScienceON, TRKO202300028164 원문: <https://scienceon.kisti.re.kr/commons/util/originalView.do?cn=TRKO202300028164&dbt=TRKO&rn=>
- NTIS, 빅데이터 기반 건강 식단 추천 시스템 연구: <https://www.ntis.go.kr/outcomes/popup/srchTotlRschRpt.do?cmd=get_contents&rstId=REP-2022-01113017257>
- Google Patents, KR102422591B1: <https://patents.google.com/patent/KR102422591B1/ko>
- ScienceON, KOR1020190039019: <https://scienceon.kisti.re.kr/srch/selectPORSrchPatent.do?cn=KOR1020190039019>
- DBpia, T16984706: <https://www.dbpia.co.kr/journal/detail?nodeId=T16984706>
- DBpia, T15096410: <https://www.dbpia.co.kr/journal/detail?nodeId=T15096410>
- KoreaScience, CFKO202233649334366: <https://koreascience.kr/article/CFKO202233649334366.pub?lang=ko&orgId=kips>
- ScienceON, DIKO0016085589: <https://scienceon.kisti.re.kr/srch/selectPORSrchArticle.do?cn=DIKO0016085589>
- Google Books, 인공지능 기반의 식단과 운동 코칭 기획 모델: <https://books.google.com/books/about/%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5_%EA%B8%B0%EB%B0%98%EC%9D%98_%EC%8B%9D%EB%8B%A8%EA%B3%BC_%EC%9A%B4%EB%8F%99.html?id=sbClzwEACAAJ>
- 국회도서관, 인공지능 기반의 식단과 운동 코칭 기획 모델: <https://dl.nanet.go.kr/detail/KDMT12021000034845>
- 질병관리청 국가건강정보포털, 고혈압의 진단: <https://health.kdca.go.kr/healthinfo/biz/health/ntcnInfo/healthSourc/thtimtCntnts/thtimtCntntsView.do?thtimt_cntnts_sn=28>
- 질병관리청 국가건강정보포털, 노인 고혈압: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=6698>
- 질병관리청 국가건강정보포털, 당뇨병: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5305>
- 질병관리청 국가건강정보포털, 이상지질혈증: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=6054>
- 질병관리청 국가건강정보포털, 뇌졸중: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5495>
- 질병관리청 국가건강정보포털, 골다공증: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=5833>
- 질병관리청 국가건강정보포털, 빈혈: <https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn=1104>

## 13. 2026-05-14 보강 조사 출처

이번 보강 조사는 기존 자료를 대체하지 않고, Lemon Aid 구현에 필요한 공식 기준과 기술·안전 근거의 빈틈을 메우기 위한 것이다. 기존 `research.md` 수록 자료는 그대로 유지하고, 새 자료는 아래 태그로 구분한다.

| 태그 | 의미 | 구현 기준 사용 |
|------|------|----------------|
| `KR_OFFICIAL` | 국내 공식 기준, 공공 데이터, 공공 건강정보 | 가능 |
| `KR_CLINICAL_GUIDE` | 국내 학회 진료지침, 복약 안전 안내 | 직접 사용 금지, 전문가 검토용 |
| `KR_RESEARCH` | 국내 연구보고서, 학위논문, 특허, UI/UX 연구 | 배경·구조 참고 |
| `GLOBAL_REVIEW` | 국외 리뷰 논문, scoping/systematic review | 최신 동향·한계 이해 |
| `GLOBAL_TECH` | AI, OCR, 추천 시스템, LLM 평가 기술 자료 | 파이프라인·검증 참고 |
| `NOT_FOR_RULE` | 사용자별 건강 판단 규칙화 금지 항목 | 구현 제한 기준 |

### 13.1 KR_OFFICIAL 추가 자료

| 자료 | 상태 | 사용할 수 있는 방식 | 사용하면 안 되는 방식 |
|------|------|---------------------|------------------------|
| 보건복지부/한국영양학회 2020 한국인 영양소 섭취기준(KDRIs) | 이번 보강 조사, 원문 확인 대상 | 연령·성별 영양소 기준값, 상한섭취량, 권장량 대비 비율 계산 | 만성질환자 치료 목표 또는 질환별 처방 기준으로 확장 |
| 식약처 식품영양성분 DB Open API | 이번 보강 조사 | 음식·가공식품 영양성분 매칭, 출처 코드 관리 | 실제 섭취량을 사용자 확인 없이 확정 |
| 농촌진흥청 국가표준식품성분표/Open API | 이번 보강 조사 | 한식·농식품 영양성분 보강, 음식명 정규화 | 조리법·분량 차이를 무시하고 확정값처럼 표시 |
| 식품안전나라 건강기능식품 원료 정보 | 이번 보강 조사 | 기능성 원료, 기능성 내용, 섭취 시 주의사항 확인 | 질병 예방·치료 효과 또는 제품 추천으로 표현 |
| 한국의약품안전관리원 DUR 안내 | 이번 보강 조사 | 병용금기·주의 개념 학습, 상담 권장 경계 설계 | 앱이 복용 가능/불가능을 최종 판정 |

### 13.2 KR_CLINICAL_GUIDE 추가 자료

| 자료 | 상태 | 사용할 수 있는 방식 | 사용하면 안 되는 방식 |
|------|------|---------------------|------------------------|
| 대한당뇨병학회 당뇨병 진료지침 | 이번 보강 조사, 원문 확인 대상 | 당뇨병과 식사·혈당 관리 맥락 학습, 의료자문 질문 정리 | 당뇨병 여부 판정, 식단 처방, 약물 기준 반영 |
| 대한고혈압학회 고혈압 진료지침 | 이번 보강 조사, 원문 확인 대상 | 고혈압과 나트륨·체중·활동 관리 맥락 학습 | 혈압 상태 진단, 치료 목표 판정 |
| 한국지질·동맥경화학회 이상지질혈증 진료지침 | 이번 보강 조사, 원문 확인 대상 | 지질 지표와 식사 요인 학습 | 심혈관질환 위험도 판정 또는 치료 권고 |
| 대한골대사학회 골다공증 진료지침 | 이번 보강 조사, 원문 확인 대상 | 칼슘·비타민 D·신체활동 맥락 학습 | 골다공증 진단, 골절 예방 보장 표현 |

### 13.3 GLOBAL_REVIEW 추가 자료

| 자료 | 상태 | 사용할 수 있는 방식 | 사용하면 안 되는 방식 |
|------|------|---------------------|------------------------|
| Artificial Intelligence Applications to Measure Food and Nutrient Intakes: Scoping Review | 이번 보강 조사 | AI 기반 식품·영양 섭취 측정의 장점과 한계 이해 | AI 추정 결과를 공식 DB 검증 없이 확정 |
| Mobile Computer Vision-Based Applications for Food Recognition and Volume and Calorific Estimation: A Systematic Review | 이번 보강 조사 | 음식 인식·분량 추정의 오차와 사용자 확인 필요성 설명 | 음식 사진만으로 섭취량·열량 확정 |
| Navigating nutrients: real-time food nutrition classification and recommendation systems | 이번 보강 조사 | 실시간 음식 영양 분류·추천 시스템 동향 참고 | 국외 추천 기준을 한국 사용자에게 직접 적용 |
| Large language models provide unsafe answers to patient-posed medical questions | 이번 보강 조사 | 환자 대상 LLM 의료 답변 안전성 위험과 필터 필요성 설명 | 챗봇이 의료 상담을 대신하도록 허용 |

### 13.4 GLOBAL_TECH 추가 자료

| 자료 | 상태 | 사용할 수 있는 방식 | 사용하면 안 되는 방식 |
|------|------|---------------------|------------------------|
| NutriBench: nutrition estimation from meal descriptions | 이번 보강 조사 | 식사 설명 기반 영양 추정 벤치마크 참고 | 벤치마크 결과를 Lemon Aid 정확도 보장으로 사용 |
| Demystifying Large Language Models for Medicine: A Primer | 이번 보강 조사 | 의료 LLM 사용 범위와 평가 관점 학습 | LLM이 의료 판단을 생성해도 된다는 근거로 사용 |
| MedHalu: Hallucinations in Responses to Healthcare Queries | 이번 보강 조사 | 의료 질의 hallucination 위험과 expert-in-the-loop 필요성 참고 | hallucination이 자동으로 해결됐다고 가정 |
| A Framework for Human Evaluation of LLMs in Healthcare | 이번 보강 조사 | 의료 LLM 인간 평가 항목 참고 | 자동 평가만으로 의료 안전성 확보 판단 |
| Towards Human-AI Collaboration in Healthcare: Guided Deferral Systems | 이번 보강 조사 | 불확실하거나 위험한 경우 사람에게 넘기는 deferral 설계 참고 | 앱이 최종 판단을 계속 유지 |

## 14. 태그별 상세 문서

보강 조사 자료와 기존 자료는 아래 상세 문서에서 태그별로 다시 정리한다.

| 문서 | 태그 | 목적 |
|------|------|------|
| [01-kr-official.md](./evidence-tags/01-kr-official.md) | `KR_OFFICIAL` | 구현 기준 가능 자료 |
| [02-kr-clinical-guide.md](./evidence-tags/02-kr-clinical-guide.md) | `KR_CLINICAL_GUIDE` | 팀 학습/전문가 검토용 자료 |
| [03-kr-research.md](./evidence-tags/03-kr-research.md) | `KR_RESEARCH` | 한국 사용자 맥락/배경 근거 |
| [04-global-review.md](./evidence-tags/04-global-review.md) | `GLOBAL_REVIEW` | 최신 동향/배경 근거 |
| [05-global-tech.md](./evidence-tags/05-global-tech.md) | `GLOBAL_TECH` | AI, OCR, 추천 시스템 구현 참고 |
| [06-not-for-rule.md](./evidence-tags/06-not-for-rule.md) | `NOT_FOR_RULE` | 사용자별 건강 판단 규칙화 금지 |

## 15. 보강 출처 목록

- 보건복지부, 2020 한국인 영양소 섭취기준: <https://www.mohw.go.kr/board.es?act=view&bid=0019&list_no=362385&mid=a10411000000&nPage=39&tag=>
- 한국영양학회 KDRIs 자료실: <https://www.kns.or.kr/fileroom/fileroom_view.asp?BoardID=Kdr&idx=108>
- 식약처 식품영양성분 DB Open API: <https://various.foodsafetykorea.go.kr/nutrient/industry/openApi/info.do>
- 농촌진흥청 국가표준식품성분표/Open API: <https://koreanfood.rda.go.kr/kfi/openapi/useNewGuidance>
- 식품안전나라: <https://www.foodsafetykorea.go.kr>
- 한국의약품안전관리원 DUR 안내: <https://www.drugsafe.or.kr/iwt/ds/ko/useinfo/EgovDurUds.do?pageCsf=KR>
- 대한당뇨병학회 당뇨병 진료지침: <https://diabetes.or.kr/bbs/download.php?code=guide&number=1522>
- 대한고혈압학회 진료지침 자료: <https://www.koreanhypertension.org/reference/guide?mode=read>
- 한국지질·동맥경화학회 이상지질혈증 진료지침: <https://www.lipid.or.kr/conferences_journals/publication.php>
- 대한골대사학회 골다공증 진료지침: <https://www.ksbmr.org/bbs/index.html?category=&code=notice&gubun=&key=&keyfield=&mode=view&number=1294&page=13>
- PubMed, Artificial Intelligence Applications to Measure Food and Nutrient Intakes: <https://pubmed.ncbi.nlm.nih.gov/39608003/>
- MDPI, Mobile Computer Vision-Based Applications for Food Recognition and Volume and Calorific Estimation: <https://www.mdpi.com/2029682>
- PubMed, Navigating nutrients: <https://pubmed.ncbi.nlm.nih.gov/40328030/>
- PMC, Large language models provide unsafe answers to patient-posed medical questions: <https://pmc.ncbi.nlm.nih.gov/articles/PMC13013898/>
- Hugging Face Papers, NutriBench: <https://huggingface.co/papers/2407.12843>
- Hugging Face Papers, Demystifying Large Language Models for Medicine: <https://huggingface.co/papers/2410.18856>
- Hugging Face Papers, MedHalu: <https://huggingface.co/papers/2409.19492>
- arXiv, A Framework for Human Evaluation of LLMs in Healthcare: <https://arxiv.org/abs/2405.02559>
- arXiv, Towards Human-AI Collaboration in Healthcare: <https://arxiv.org/abs/2406.07212>
- ScienceDirect, Can large language models reason about medical questions?: <https://www.sciencedirect.com/science/article/pii/S2666389924000424>
