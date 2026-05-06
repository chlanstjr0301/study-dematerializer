# MVP5 개발 계획서

_작성일: 2026-05-06_
_기반: `docs/diagnostics/MVP4_PRODUCT_ALIGNMENT_DIAGNOSIS.md`_
_성격: 제품 정렬 복구 — 기능 확장이 아님_

---

## 목차

- [0. 요약](#0-요약)
- [1. 기준선: 현재 MVP4 상태](#1-기준선-현재-mvp4-상태)
- [2. MVP5 제품 목표](#2-mvp5-제품-목표)
- [3. MVP5 범위 경계 (6개 단계)](#3-mvp5-범위-경계-6개-단계)
- [4. MVP5 사용자 흐름](#4-mvp5-사용자-흐름)
- [5. 화면 아키텍처](#5-화면-아키텍처)
- [6. 백엔드 아키텍처](#6-백엔드-아키텍처)
- [7. 데이터 모델](#7-데이터-모델)
- [8. 프론트엔드 컴포넌트 계획](#8-프론트엔드-컴포넌트-계획)
- [9. LLM 정책](#9-llm-정책)
- [10. 테스트 전략](#10-테스트-전략)
- [11. 수락 기준 / 완료 정의](#11-수락-기준--완료-정의)
- [12. 엔지니어링 태스크 목록](#12-엔지니어링-태스크-목록)
- [13. Claude Code 프롬프트](#13-claude-code-프롬프트)
- [14. 배포 정책](#14-배포-정책)
- [15. 최종 권고](#15-최종-권고)

---

## 0. 요약

### MVP5의 목적은 배포 안정화가 아니라 제품 정렬 복구다.

MVP4 진단(`MVP4_PRODUCT_ALIGNMENT_DIAGNOSIS.md`)이 확인한 핵심 문제: **현 구현은 개발자 파이프라인 검증 도구이지, 학습자 중심 통합 학습 루프가 아니다.**

- S0 갭 3개: 통합 학습 세션 부재, 5가지 표현 하드코딩, 대화형 진단 부재
- S1 갭 5개: 자기 설명 미구현, White Recall 미통합, 오개념 MCQ 미제시, 스캐폴딩 전무, proof schema walkthrough 없음
- S2 갭 3개: Dashboard/RecallSession 영어, 개발자 도구 학습자 노출

MVP5는 이 갭들 중 **S0 전체와 S1/S2 핵심을 수리**한다. 새 기능이 아니라 원래 비전(`00_vision.md` ~ `09_risks_and_guardrails.md`)이 요구한 것을 구현하는 것이다.

**프로덕션 경화는 제품 적합성이 복구된 후에 진행한다.**

---

## 1. 기준선: 현재 MVP4 상태

| 영역 | 현 상태 | 제품 문제 | MVP5 함의 |
|------|---------|----------|----------|
| 파이프라인 | 8단계 컴파일러 작동. `run_new_concept_session()` → 12 아티팩트 생성 (`session.py`) | 학습자가 직접 호출 불가. 개발자가 수동 실행 | MVP5-2에서 `POST /api/study-session`이 내부 호출 |
| 표현 생성 | `REPRESENTATION_PREVIEWS` 하드코딩 (`compiler_analyzer_service.py:65-137`). 소스 무관 | S0 — 핵심 가치 "소스 기반 5표현" 미충족 | MVP5에서는 mock 유지. 하드코딩 표현을 세션 내에서 표시하되, LLM 실시간 생성은 MVP6으로 이관 |
| ChatCompiler | 한국어 규칙 기반 분석 (`POST /api/compiler/analyze`). 개념 매칭 + 갭 추론 | 단일 메시지 분석기 — 대화형 진단 아님 | MVP5에서 ChatCompiler는 유지. 대화형 진단은 `/study/:conceptId` 1단계에서 처리 |
| Recall | `/recall` 독립 페이지. `grader: 'mock'` 하드코딩 (`RecallSession.tsx:103`). bank 필수 | 세션 내 필수 단계 아님. 첫 사용 시 bank 없어 사용 불가 | MVP5-4에서 StudySession 5단계에 인출 내장. 자동 bank 준비 |
| Dashboard | 6개 API 호출. ~40개 영어 문자열 | S2 — 학습자 대면인데 전체 영어 | MVP5-0에서 한국어화 |
| RecallSession | ~30개 영어 문자열. 빈 상태만 한국어 | S2 — 핵심 학습 활동인데 혼합 언어 | MVP5-0에서 한국어화 |
| STUDY.md | 파싱/쓰기/검증/복구 완전 구현 (`writer.py`, `parser.py`, `validate.py`) | 없음 — 잘 작동 | 그대로 재사용 |
| 자기 설명 | `evaluate_self_explanation()` 구현 완료 (`self_explanation.py:51-80`). UI 없어 한 번도 호출 안 됨 | S1 — P5 원칙 미준수 | MVP5-4에서 UI + API 추가하여 기존 백엔드 활성화 |
| 테스트 | 965 함수, 47 파일. ~975 통과 (파라미터 확장) | 없음 | 기준선 유지. 회귀 불허 |
| LLM | `MockLLMClient()` 하드코딩 (`concept_service.py:95`). `LLM_DISABLED=1` 기본값 | LLM 생성 경로가 프로덕션에서 비활성 | MVP5 전체에서 mock 유지. LLM 활성화는 MVP6 |
| 네비게이션 | 한국어 기본 (공부하기/인출연습/대시보드) + 개발자 토글 (`Layout.tsx`) | 개발자 도구 4개가 토글 뒤에 숨겨져 있으나 학습자가 발견 가능 | MVP5에서 개발자 도구는 현 상태 유지 |
| 라우트 | 9개 (`App.tsx`): `/`, `/dashboard`, `/bank`, `/sessions`, `/sessions/:id`, `/recall`, `/sources`, `/review/:id`, `/concepts` | `/study/:conceptId` 부재 | MVP5-1에서 추가 |

---

## 2. MVP5 제품 목표

### 한 문장 목표

> **학습자가 개념명을 입력하면 하나의 화면에서 "진단 → 선행 확인 → 5가지 표현 학습 + 자기 설명 → 인출 연습 → 세션 정리"를 완주할 수 있게 한다.**

### 대상 사용자

한국어 사용 학부 3-4학년, 실해석학 독학자. 개발 경험 없음. CLI/개발자 도구에 익숙하지 않음.

### 주요 사용자 스토리

> "실해석학 수업에서 compactness가 이해 안 된다. 공부해체분석기에 '옹골성 공부하고 싶어'라고 입력하면, 내가 뭘 모르는지 진단해 주고, 선행 지식을 확인해 주고, 5가지 다른 방식으로 설명해 주고, 각 설명마다 내 말로 다시 설명해 보게 하고, 마지막에 교재 덮고 인출해 보게 해서, STUDY.md에 오늘 기록이 남는다."

### 비목표 (MVP5에서 하지 않는 것)

| 비목표 | 이유 |
|--------|------|
| 사용자 인증/로그인 | 단일 사용자 로컬 도구. v2 이후 |
| 데이터베이스 | STUDY.md + JSON 아티팩트가 현재 충분 |
| PDF/OCR 소스 업로드 | 마크다운 소스만 지원. PDF 변환은 별도 도구 |
| 프로덕션 경화 (HTTPS, systemd, 도메인) | 제품 적합성 복구가 선행 조건 |
| 다중 사용자 | v2 이후 |
| 새 도메인/개념 추가 | 기존 3개 seed (compactness, connectedness, uniform_continuity)로 핵심 루프 증명 |
| 실제 LLM 활성화 (가드레일 전) | 환각 위험. MVP6에서 가드레일과 함께 활성화 |
| i18n 라이브러리 도입 | 단일 언어(한국어) 제품. 문자열 직접 교체 |

---

## 3. MVP5 범위 경계 (6개 단계)

### MVP5-0: UX 보정 (한국어화)

**목표**: 학습자 대면 페이지에서 영어 UI 문자열 제거

**범위**:
- `Dashboard.tsx` — ~40개 영어 문자열 한국어 교체
  - "Dashboard" → "대시보드", "API Status" → "API 상태", "Review Due" → "복습 예정"
  - "Weak Representations" → "취약 표현", "Recent Sessions" → "최근 세션"
  - "STUDY.md State" → "STUDY.md 상태", "Valid" → "정상"
  - CTA: "Resume: N concept(s) due" → "복습: N개 개념 복습 예정"
  - "Strengthen →" → "강화 →", "Review Weak →" → "취약 복습 →", "Full Review →" → "전체 복습 →"
  - "View →" → "보기 →", "All representations current" → "모든 표현 최신"
  - "Nothing due for review." → "복습 예정인 개념이 없습니다."
  - "No sessions yet." → "아직 세션이 없습니다."
  - 테이블 헤더: "Concept"→"개념", "Mastery"→"숙련도", "Weak Reps"→"취약", "Next Review"→"다음 복습", "Status"→"상태", "Type"→"유형", "Last reviewed"→"최근 복습", "Started"→"시작일"
  - 배지: "overdue"→"초과", "due"→"예정", "solid"→"완전", "partial"→"부분", "unknown"→"미확인"
- `RecallSession.tsx` — ~30개 영어 문자열 한국어 교체
  - "Recall Session" → "인출 연습", "Select a Question Bank" → "문제은행 선택"
  - "Loading banks..." → "문제은행 불러오는 중...", "Recall: {selected}" → "인출: {selected}"
  - "Mode: Full Recall" → "모드: 전체 인출", "Due review: targeting..." → "복습 대상: ..."
  - "Targeting: {rep} representation" → "대상: {rep} 표현"
  - "Loading questions..." → "질문 불러오는 중..."
  - "No accepted questions found." → "승인된 질문이 없습니다."
  - "Write your answer here..." → "답변을 작성하세요..."
  - "Submit (mock grader)" → "제출 (모의 채점)", "Submitting..." → "제출 중..."
  - "Session Created" → "세션 생성 완료", "Session ID" → "세션 ID", "Attempts graded" → "채점된 응답 수"
  - "Session summary" → "세션 요약", "Mastery Changes" → "숙련도 변화"
  - "Representation"→"표현", "Before"→"이전", "After"→"이후", "Score"→"점수"
  - "Weak Questions" → "취약 질문", "No weak questions — great work!" → "취약 질문 없음 — 잘했습니다!"
  - "View Session Detail →" → "세션 상세 보기 →", "Back to Dashboard →" → "대시보드로 돌아가기 →"
  - "Submission failed:" → "제출 실패:"
- 빈 상태 안내 개선 (이미 한국어인 부분 유지)

**비범위**: 개발자 도구 한국어화, 새 페이지 생성, API 변경, i18n 라이브러리

---

### MVP5-1: Study Session 셸 (프론트엔드 전용)

**목표**: `/study/:conceptId` 라우트에 6단계 한국어 스텝퍼 UI 배치. 백엔드 없이 placeholder.

**범위**:
- 신규 `apps/web/src/pages/StudySession.tsx` — 6단계 스텝퍼
  - 1단계: 진단 (textarea 2개: 사전 지식 / 갭 서술)
  - 2단계: 선행 지식 확인 (checkbox 목록 placeholder)
  - 3단계: 5가지 표현 + 자기 설명 (표현 카드 + textarea placeholder)
  - 4단계: 오개념 체크 (MCQ placeholder)
  - 5단계: 인출 연습 (textarea placeholder)
  - 6단계: 세션 정리 (요약 placeholder)
- `/study/:conceptId` 라우트 등록 (`App.tsx`)
- ChatCompiler → "공부 시작" 클릭 시 `/study/:conceptId` 이동 (`ChatCompiler.tsx` 수정)
  - `recommended_actions`에서 `route: "/study/{concept_id}"` 반환하도록 `compiler_analyzer_service.py` 수정
  - 또는 프론트엔드에서 직접 `Link to={`/study/${conceptId}`}` 추가
- Layout 네비게이션에 "공부하기" 링크는 이미 `/`로 설정됨 — 변경 불필요
- 세션 상태: React `useState`로 관리 (step index, 각 단계 입력 값)

**비범위**: 백엔드 API 없음. LLM 없음. 실제 데이터 바인딩 없음.

---

### MVP5-2: Study Session 백엔드

**목표**: 통합 학습 세션의 백엔드 API — 세션 생성, 상태 조회, 진단 제출.

**범위**:
- `POST /api/study-session` — 세션 생성 (6절 상세)
- `GET /api/study-session/{id}` — 세션 상태 + 아티팩트 조회 (6절 상세)
- `POST /api/study-session/{id}/diagnose` — 진단 텍스트 수신 + 저장 (6절 상세)
- `POST /api/study-session/{id}/advance` — 단계 진행 (6절 상세)
- 신규 라우터: `apps/api/routers/study_session.py`
- 신규 서비스: `apps/api/services/study_session_service.py`
- 세션 상태 파일: `runs/{session_id}/study_session_state.json`
- 기존 `run_new_concept_session()` 내부 호출 (MockLLMClient 유지)
- `main.py`에 라우터 등록

**비범위**: LLM 실시간 생성 없음. 자기 설명 API는 MVP5-4. 프론트엔드 바인딩은 MVP5-3.

---

### MVP5-3: 파이프라인 통합

**목표**: StudySession 프론트엔드를 MVP5-2 백엔드에 연결. 학습자 경로에서 수동 bank 빌드/리뷰 제거.

**범위**:
- `StudySession.tsx`에서 `POST /api/study-session` 호출 → 세션 생성 → 아티팩트 로드
- 표현 단계: `representation_set.json`에서 5가지 표현 읽어 표시
- 선행 단계: `prerequisite_graph.json`에서 선행 목록 표시 + mastery 체크박스
- 오개념 단계: `diagnosis.json`에서 오개념 목록 읽기 (MCQ UI는 placeholder — 참/거짓 표시만)
- 인출 단계: `recall_tasks.json`에서 질문 로드 → 기존 `POST /api/sessions` 재사용
- 자동 bank 준비: `study_session_service.py`에서 컴파일 후 `questions.generated.json` → `questions.accepted.json` 자동 복사 (학습자 경로에서 수동 리뷰 생략)
- `apps/web/src/api/client.ts`에 study-session API 함수 추가
- `apps/web/src/api/types.ts`에 StudySession 관련 타입 추가

**비범위**: LLM 없음. 자기 설명 수집/평가 없음 (MVP5-4). 오개념 MCQ 상호작용 없음 (표시만).

---

### MVP5-4: 자기 설명 + White Recall 통합

**목표**: 각 표현 후 자기 설명 수집 + mock 평가. White Recall을 세션 완료 필수 단계로. STUDY.md 자동 업데이트. 세션 요약 한국어.

**범위**:
- 표현 단계: 각 표현 후 자기 설명 textarea + "제출" 버튼
- `POST /api/study-session/{id}/self-explain` — representation_type + learner_response 수신 → `evaluate_self_explanation()` 호출 (MockLLMClient)
- `POST /api/study-session/{id}/recall` — 기존 `POST /api/sessions` 로직 위임
- `POST /api/study-session/{id}/complete` — STUDY.md 패치 적용 + 한국어 세션 요약 반환
- White Recall 필수화: 5단계(인출) 완료 전에는 6단계(정리) 진입 불가
- 세션 요약 한국어: "오늘 다룬 내용", "숙련도 변화", "다음 복습일", "남은 선행"
- STUDY.md 업데이트: 기존 `apply_patch()` 재사용

**비범위**: 실제 LLM 평가 (MVP6). 오개념 MCQ 대화형 상호작용 (MVP6). 스캐폴딩 난이도 분기 (MVP6).

---

### MVP5-5: 로컬 도그푸딩 게이트

**목표**: MVP5-0~4 완료 후, 실제 사용 시나리오로 전체 흐름 검증.

**범위**:
- 5가지 수동 시나리오 완주 (10절 참조)
- 전체 학습자 경로에서 영어 문자열 0개 확인
- STUDY.md 무결성 확인 (validate 통과)
- 기존 테스트 전체 통과 (회귀 없음)
- `npm run build` 성공 (프론트엔드 빌드)
- 발견된 문제 수정 → 재검증

**비범위**: 외부 배포. 프로덕션 경화. 실제 사용자 테스트.

---

## 4. MVP5 사용자 흐름

### 통합 학습 세션: 11단계

| # | 단계 | 화면 동작 | 백엔드 호출 | 기록되는 데이터 | 실패 시 | 한국어 카피 |
|---|------|----------|------------|----------------|---------|-----------|
| 1 | 개념 입력 | ChatCompiler(`/`)에서 자유 텍스트 입력 | `POST /api/compiler/analyze` | — | 미인식 → "이 개념은 아직 지원하지 않습니다" | "무엇을 공부하고 싶으세요?" |
| 2 | 개념 인식 + 공부 시작 | 분석 결과 표시 + "공부 시작" 버튼 | — | — | — | "[개념명] 공부 시작 →" |
| 3 | 세션 생성 | `/study/:conceptId` 이동. 로딩 스피너 | `POST /api/study-session` | `runs/{session_id}/` 12 아티팩트 + `study_session_state.json` | 컴파일 실패 → "세션을 시작할 수 없습니다. 다시 시도해 주세요." | "학습 세션을 준비하고 있습니다..." |
| 4 | 진단 | 2개 textarea: "이 개념에 대해 알고 있는 것" + "어디서 막히나요?" | `POST .../diagnose` | `study_session_state.json` 업데이트 | 빈 입력 허용 (선택적) | "지금 알고 있는 것을 적어 주세요", "어디서 막히거나 헷갈리나요?" |
| 5 | 선행 확인 | 선행 개념 목록 + mastery 체크박스 | `GET .../` (세션 상태 내 prerequisite_graph) | — | — | "이 개념을 공부하려면 다음 개념이 필요합니다", "편하게 설명할 수 있나요?" |
| 6 | 표현 학습 (1/5 ~ 5/5) | 표현 카드 순차 표시 | — (프론트엔드에서 로컬 데이터 표시) | — | — | "[1/5] 정의 (formal)", "[2/5] 직관 (intuitive)", ... |
| 7 | 자기 설명 (각 표현 후) | textarea + "제출" | `POST .../self-explain` | `runs/{session_id}/self_explanations.json` | 빈 입력 → "자기 설명을 작성해 주세요" | "이 표현을 자기 말로 설명해 보세요", 피드백: "정확합니다. 누락: ..." |
| 8 | 오개념 확인 | diagnosis.json의 misconceptions 표시 (읽기 전용) | — | — | — | "주의할 오개념", "참/거짓을 판단해 보세요" |
| 9 | White Recall | 질문 목록 + textarea. 필수 — 건너뛸 수 없음 | `POST .../recall` | `runs/{session_id}/recall_attempts.json` | 빈 응답 → "인출 응답을 작성해 주세요" | "교재를 덮고, 처음부터 설명해 보세요" |
| 10 | 세션 완료 | "완료" 클릭 | `POST .../complete` | STUDY.md 패치 (`apply_patch`) | Recall 미완료 → "인출 연습을 먼저 완료해야 합니다" | "학습 완료" |
| 11 | 세션 정리 | 한국어 요약 표시: 다룬 내용, mastery 변화, 다음 복습일, 남은 선행 | — | — | — | "오늘 다룬 내용", "숙련도 변화", "다음 복습일: YYYY-MM-DD" |

---

## 5. 화면 아키텍처

### 라우트 테이블

| 경로 | 목적 | 대상 사용자 | 한국어 제목 | 기본 내비 | 개발자 토글 | MVP5 변경 |
|------|------|------------|------------|----------|------------|----------|
| `/` | ChatCompiler — 개념 입력 + 분석 | 학습자 | 공부하기 | 예 | 아니오 | "공부 시작" → `/study/:id` 연결 (MVP5-1) |
| `/study/:conceptId` | **통합 학습 세션** — 6단계 스텝퍼 | 학습자 | 학습 세션 | 아니오 (세션 내) | 아니오 | **신규** (MVP5-1) |
| `/dashboard` | 학습 현황 + 복습 알림 | 학습자 | 대시보드 | 예 | 아니오 | 한국어화 (MVP5-0) |
| `/recall` | 독립 인출 연습 (복습용) | 학습자 | 인출연습 | 예 | 아니오 | 한국어화 (MVP5-0) |
| `/sources` | 소스 업로드 | 개발자 | 소스 관리 | 아니오 | 예 | 변경 없음 |
| `/bank` | 문제은행 조회 | 개발자 | 문제은행 | 아니오 | 예 | 변경 없음 |
| `/review/:conceptId` | Bank 리뷰/승인 | 개발자 | — | 아니오 | 예 | 변경 없음 |
| `/concepts` | 개념 컴파일러 | 개발자 | 컴파일러 | 아니오 | 예 | 변경 없음 |
| `/sessions` | 세션 이력 | 개발자 | 세션 | 아니오 | 예 | 변경 없음 |
| `/sessions/:sessionId` | 세션 상세 | 개발자 | — | 아니오 | 예 | 변경 없음 |

### 핵심 변경

- `/study/:conceptId`가 학습자의 **주요 학습 경로**
- ChatCompiler(`/`)는 진입점. 개념 인식 → 공부 시작 → `/study` 이동
- `/recall`은 STUDY.md due 기반 **독립 복습** 전용으로 유지
- 개발자 도구 (`/sources`, `/bank`, `/review`, `/concepts`, `/sessions`)는 토글 뒤에 유지 — 삭제하지 않음
- Layout 네비게이션 변경 없음 (이미 한국어: 공부하기/인출연습/대시보드)

---

## 6. 백엔드 아키텍처

### 6.1 POST /api/study-session — 세션 생성

| 항목 | 내용 |
|------|------|
| **메서드** | POST |
| **단계** | MVP5-2 |
| **목적** | 개념 입력 → 8단계 파이프라인 실행 → 세션 생성 + bank 자동 준비 |

**요청 스키마**:
```python
class CreateStudySessionRequest(BaseModel):
    concept_id: str
    source_relative_path: str | None = None  # 미제공 시 기존 소스 자동 탐색
```

**응답 스키마**:
```python
class CreateStudySessionResponse(BaseModel):
    session_id: str
    concept_id: str
    canonical_name_ko: str
    current_step: int                        # 1 (diagnose)
    steps: list[str]                         # ["diagnose","prerequisites","representations","misconceptions","recall","summary"]
    representations: dict[str, str]          # {formal: "...", intuitive: "...", ...}
    prerequisites: list[PrerequisiteInfo]    # [{concept_id, name_ko, mastery}]
    misconceptions: list[MisconceptionInfo]  # [{id, claim, is_correct}]
```

**JSON 예시**:

요청:
```json
{
  "concept_id": "compactness"
}
```

응답 (201):
```json
{
  "session_id": "a1b2c3d4-5678-9abc-def0-123456789abc",
  "concept_id": "compactness",
  "canonical_name_ko": "옹골성",
  "current_step": 1,
  "steps": ["diagnose", "prerequisites", "representations", "misconceptions", "recall", "summary"],
  "representations": {
    "formal": "Definition 2.32: A subset K of a metric space X is said to be compact if ...",
    "intuitive": "직관적으로 콤팩트 집합은 ...",
    "visual": "[시각적 설명]",
    "counterexample": "(0,1) 구간이 콤팩트가 아닌 이유 ...",
    "proof_schema": "Heine-Borel 정리 증명 구조 ..."
  },
  "prerequisites": [
    {"concept_id": "metric_space", "name_ko": "거리 공간", "mastery": "unknown"},
    {"concept_id": "open_cover", "name_ko": "열린 덮개", "mastery": "unknown"}
  ],
  "misconceptions": [
    {"id": "compactness_m01", "claim": "콤팩트 집합은 항상 유계이다", "is_correct": false}
  ]
}
```

**오류**:
- 422: 미인식 concept_id → `{"detail": "지원하지 않는 개념입니다: {concept_id}"}`
- 500: 파이프라인 실패 → `{"detail": "세션 생성 중 오류가 발생했습니다"}`

**내부 로직**:
1. `resolve_concept(concept_id)` — 유효성 검증
2. 소스 탐색: `source_relative_path` 제공 시 사용, 아니면 `SOURCES_DIR`에서 해당 개념의 기존 소스 탐색
3. `run_new_concept_session()` 호출 (MockLLMClient) → 12 아티팩트 생성
4. bank 자동 준비: `questions.generated.json` → `questions.accepted.json` 복사
5. `study_session_state.json` 생성 (초기 상태: step=1)
6. 응답에 표현/선행/오개념 포함

**테스트**: 정상 생성 + 아티팩트 확인, 미인식 개념 422, 소스 없는 경우 처리

---

### 6.2 GET /api/study-session/{session_id} — 세션 상태 조회

| 항목 | 내용 |
|------|------|
| **메서드** | GET |
| **단계** | MVP5-2 |
| **목적** | 세션의 현재 상태 + 진행 정보 반환 |

**응답 스키마**:
```python
class StudySessionState(BaseModel):
    session_id: str
    concept_id: str
    canonical_name_ko: str
    current_step: int
    steps_completed: list[str]
    diagnosis: DiagnosisData | None = None
    self_explanations: dict[str, SelfExplanationResult] | None = None
    recall_completed: bool
    created_at: str
```

**JSON 예시**:

응답 (200):
```json
{
  "session_id": "a1b2c3d4-...",
  "concept_id": "compactness",
  "canonical_name_ko": "옹골성",
  "current_step": 3,
  "steps_completed": ["diagnose", "prerequisites"],
  "diagnosis": {
    "prior_knowledge": "열린 덮개가 뭔지는 아는데...",
    "gap_description": "유한 부분덮개가 왜 필요한지 모르겠어"
  },
  "self_explanations": {
    "formal": {"submitted": true, "accuracy_score": 0.7, "missing": ["유한 부분덮개"]},
    "intuitive": {"submitted": false}
  },
  "recall_completed": false,
  "created_at": "2026-05-06T14:30:00Z"
}
```

**오류**:
- 404: 존재하지 않는 session_id → `{"detail": "세션을 찾을 수 없습니다: {session_id}"}`

**테스트**: 정상 조회, 404, 단계 진행 후 상태 변경 확인

---

### 6.3 POST /api/study-session/{session_id}/diagnose — 진단 제출

| 항목 | 내용 |
|------|------|
| **메서드** | POST |
| **단계** | MVP5-2 |
| **목적** | 학습자 사전 지식 + 갭 서술 수신 → 저장 + 결정적 평가 |

**요청 스키마**:
```python
class DiagnoseRequest(BaseModel):
    prior_knowledge: str = ""
    gap_description: str = ""
```

**응답 스키마**:
```python
class DiagnoseResponse(BaseModel):
    initial_mastery_estimate: str    # "unknown" | "partial" | "solid"
    identified_gaps: list[str]
    recommendation: str
```

**JSON 예시**:

요청:
```json
{
  "prior_knowledge": "열린 덮개가 뭔지는 아는데, 유한 부분덮개가 왜 필요한지 모르겠어",
  "gap_description": "증명에서 유한성이 왜 중요한지 이해 안 됨"
}
```

응답 (200):
```json
{
  "initial_mastery_estimate": "partial",
  "identified_gaps": ["유한 부분덮개의 필요성"],
  "recommendation": "formal 표현부터 시작하는 것을 권장합니다"
}
```

MVP5에서는 결정적 처리: `GAP_CUES` 키워드 매칭 기반. LLM 평가는 MVP6.

**오류**:
- 404: 존재하지 않는 세션
- 409: 이미 진단 제출된 세션 → `{"detail": "이미 진단이 완료되었습니다"}`

**테스트**: 정상 제출 + 상태 업데이트, 빈 입력 허용, 404, 409

---

### 6.4 POST /api/study-session/{session_id}/advance — 단계 진행

| 항목 | 내용 |
|------|------|
| **메서드** | POST |
| **단계** | MVP5-2 |
| **목적** | 현재 단계 완료 → 다음 단계로 진행 |

**요청 스키마**:
```python
class AdvanceRequest(BaseModel):
    completed_step: str  # "diagnose" | "prerequisites" | "representations" | "misconceptions" | "recall"
```

**응답 스키마**:
```python
class AdvanceResponse(BaseModel):
    current_step: int
    current_step_name: str
    steps_completed: list[str]
```

**JSON 예시**:

요청:
```json
{"completed_step": "diagnose"}
```

응답 (200):
```json
{
  "current_step": 2,
  "current_step_name": "prerequisites",
  "steps_completed": ["diagnose"]
}
```

**오류**:
- 400: 순서 위반 (예: recall 전에 complete 시도) → `{"detail": "이전 단계를 먼저 완료해야 합니다"}`
- 404: 존재하지 않는 세션

**테스트**: 정상 진행, 순서 위반 거부, 최종 단계 후 진행 시도

---

### 6.5 POST /api/study-session/{session_id}/self-explain — 자기 설명 제출

| 항목 | 내용 |
|------|------|
| **메서드** | POST |
| **단계** | MVP5-4 |
| **목적** | 표현별 자기 설명 수집 → mock 평가 → 피드백 반환 |

**요청 스키마**:
```python
class SelfExplainRequest(BaseModel):
    representation_type: str  # "formal" | "intuitive" | "visual" | "counterexample" | "proof_schema"
    learner_response: str
```

**응답 스키마**:
```python
class SelfExplainResponse(BaseModel):
    accuracy_score: float
    missing_elements: list[str]
    errors: list[str]
    feedback: str
```

**JSON 예시**:

요청:
```json
{
  "representation_type": "formal",
  "learner_response": "콤팩트 집합은 모든 열린 덮개가 유한 부분덮개를 가지는 집합입니다"
}
```

응답 (200):
```json
{
  "accuracy_score": 0.85,
  "missing_elements": ["위상 공간 또는 거리 공간 맥락 명시"],
  "errors": [],
  "feedback": "정확합니다. 한 가지 보완: 이 정의가 어떤 공간에서 성립하는지 명시하면 더 좋습니다."
}
```

**내부 로직**: `evaluate_self_explanation()` (`self_explanation.py:51-80`) 호출. MockLLMClient fixture → 고정 응답 반환.

**오류**:
- 404: 존재하지 않는 세션
- 400: 빈 learner_response → `{"detail": "자기 설명을 작성해 주세요"}`
- 400: 유효하지 않은 representation_type

**테스트**: 정상 제출 → RecallEvaluation 반환, 빈 입력 거부, 각 representation_type 테스트

---

### 6.6 POST /api/study-session/{session_id}/recall — White Recall 제출

| 항목 | 내용 |
|------|------|
| **메서드** | POST |
| **단계** | MVP5-4 |
| **목적** | White Recall 응답 수집 → mock 채점 → 결과 반환 |

**요청 스키마**:
```python
class StudyRecallRequest(BaseModel):
    answers: list[AnswerInput]  # 기존 AnswerInput 재사용
    grader: Literal["mock"] = "mock"
```

**응답 스키마**:
```python
class StudyRecallResponse(BaseModel):
    attempt_count: int
    results: list[RecallResult]
    overall_summary: str
```

**JSON 예시**:

요청:
```json
{
  "answers": [
    {"question_id": "q_formal_001", "learner_response": "콤팩트 집합은..."},
    {"question_id": "q_counterexample_001", "learner_response": "(0,1) 구간은..."}
  ],
  "grader": "mock"
}
```

응답 (200):
```json
{
  "attempt_count": 2,
  "results": [
    {
      "question_id": "q_formal_001",
      "accuracy_score": 0.9,
      "feedback": "정확합니다.",
      "mastery_before": "unknown",
      "mastery_after": "solid"
    }
  ],
  "overall_summary": "2개 질문 중 2개 정답. formal: unknown → solid."
}
```

**내부 로직**: 기존 `POST /api/sessions` 로직(`routers/sessions.py`)을 내부 위임 호출. `RunSessionRequest` 구성 → `run_recall_session()` 호출.

**오류**:
- 404: 존재하지 않는 세션
- 400: 빈 answers → `{"detail": "인출 응답을 작성해 주세요"}`

**테스트**: 정상 채점, 빈 응답 거부, 기존 세션 API와의 결과 일관성

---

### 6.7 POST /api/study-session/{session_id}/complete — 세션 완료

| 항목 | 내용 |
|------|------|
| **메서드** | POST |
| **단계** | MVP5-4 |
| **목적** | 세션 완료 → STUDY.md 패치 적용 → 한국어 요약 반환 |

**요청**: 빈 body (`{}`)

**응답 스키마**:
```python
class CompleteSessionResponse(BaseModel):
    session_id: str
    summary_ko: str
    mastery_changes: list[MasteryChange]
    next_review_date: str | None
    study_md_updated: bool
```

**JSON 예시**:

응답 (200):
```json
{
  "session_id": "a1b2c3d4-...",
  "summary_ko": "오늘 다룬 내용: compactness (5가지 표현)\n숙련도 변화: formal unknown→solid, intuitive unknown→partial\n다음 복습일: 2026-05-09\n남은 선행: open_cover (미확인)",
  "mastery_changes": [
    {"representation": "formal", "before": "unknown", "after": "solid"},
    {"representation": "intuitive", "before": "unknown", "after": "partial"}
  ],
  "next_review_date": "2026-05-09",
  "study_md_updated": true
}
```

**내부 로직**:
1. recall 단계 완료 여부 확인 → 미완료 시 400
2. `apply_patch(study_md_path, session)` 호출 → STUDY.md 업데이트
3. `compute_next_review_date()` → 다음 복습일 계산
4. 한국어 요약 문자열 생성
5. `study_session_state.json` → completed 마킹

**오류**:
- 400: recall 미완료 → `{"detail": "인출 연습을 먼저 완료해야 합니다"}`
- 404: 존재하지 않는 세션
- 409: 이미 완료된 세션 → `{"detail": "이미 완료된 세션입니다"}`

**테스트**: 정상 완료 + STUDY.md 패치 확인, recall 미완료 거부, 중복 완료 거부, STUDY.md 백업 생성 확인

---

## 7. 데이터 모델

### 7.1 StudySession 상태 아티팩트

파일 경로: `runs/{session_id}/study_session_state.json`

기존 12 아티팩트 구조와 동일한 디렉토리에 추가. `concept_service.py`의 `compile_concept()`이 이미 `runs/{session_id}/`를 사용하고, `GET /api/sessions/{id}`가 이 디렉토리에서 읽음.

**스키마**:

```json
{
  "session_id": "a1b2c3d4-...",
  "concept_id": "compactness",
  "canonical_name_ko": "옹골성",
  "session_type": "study",
  "current_step": 3,
  "steps": ["diagnose", "prerequisites", "representations", "misconceptions", "recall", "summary"],
  "steps_completed": ["diagnose", "prerequisites"],
  "diagnosis": {
    "prior_knowledge": "...",
    "gap_description": "...",
    "initial_mastery_estimate": "partial",
    "identified_gaps": ["..."],
    "submitted_at": "2026-05-06T14:30:00Z"
  },
  "self_explanations": {
    "formal": {
      "learner_response": "...",
      "accuracy_score": 0.85,
      "missing_elements": ["..."],
      "errors": [],
      "feedback": "...",
      "submitted_at": "2026-05-06T14:35:00Z"
    }
  },
  "recall_session_id": null,
  "recall_completed": false,
  "completed": false,
  "created_at": "2026-05-06T14:28:00Z",
  "completed_at": null
}
```

**필드 설명**:

| 필드 | 타입 | 설명 |
|------|------|------|
| `session_id` | str | UUID. `run_new_concept_session()`에 전달한 것과 동일 |
| `concept_id` | str | 정규화된 개념 ID |
| `canonical_name_ko` | str | 한국어 정식 명칭 |
| `session_type` | str | 항상 `"study"` |
| `current_step` | int | 현재 단계 (1-6) |
| `steps` | list[str] | 6단계 이름 (고정) |
| `steps_completed` | list[str] | 완료된 단계 목록 |
| `diagnosis` | object \| null | 진단 데이터 (4절 #4) |
| `self_explanations` | dict[str, object] | 표현별 자기 설명 결과 |
| `recall_session_id` | str \| null | 연결된 recall 세션 ID (`POST /api/sessions` 결과) |
| `recall_completed` | bool | 인출 단계 완료 여부 |
| `completed` | bool | 전체 세션 완료 여부 |
| `created_at` | str | ISO 8601 생성 시각 |
| `completed_at` | str \| null | ISO 8601 완료 시각 |

### 7.2 기존 아티팩트와의 관계

```
runs/{session_id}/
  ├── source_manifest.json        ← Stage 0 (기존)
  ├── source_excerpt.md           ← Stage 0 (기존)
  ├── concept_decomposition.json  ← Stage 1 (기존)
  ├── prerequisite_graph.json     ← Stage 2 (기존)
  ├── representation_cards.md     ← Stage 3 (기존)
  ├── representation_set.json     ← Stage 3 (기존)
  ├── self_explanation_prompt.md  ← Stage 5 (기존)
  ├── diagnosis.json              ← Stage 4 (기존)
  ├── recall_tasks.md             ← Stage 6 (기존)
  ├── recall_tasks.json           ← Stage 6 (기존)
  ├── STUDY.patch.md              ← Stage 7 (기존)
  ├── session.json                ← 세션 메타 (기존)
  ├── study_session_state.json    ← MVP5 신규
  ├── self_explanations.json      ← MVP5-4 신규 (자기 설명 응답 저장)
  ├── recall_attempts.json        ← MVP5-4 신규 (인출 응답 저장)
  └── llm_traces/                 ← 기존 (LLM 추적)
```

---

## 8. 프론트엔드 컴포넌트 계획

### 8.1 컴포넌트 구조

```
apps/web/src/
  pages/
    StudySession.tsx          ← 신규 (MVP5-1). 6단계 세션 오케스트레이터
  components/
    study/
      StudyStepper.tsx        ← 신규 (MVP5-1). 6단계 진행 표시바
      DiagnosisStep.tsx       ← 신규 (MVP5-1). 1단계: 사전 지식 + 갭 입력
      PrerequisiteStep.tsx    ← 신규 (MVP5-1). 2단계: 선행 개념 목록 + 체크
      RepresentationStep.tsx  ← 신규 (MVP5-1). 3단계: 표현 카드 + 자기 설명
      SelfExplanationStep.tsx ← 신규 (MVP5-4). 자기 설명 textarea + 피드백 (RepresentationStep 내부)
      WhiteRecallStep.tsx     ← 신규 (MVP5-3). 5단계: 질문 + textarea
      SessionSummaryStep.tsx  ← 신규 (MVP5-4). 6단계: 한국어 요약
  api/
    client.ts                 ← 수정 (MVP5-3). study-session API 함수 추가
    types.ts                  ← 수정 (MVP5-3). StudySession 관련 타입 추가
```

### 8.2 컴포넌트 상세

#### `StudySession.tsx` (페이지)

```typescript
// 핵심 상태
const [session, setSession] = useState<StudySessionData | null>(null);
const [currentStep, setCurrentStep] = useState(0);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);

// conceptId from URL param
const { conceptId } = useParams<{ conceptId: string }>();
```

- URL: `/study/:conceptId`
- 초기 로드 시 `POST /api/study-session` 호출 → 세션 생성
- 각 단계 컴포넌트를 조건부 렌더링
- 단계 전환: `advance()` 호출 → `currentStep` 증가

#### `StudyStepper.tsx` (컴포넌트)

```typescript
interface StudyStepperProps {
  steps: string[];        // ["진단", "선행", "표현", "오개념", "인출", "정리"]
  currentStep: number;    // 0-5
  completedSteps: number[];
}
```

- 6단계 진행 표시바: 완료(체크) / 현재(강조) / 미완(비활성)
- 한국어 레이블: `["진단", "선행 확인", "표현 학습", "오개념 체크", "인출 연습", "세션 정리"]`
- 완료된 단계 클릭 시 해당 단계 표시 (읽기 전용)

#### `DiagnosisStep.tsx`

```typescript
interface DiagnosisStepProps {
  onSubmit: (priorKnowledge: string, gapDescription: string) => void;
  loading: boolean;
}
```

- textarea 2개: "이 개념에 대해 알고 있는 것을 적어 주세요", "어디서 막히거나 헷갈리나요?"
- "다음 단계 →" 버튼
- 빈 입력 허용 (진단은 선택적 — 학습자가 "모르겠다"고 할 수 있음)

#### `PrerequisiteStep.tsx`

```typescript
interface PrerequisiteStepProps {
  prerequisites: PrerequisiteInfo[];
  onContinue: () => void;
}
```

- 선행 개념 목록: checkbox + "편하게 설명할 수 있나요?"
- mastery=unknown인 선행이 있으면 경고: "⚠ {concept}의 숙련도가 '미확인'입니다"
- "그래도 계속" / "선행부터 학습" 선택지 (선행 학습은 `/study/{prerequisite}` 이동)

#### `RepresentationStep.tsx`

```typescript
interface RepresentationStepProps {
  representations: Record<string, string>;  // {formal: "...", ...}
  sessionId: string;
  onAllCompleted: () => void;
}
```

- 5가지 표현을 순차 표시: `[1/5] 정의 (formal)` → `[2/5] 직관 (intuitive)` → ...
- 각 표현 카드 하단에 `SelfExplanationStep` 렌더링 (MVP5-4)
- MVP5-1/3에서는 자기 설명 없이 "다음 표현 →" 버튼만

#### `SelfExplanationStep.tsx` (MVP5-4)

```typescript
interface SelfExplanationStepProps {
  sessionId: string;
  representationType: string;
  onSubmitted: (result: SelfExplainResponse) => void;
}
```

- textarea: "이 표현을 자기 말로 설명해 보세요"
- "제출" → `POST .../self-explain` 호출
- 피드백 표시: accuracy_score, missing_elements, feedback (한국어)
- 제출 전에는 "다음 표현" 비활성 (자기 설명 필수)

#### `WhiteRecallStep.tsx`

```typescript
interface WhiteRecallStepProps {
  questions: RecallQuestion[];
  sessionId: string;
  onSubmitted: (result: StudyRecallResponse) => void;
}
```

- 안내: "교재를 덮고, 처음부터 설명해 보세요"
- 각 질문별 textarea
- "제출" → `POST .../recall` 호출
- 건너뛸 수 없음 (필수 단계)

#### `SessionSummaryStep.tsx` (MVP5-4)

```typescript
interface SessionSummaryStepProps {
  summary: CompleteSessionResponse;
}
```

- 한국어 요약: "오늘 다룬 내용", "숙련도 변화" (표), "다음 복습일", "남은 선행"
- "대시보드로 돌아가기" / "다른 개념 공부하기" 링크

### 8.3 API 타입 추가 (`types.ts`)

```typescript
// MVP5 Study Session types
interface PrerequisiteInfo {
  concept_id: string;
  name_ko: string;
  mastery: string;
}

interface MisconceptionInfo {
  id: string;
  claim: string;
  is_correct: boolean;
}

interface CreateStudySessionResponse {
  session_id: string;
  concept_id: string;
  canonical_name_ko: string;
  current_step: number;
  steps: string[];
  representations: Record<string, string>;
  prerequisites: PrerequisiteInfo[];
  misconceptions: MisconceptionInfo[];
}

interface StudySessionState {
  session_id: string;
  concept_id: string;
  canonical_name_ko: string;
  current_step: number;
  steps_completed: string[];
  diagnosis: DiagnosisData | null;
  self_explanations: Record<string, SelfExplanationResult> | null;
  recall_completed: boolean;
  created_at: string;
}

interface DiagnosisData {
  prior_knowledge: string;
  gap_description: string;
}

interface DiagnoseResponse {
  initial_mastery_estimate: string;
  identified_gaps: string[];
  recommendation: string;
}

interface SelfExplainResponse {
  accuracy_score: number;
  missing_elements: string[];
  errors: string[];
  feedback: string;
}

interface RecallResult {
  question_id: string;
  accuracy_score: number;
  feedback: string;
  mastery_before: string;
  mastery_after: string;
}

interface StudyRecallResponse {
  attempt_count: number;
  results: RecallResult[];
  overall_summary: string;
}

interface MasteryChange {
  representation: string;
  before: string;
  after: string;
}

interface CompleteSessionResponse {
  session_id: string;
  summary_ko: string;
  mastery_changes: MasteryChange[];
  next_review_date: string | null;
  study_md_updated: boolean;
}
```

### 8.4 API 클라이언트 함수 추가 (`client.ts`)

```typescript
export async function createStudySession(conceptId: string): Promise<CreateStudySessionResponse> { ... }
export async function getStudySession(sessionId: string): Promise<StudySessionState> { ... }
export async function submitDiagnosis(sessionId: string, data: DiagnosisData): Promise<DiagnoseResponse> { ... }
export async function advanceStep(sessionId: string, completedStep: string): Promise<AdvanceResponse> { ... }
export async function submitSelfExplanation(sessionId: string, data: SelfExplainRequest): Promise<SelfExplainResponse> { ... }
export async function submitRecall(sessionId: string, data: StudyRecallRequest): Promise<StudyRecallResponse> { ... }
export async function completeSession(sessionId: string): Promise<CompleteSessionResponse> { ... }
```

---

## 9. LLM 정책

### 원칙: MVP5 전체에서 실제 LLM을 활성화하지 않는다.

| 항목 | 정책 |
|------|------|
| 컴파일 파이프라인 | `MockLLMClient()` 유지 (`concept_service.py:95`). `LLM_DISABLED=1` (기본값) 변경 금지 |
| 자기 설명 평가 | `evaluate_self_explanation()` → MockLLMClient fixture 응답. 결정적 |
| 인출 채점 | `grader: 'mock'` 고정. 기존 `POST /api/sessions` 경로의 mock 채점 재사용 |
| 진단 | 키워드 매칭 기반 (`GAP_CUES`). LLM 없음 |
| `.env` | `OPENAI_API_KEY`는 `.env`에만 존재. 코드에 하드코딩 절대 금지 |
| 테스트 | LLM 관련 테스트는 mock만 사용. CI에서 실제 API 호출 없음 |

### MVP6에서 활성화할 것

- `concept_service.py`의 `MockLLMClient()` → `make_llm_client()` (설정 기반 분기)
- `REPRESENTATION_PREVIEWS` → fallback으로 격하 (LLM 실패 시에만)
- 자기 설명 LLM 평가: `evaluate_self_explanation()` → 실제 LLM
- 가드레일: JSON 스키마 검증, 1회 재시도, 30초 타임아웃, 세션당 30,000 토큰 상한
- UI 경고 배너: "AI 생성 — 교재에서 검증하세요"

### LLM 실패가 흐름을 깨뜨리면 안 된다

MVP5에서는 모든 LLM 경로가 mock이므로 실패 가능성이 극히 낮다. 그러나 방어적으로:
- MockLLMClient fixture 미매칭 시 빈 응답 반환 (에러 아님)
- 자기 설명 평가 실패 시 기본 피드백 반환: `{"accuracy_score": 0.0, "feedback": "평가를 수행할 수 없습니다"}`
- 파이프라인 실패 시 세션 생성 거부 (500) — 학습자에게 "다시 시도해 주세요" 안내

---

## 10. 테스트 전략

### 10.1 자동화 테스트

#### pytest (백엔드)

| 범주 | 테스트 | 파일 | 단계 |
|------|--------|------|------|
| API CRUD | 세션 생성/조회/진단/진행/자기설명/인출/완료 | `tests/test_api_study_session.py` (신규) | MVP5-2/4 |
| 서비스 로직 | 단계 전환, recall 필수 검증, 자동 bank 준비 | `tests/test_study_session_service.py` (신규) | MVP5-2/3 |
| 아티팩트 | `study_session_state.json` 생성/업데이트 확인 | `tests/test_study_session_artifacts.py` (신규) | MVP5-2 |
| STUDY.md | complete 후 패치 적용 + 검증 | `tests/test_study_session_complete.py` (신규) | MVP5-4 |
| 자기 설명 | evaluate_self_explanation → RecallEvaluation 반환 | 기존 `tests/` (자기 설명 관련) | MVP5-4 |
| 회귀 | 기존 ~975 테스트 전체 통과 | 기존 `tests/` 전체 | 모든 단계 |

#### npm 빌드 (프론트엔드)

```bash
cd apps/web && npm run build
```

모든 단계에서 빌드 성공 확인. TypeScript 컴파일 에러 0.

### 10.2 수동 테스트 시나리오 (MVP5-5 도그푸딩)

| # | 시나리오 | 전제 조건 | 기대 결과 |
|---|---------|----------|----------|
| 1 | **첫 사용자 전체 흐름** | 빈 STUDY.md, 소스 파일 1개 존재 | ChatCompiler → 개념 입력 → "공부 시작" → `/study/compactness` → 6단계 완주 → STUDY.md에 compactness 기록 |
| 2 | **기존 소스 있는 개념** | compactness 소스 이미 업로드됨, STUDY.md에 compactness 없음 | 세션 생성 시 기존 소스 자동 탐색 → 정상 진행 |
| 3 | **소스 없는 개념** | connectedness의 소스 없음 | 세션 생성 실패 → 에러 안내 → ChatCompiler로 복귀 |
| 4 | **인출 + STUDY.md 업데이트** | compactness 세션 5단계까지 진행 | 인출 제출 → complete → STUDY.md 패치 → `/dashboard`에서 mastery 변화 확인 |
| 5 | **한국어 UX 전체 확인** | 정상 데이터 | `/` → `/study` → `/dashboard` → `/recall` 경로에서 영어 UI 문자열 0개 |

### 10.3 데이터 안전 확인

```bash
git status                          # 추적되지 않은 민감 파일 없음
git check-ignore .env               # .env가 gitignore에 포함
git grep "sk-" -- ':!*.md'          # API key 하드코딩 없음
git diff --stat                     # 의도하지 않은 파일 변경 없음
```

---

## 11. 수락 기준 / 완료 정의

| 단계 | 수락 기준 | 완료 정의 (DoD) | 배포 결정 |
|------|----------|-----------------|----------|
| **MVP5-0** | (1) Dashboard 전체 한국어 (2) RecallSession 전체 한국어 (3) 학습자 경로에서 영어 0개 | 기존 테스트 통과 + `npm run build` 성공 + 수동 확인 | ❌ 배포 불가 — 통합 세션 없음 |
| **MVP5-1** | (1) `/study/compactness` 접근 시 6단계 스텝퍼 렌더링 (2) 단계 간 전환 가능 (3) 전체 한국어 (4) ChatCompiler "공부 시작" → `/study` 이동 | 기존 테스트 통과 + `npm run build` 성공 | ❌ 배포 불가 — 백엔드 없음 |
| **MVP5-2** | (1) `POST /api/study-session` → 세션 생성 + 아티팩트 확인 (2) `GET .../` → 상태 반환 (3) `POST .../diagnose` → 저장 + 응답 (4) `POST .../advance` → 단계 진행 | 신규 API 테스트 + 기존 회귀 없음 | ❌ 배포 불가 — 프론트 미연결 |
| **MVP5-3** | (1) 세션 자동 생성 (수동 컴파일 불필요) (2) 표현 5개 표시 (3) 선행 목록 표시 (4) 인출 제출 가능 (5) bank 자동 준비 | E2E 흐름 통과 + 기존 회귀 없음 | ⚠ 내부 테스트 가능 |
| **MVP5-4** | (1) 자기 설명 제출 → 피드백 반환 (2) 인출 필수 (건너뛸 수 없음) (3) complete → STUDY.md 패치 (4) 세션 요약 한국어 | 전체 6단계 완주 E2E + STUDY.md 무결성 | ⚠ 내부 테스트 배포 가능 |
| **MVP5-5** | (1) 5가지 수동 시나리오 전체 통과 (2) 학습자 경로 영어 0개 (3) 기존 975+ 테스트 통과 (4) `npm run build` 성공 | 도그푸딩 게이트 통과 | ✅ MVP6 진행 가능 |

---

## 12. 엔지니어링 태스크 목록

| # | 단계 | 태스크 | 파일 | 상세 | 테스트 | 위험 |
|---|------|--------|------|------|--------|------|
| 1 | MVP5-0 | Dashboard 한국어화 (~40개 문자열) | `Dashboard.tsx` | "Dashboard"→"대시보드", "Review Due"→"복습 예정" 등. 로직 변경 없음 | 기존 Playwright 통과 | 극히 낮음 |
| 2 | MVP5-0 | RecallSession 한국어화 (~30개 문자열) | `RecallSession.tsx` | "Recall Session"→"인출 연습", "Submit"→"제출" 등. 로직 변경 없음 | 기존 Playwright 통과 | 극히 낮음 |
| 3 | MVP5-0 | 빈 상태 한국어 안내 개선 | `Dashboard.tsx`, `RecallSession.tsx` | empty state 메시지 한국어 개선 | 수동 확인 | 극히 낮음 |
| 4 | MVP5-0 | 배지/상태 문자열 한국어화 | `Dashboard.tsx` | "solid"→"완전", "partial"→"부분", "unknown"→"미확인", "overdue"→"초과", "due"→"예정" | 수동 확인 | 극히 낮음 |
| 5 | MVP5-1 | `StudySession.tsx` 6단계 스텝퍼 | 신규 `pages/StudySession.tsx` | 6단계 UI shell. React state로 단계 관리. placeholder 컴포넌트 | `npm run build` 성공 | 낮음 |
| 6 | MVP5-1 | `StudyStepper.tsx` 진행 표시 | 신규 `components/study/StudyStepper.tsx` | 6단계 진행바 + 한국어 레이블 | `npm run build` 성공 | 낮음 |
| 7 | MVP5-1 | `DiagnosisStep.tsx` | 신규 `components/study/DiagnosisStep.tsx` | textarea 2개 + "다음 단계" 버튼 | `npm run build` 성공 | 낮음 |
| 8 | MVP5-1 | `PrerequisiteStep.tsx` | 신규 `components/study/PrerequisiteStep.tsx` | 선행 목록 + checkbox + mastery 경고 | `npm run build` 성공 | 낮음 |
| 9 | MVP5-1 | `RepresentationStep.tsx` | 신규 `components/study/RepresentationStep.tsx` | 5개 표현 카드 순차 표시 | `npm run build` 성공 | 낮음 |
| 10 | MVP5-1 | `WhiteRecallStep.tsx` | 신규 `components/study/WhiteRecallStep.tsx` | 질문 + textarea placeholder | `npm run build` 성공 | 낮음 |
| 11 | MVP5-1 | `SessionSummaryStep.tsx` | 신규 `components/study/SessionSummaryStep.tsx` | 요약 placeholder | `npm run build` 성공 | 낮음 |
| 12 | MVP5-1 | `/study/:conceptId` 라우트 등록 | `App.tsx` | Route 추가 + import | `npm run build` 성공 | 극히 낮음 |
| 13 | MVP5-1 | ChatCompiler "공부 시작" → `/study` 연결 | `ChatCompiler.tsx` 또는 `compiler_analyzer_service.py` | `recommended_actions`에 `/study/{concept_id}` route 추가. 또는 프론트엔드에서 직접 Link | `npm run build` 성공 | 낮음 |
| 14 | MVP5-2 | Pydantic 스키마 추가 | `api_schemas.py` | CreateStudySessionRequest/Response, DiagnoseRequest/Response 등 8개 모델 | pytest import 확인 | 낮음 |
| 15 | MVP5-2 | `study_session_service.py` 서비스 | 신규 `services/study_session_service.py` | create, get, diagnose, advance 메서드 | `test_study_session_service.py` | 중간 — `run_new_concept_session` 통합 |
| 16 | MVP5-2 | `study_session.py` 라우터 | 신규 `routers/study_session.py` | POST/GET/diagnose/advance 4개 엔드포인트 | `test_api_study_session.py` | 낮음 |
| 17 | MVP5-2 | `main.py` 라우터 등록 | `main.py` | `app.include_router(study_session_router)` | 기존 테스트 회귀 없음 | 극히 낮음 |
| 18 | MVP5-2 | `study_session_state.json` 영속화 | `study_session_service.py` | 생성/읽기/업데이트. `runs/{session_id}/` 디렉토리 사용 | `test_study_session_artifacts.py` | 낮음 |
| 19 | MVP5-2 | 세션 생성 시 기존 파이프라인 호출 | `study_session_service.py` | `run_new_concept_session(MockLLMClient)` 호출 | 통합 테스트 | 중간 — 소스 파일 의존 |
| 20 | MVP5-3 | API 클라이언트 함수 추가 | `client.ts` | 7개 함수: createStudySession, getStudySession, ... | TypeScript 컴파일 | 낮음 |
| 21 | MVP5-3 | TypeScript 타입 추가 | `types.ts` | 12+ 인터페이스 (8절 참조) | TypeScript 컴파일 | 낮음 |
| 22 | MVP5-3 | `StudySession.tsx` 백엔드 연결 | `StudySession.tsx` | 세션 생성 → 아티팩트 로드 → 단계별 데이터 표시 | E2E 흐름 | 중간 |
| 23 | MVP5-3 | 표현 단계 데이터 바인딩 | `RepresentationStep.tsx` | `representation_set.json` 데이터 표시 | E2E | 낮음 |
| 24 | MVP5-3 | 선행 단계 데이터 바인딩 | `PrerequisiteStep.tsx` | `prerequisite_graph.json` 데이터 표시 + mastery 표시 | E2E | 낮음 |
| 25 | MVP5-3 | 오개념 단계 읽기 전용 표시 | `RepresentationStep.tsx` 또는 별도 | `diagnosis.json` misconceptions 표시 | E2E | 낮음 |
| 26 | MVP5-3 | 인출 단계 질문 로드 | `WhiteRecallStep.tsx` | `recall_tasks.json` 또는 bank에서 질문 로드 | E2E | 낮음 |
| 27 | MVP5-3 | 자동 bank 준비 | `study_session_service.py` | `questions.generated.json` → `questions.accepted.json` 복사 | pytest | 낮음 |
| 28 | MVP5-4 | `SelfExplanationStep.tsx` | 신규 `components/study/SelfExplanationStep.tsx` | textarea + 제출 + 피드백 표시 | `npm run build` | 낮음 |
| 29 | MVP5-4 | `POST .../self-explain` 엔드포인트 | `routers/study_session.py` | `evaluate_self_explanation()` 호출 (MockLLM) | `test_api_study_session.py` | 낮음 — 기존 함수 재사용 |
| 30 | MVP5-4 | `POST .../recall` 엔드포인트 | `routers/study_session.py` | `POST /api/sessions` 로직 위임 | `test_api_study_session.py` | 낮음 — 기존 로직 재사용 |
| 31 | MVP5-4 | `POST .../complete` 엔드포인트 | `routers/study_session.py` | recall 필수 검증 + `apply_patch()` + 한국어 요약 | `test_study_session_complete.py` | 중간 — STUDY.md 무결성 |
| 32 | MVP5-4 | White Recall 필수화 | `StudySession.tsx` | 5단계 미완료 시 6단계 진입 불가 (프론트 + 백 양쪽) | E2E + pytest | 낮음 |
| 33 | MVP5-4 | 자기 설명 필수화 | `RepresentationStep.tsx`, `SelfExplanationStep.tsx` | 자기 설명 미제출 시 다음 표현 비활성 | E2E | 낮음 |
| 34 | MVP5-4 | `SessionSummaryStep.tsx` 데이터 바인딩 | `SessionSummaryStep.tsx` | complete 응답 → 한국어 요약 표시 | E2E | 낮음 |
| 35 | MVP5-4 | `self_explanations.json` 아티팩트 저장 | `study_session_service.py` | 자기 설명 응답 + 평가 결과 영속화 | pytest 아티팩트 확인 | 낮음 |
| 36 | MVP5-4 | `recall_attempts.json` 아티팩트 저장 | `study_session_service.py` | 인출 응답 + 채점 결과 영속화 | pytest 아티팩트 확인 | 낮음 |
| 37 | MVP5-5 | 도그푸딩 시나리오 1: 첫 사용자 전체 흐름 | — | 빈 STUDY.md → 전체 6단계 완주 | 수동 | — |
| 38 | MVP5-5 | 도그푸딩 시나리오 2: 기존 소스 | — | 기존 소스 자동 탐색 → 정상 진행 | 수동 | — |
| 39 | MVP5-5 | 도그푸딩 시나리오 3: 소스 없음 | — | 에러 안내 → ChatCompiler 복귀 | 수동 | — |
| 40 | MVP5-5 | 도그푸딩 시나리오 4: STUDY.md 업데이트 | — | complete → 패치 → Dashboard 확인 | 수동 | — |
| 41 | MVP5-5 | 도그푸딩 시나리오 5: 한국어 전체 확인 | — | 학습자 경로 영어 0개 | 수동 | — |
| 42 | MVP5-5 | 전체 테스트 회귀 확인 | — | `python -m pytest tests/ -q` 전체 통과 | 자동 | — |
| 43 | MVP5-5 | 프론트엔드 빌드 확인 | — | `cd apps/web && npm run build` 성공 | 자동 | — |

---

## 13. Claude Code 프롬프트

### MVP5-0 프롬프트

```
/plan

## 목표
Dashboard.tsx와 RecallSession.tsx의 모든 영어 UI 문자열을 한국어로 교체.

## 범위
- Dashboard.tsx: ~40개 영어 문자열 (headings, CTAs, table headers, badges, empty states)
  - "Dashboard" → "대시보드"
  - "API Status" → "API 상태"
  - "Review Due" → "복습 예정"
  - "Weak Representations" → "취약 표현"
  - "Recent Sessions" → "최근 세션"
  - "STUDY.md State" → "STUDY.md 상태"
  - 배지: "solid"→"완전", "partial"→"부분", "unknown"→"미확인", "overdue"→"초과", "due"→"예정"
  - CTA: "Resume:"→"복습:", "Strengthen:"→"강화:", etc.
  - 테이블 헤더: "Concept"→"개념", "Mastery"→"숙련도", etc.
  - 빈 상태: "Nothing due for review."→"복습 예정인 개념이 없습니다.", "No sessions yet."→"아직 세션이 없습니다."
- RecallSession.tsx: ~30개 영어 문자열
  - "Recall Session"→"인출 연습", "Select a Question Bank"→"문제은행 선택"
  - "Submit (mock grader)"→"제출 (모의 채점)", "Session Created"→"세션 생성 완료"
  - "Mastery Changes"→"숙련도 변화", "Weak Questions"→"취약 질문"
  - 빈 상태/에러 메시지 한국어화

## 비범위
- 개발자 도구 페이지 (SourceUpload, BankBrowser, ConceptCompiler, SessionHistory, SessionDetail) — 변경 금지
- i18n 라이브러리 도입 금지
- Layout.tsx — 이미 한국어 (변경 불필요)
- API 변경 없음

## 파일
- apps/web/src/pages/Dashboard.tsx
- apps/web/src/pages/RecallSession.tsx

## 테스트
- python -m pytest tests/ -q (기존 전체 통과)
- cd apps/web && npm run build (성공)
- 수동: Dashboard/RecallSession에서 영어 문자열 0개 확인

## 수락 기준
학습자 대면 3개 페이지 (/, /dashboard, /recall)에서 영어 UI 문자열 0개.
```

---

### MVP5-1 프롬프트

```
/plan

## 목표
/study/:conceptId 라우트에 6단계 한국어 스텝퍼 UI 구현. 백엔드 없이 프론트엔드 placeholder.

## 범위
- 신규 StudySession.tsx (pages/) — 6단계 오케스트레이터
- 신규 StudyStepper.tsx (components/study/) — 진행 표시바
- 신규 DiagnosisStep.tsx — textarea 2개 (사전 지식 / 갭)
- 신규 PrerequisiteStep.tsx — checkbox 목록 placeholder
- 신규 RepresentationStep.tsx — 표현 카드 placeholder (5개)
- 신규 WhiteRecallStep.tsx — textarea placeholder
- 신규 SessionSummaryStep.tsx — 요약 placeholder
- App.tsx 수정: <Route path="/study/:conceptId" element={<StudySession />} />
- ChatCompiler.tsx 수정: "공부 시작" 버튼에 Link to={`/study/${conceptId}`} 추가
  - recommended_actions에서 route가 null이고 action_id가 study_start인 액션에 대해
    프론트엔드에서 /study/{concept_id} 링크 생성
  - 또는 compiler_analyzer_service.py에서 route: "/study/{concept_id}" 반환

## 비범위
- 백엔드 API 없음
- 실제 데이터 바인딩 없음 (placeholder 텍스트 사용)
- LLM 없음

## 단계 이름 (한국어)
1. 진단 — "이 개념에 대해 알고 있는 것을 적어 주세요"
2. 선행 확인 — "이 개념을 공부하려면 다음 개념이 필요합니다"
3. 표현 학습 — "[1/5] 정의 (formal)" ... "[5/5] 증명 구조 (proof_schema)"
4. 오개념 체크 — "주의할 오개념"
5. 인출 연습 — "교재를 덮고, 처음부터 설명해 보세요"
6. 세션 정리 — "오늘 다룬 내용"

## 파일
- 신규: apps/web/src/pages/StudySession.tsx
- 신규: apps/web/src/components/study/*.tsx (6개)
- 수정: apps/web/src/App.tsx
- 수정: apps/web/src/pages/ChatCompiler.tsx (또는 compiler_analyzer_service.py)

## 테스트
- cd apps/web && npm run build (성공)
- 수동: /study/compactness 접근 → 6단계 스텝퍼 렌더링 → 단계 전환 → 전체 한국어

## 수락 기준
(1) /study/compactness 접근 시 6단계 한국어 스텝퍼 렌더링
(2) 단계 간 전환 가능 (이전/다음 버튼)
(3) ChatCompiler에서 "공부 시작" → /study/compactness 이동
(4) 전체 한국어
```

---

### MVP5-2 프롬프트

```
/plan

## 목표
통합 학습 세션 백엔드 API 4개 엔드포인트 구현.

## 범위
- POST /api/study-session — 세션 생성
  - concept_id 수신 → resolve_concept() → run_new_concept_session(MockLLMClient) → 12 아티팩트 생성
  - study_session_state.json 생성 (runs/{session_id}/)
  - 응답: session_id, concept_id, canonical_name_ko, current_step, steps, representations, prerequisites, misconceptions
- GET /api/study-session/{id} — 세션 상태 조회
- POST /api/study-session/{id}/diagnose — 진단 텍스트 수신 + 저장 + 결정적 평가
  - GAP_CUES 키워드 매칭 재사용 (compiler_analyzer_service.py의 로직)
- POST /api/study-session/{id}/advance — 단계 진행 (순서 검증)

## 기존 코드 재사용
- session.py: run_new_concept_session() — 12 아티팩트 생성 오케스트레이터
- concept_service.py: compile_concept() 패턴 참조 (MockLLMClient 사용, 아티팩트 로드)
- config.py: RUNS_DIR, BANK_ROOT, STUDY_MD, SOURCES_DIR
- real_analysis.py: CONCEPTS (canonical_name 포함), PREREQUISITE_EDGES

## 비범위
- self-explain, recall, complete 엔드포인트 (MVP5-4에서)
- LLM 없음 (MockLLMClient 유지)
- 프론트엔드 변경 없음

## 파일
- 신규: apps/api/routers/study_session.py
- 신규: apps/api/services/study_session_service.py
- 수정: apps/api/schemas/api_schemas.py (8+ 새 Pydantic 모델)
- 수정: apps/api/main.py (라우터 등록)

## 테스트
- python -m pytest tests/ -q (전체 통과)
- 신규: tests/test_api_study_session.py — CRUD 테스트 (생성/조회/진단/진행)
- 신규: tests/test_study_session_service.py — 서비스 단위 테스트

## 수락 기준
(1) POST /api/study-session {"concept_id": "compactness"} → 201 + session_id
(2) GET /api/study-session/{id} → 200 + 세션 상태
(3) POST .../diagnose → 200 + 진단 결과
(4) POST .../advance → 200 + 다음 단계
(5) runs/{session_id}/study_session_state.json 생성 확인
(6) 기존 테스트 회귀 없음
```

---

### MVP5-3 프롬프트

```
/plan

## 목표
StudySession 프론트엔드를 MVP5-2 백엔드에 연결. 자동 bank 준비. 학습자 경로에서 수동 리뷰 제거.

## 범위
- client.ts에 study-session API 함수 7개 추가 (8.4절 참조)
- types.ts에 StudySession 관련 TypeScript 타입 12+ 추가 (8.3절 참조)
- StudySession.tsx: 마운트 시 POST /api/study-session → 세션 생성 → 아티팩트 로드
- RepresentationStep.tsx: representations 데이터 표시 (mock 생성 텍스트)
- PrerequisiteStep.tsx: prerequisites 데이터 표시 + mastery 배지
- WhiteRecallStep.tsx: recall_tasks.json 질문 로드 → textarea → 제출 가능
- 자동 bank 준비: study_session_service.py에서 questions.generated.json → questions.accepted.json 복사
  (학습자 경로에서 수동 BankReview 생략)
- bank 리뷰는 /review/:id (개발자 도구)에 유지 — 삭제 금지

## 비범위
- 자기 설명 수집/평가 (MVP5-4)
- LLM 없음
- complete 엔드포인트 (MVP5-4)

## 파일
- 수정: apps/web/src/api/client.ts
- 수정: apps/web/src/api/types.ts
- 수정: apps/web/src/pages/StudySession.tsx
- 수정: apps/web/src/components/study/RepresentationStep.tsx
- 수정: apps/web/src/components/study/PrerequisiteStep.tsx
- 수정: apps/web/src/components/study/WhiteRecallStep.tsx
- 수정: apps/api/services/study_session_service.py (자동 bank 준비)

## 테스트
- python -m pytest tests/ -q (전체 통과)
- cd apps/web && npm run build (성공)
- 수동: ChatCompiler → "공부 시작" → /study/compactness → 세션 생성 → 표현 표시 → 인출 가능

## 수락 기준
(1) 학습자가 수동 bank 빌드/리뷰 없이 세션 진행 가능
(2) 표현 5개 실제 데이터 표시
(3) 선행 목록 실제 데이터 표시
(4) 인출 질문 실제 데이터 표시 + 제출 가능
```

---

### MVP5-4 프롬프트

```
/plan

## 목표
자기 설명 수집 + mock 평가. White Recall 필수화. STUDY.md 자동 업데이트. 세션 요약 한국어.

## 범위
- 신규 SelfExplanationStep.tsx: 각 표현 후 textarea + "제출" → POST .../self-explain → 피드백 표시
- RepresentationStep.tsx 수정: 자기 설명 미제출 시 다음 표현 비활성
- POST /api/study-session/{id}/self-explain 구현
  - evaluate_self_explanation() 호출 (self_explanation.py:51-80, MockLLMClient)
  - RecallEvaluation → SelfExplainResponse 변환
- POST /api/study-session/{id}/recall 구현
  - 기존 POST /api/sessions 로직 위임 (RunSessionRequest 구성)
- POST /api/study-session/{id}/complete 구현
  - recall_completed 확인 → 미완료 시 400
  - apply_patch(study_md_path, session) 호출 → STUDY.md 업데이트
  - 한국어 요약 생성: "오늘 다룬 내용: {concept}", "숙련도 변화: formal unknown→solid", "다음 복습일: YYYY-MM-DD"
- SessionSummaryStep.tsx 데이터 바인딩: complete 응답 표시
- White Recall 필수화: 프론트(5단계 건너뛰기 불가) + 백(complete 시 recall 확인)
- self_explanations.json + recall_attempts.json 아티팩트 저장

## 기존 코드 재사용
- self_explanation.py:evaluate_self_explanation() — 이미 완전 구현. UI+API만 추가
- writer.py:apply_patch() — STUDY.md 패치 + 백업 + 검증
- writer.py:compute_mastery_state(), compute_next_review_date()
- sessions.py (routers) — POST /api/sessions 로직
- grading/factory.py:make_grader("mock")

## 비범위
- 실제 LLM 평가 (MVP6)
- 오개념 MCQ 대화형 상호작용 (MVP6)
- 스캐폴딩 난이도 분기 (MVP6)

## 파일
- 신규: apps/web/src/components/study/SelfExplanationStep.tsx
- 수정: apps/web/src/components/study/RepresentationStep.tsx (자기 설명 통합 + 필수화)
- 수정: apps/web/src/components/study/SessionSummaryStep.tsx (데이터 바인딩)
- 수정: apps/web/src/pages/StudySession.tsx (complete 호출 + 필수화 로직)
- 수정: apps/api/routers/study_session.py (self-explain, recall, complete 3개 엔드포인트)
- 수정: apps/api/services/study_session_service.py (self-explain, recall, complete 로직)
- 수정: apps/api/schemas/api_schemas.py (SelfExplainRequest/Response 등)

## 테스트
- python -m pytest tests/ -q (전체 통과)
- cd apps/web && npm run build (성공)
- 신규 테스트: self-explain 제출 → RecallEvaluation 반환, recall 미완료 시 complete 거부, complete 후 STUDY.md 패치 확인
- 수동: 전체 6단계 완주 E2E

## 수락 기준
(1) 각 표현 후 자기 설명 제출 가능 + 피드백 표시
(2) 자기 설명 미제출 시 다음 표현 비활성
(3) 인출 미완료 시 세션 완료 불가 (프론트 + 백)
(4) complete → STUDY.md 패치 + 세션 요약 한국어
(5) runs/{session_id}/에 self_explanations.json + recall_attempts.json 생성
```

---

### MVP5-5 프롬프트

```
## 목표
MVP5-0~4 완료 후 도그푸딩 게이트. 수동 시나리오 5개 완주.

## 체크리스트
1. python -m pytest tests/ -q → 전체 통과 (975+ 테스트)
2. cd apps/web && npm run build → 성공
3. 시나리오 1: 빈 STUDY.md → ChatCompiler → "compactness 공부하고 싶어" → 공부 시작 → 6단계 완주 → STUDY.md에 compactness 기록
4. 시나리오 2: 기존 소스 → 세션 생성 시 자동 탐색 → 정상 진행
5. 시나리오 3: 소스 없는 개념 → 에러 안내 → ChatCompiler 복귀
6. 시나리오 4: 인출 제출 → complete → STUDY.md 패치 → Dashboard에서 mastery 확인
7. 시나리오 5: /, /study, /dashboard, /recall 경로에서 영어 UI 문자열 0개
8. git status → 민감 파일 없음
9. git check-ignore .env → gitignore 포함
10. git grep "sk-" -- ':!*.md' → API key 하드코딩 없음
```

---

## 14. 배포 정책

### 원칙

| 원칙 | 내용 |
|------|------|
| **MVP5-0+1 통과 전 배포 금지** | 영어 UI + 통합 세션 없는 상태에서 배포는 제품 정체성 손상 |
| **Oracle은 스테이징 전용** | `docs/deployment/ORACLE_DEPLOYMENT_CHECKLIST.md`의 Oracle 인스턴스는 내부 테스트만 |
| **MVP5는 프로덕션 경화가 아님** | systemd, nginx, HTTPS, 도메인 설정은 MVP6 이후 |
| **LLM 비활성 상태 유지** | `LLM_DISABLED=1` 변경 금지. 가드레일 없이 LLM 활성화 시 환각 위험 |

### 배포 적합성 표

| 마일스톤 | 배포 적합성 | 이유 |
|---------|-----------|------|
| MVP5-0 완료 | ❌ | 한국어는 개선되나 통합 세션 없음 |
| MVP5-1 완료 | ❌ | UI shell만 — 백엔드 없음 |
| MVP5-2 완료 | ❌ | 백엔드 있으나 프론트 미연결 |
| MVP5-3 완료 | ⚠ 내부 테스트 | 전체 흐름 작동하나 자기 설명/인출 필수화 없음 |
| MVP5-4 완료 | ⚠ 내부 도그푸딩 | 6단계 완주 가능. mock만 사용 |
| MVP5-5 통과 | ✅ MVP6 진행 가능 | 도그푸딩 게이트 통과. LLM 활성화 준비 |

---

## 15. 최종 권고

### 지금 즉시: MVP5-0 시작

- **이유**: 코드 변경량 최소 (~70개 문자열 교체), 위험 없음, 학습자 UX 즉시 개선
- **예상 범위**: Dashboard.tsx + RecallSession.tsx 문자열 교체
- **의존성**: 없음 — 다른 단계와 완전 독립

### MVP5-0 직후: MVP5-1 시작

- **이유**: S0-1 (통합 학습 세션 부재) 해소의 첫 단계. 학습 흐름 시각화만으로도 제품 정체성 개선
- **의존성**: 없음 — 백엔드 불필요

### 이후 순서

MVP5-2 (백엔드) → MVP5-3 (통합) → MVP5-4 (자기 설명 + 인출 필수화) → MVP5-5 (도그푸딩)

MVP5-0과 MVP5-1은 **병렬 진행 가능** (서로 독립).
MVP5-2와 MVP5-1도 **병렬 진행 가능** (프론트/백 분리).
MVP5-3은 MVP5-1 + MVP5-2 **양쪽 완료 필요**.

### 하지 말 것

1. **프로덕션 경화 진행 금지** — 제품 적합성이 수리되기 전에 인프라 경화는 시기상조
2. **LLM 활성화 금지** — 가드레일 없이 `LLM_DISABLED=0` 설정 금지
3. **새 도메인/개념 추가 금지** — 기존 3개 seed에서 핵심 루프 증명이 먼저
4. **기존 개발자 도구 삭제 금지** — `/sources`, `/bank`, `/review`, `/concepts`, `/sessions`는 유지
5. **i18n 라이브러리 도입 금지** — 단일 언어 제품, 과도한 추상화

### 의존 관계

```
MVP5-0 (한국어화)         MVP5-1 (UI shell)
    │ (독립)                   │
    │                     MVP5-2 (백엔드) ←── 병렬 가능
    │                          │
    ▼                     MVP5-3 (통합) ←── MVP5-1 + MVP5-2 양쪽 필요
                               │
                          MVP5-4 (자기 설명 + 인출)
                               │
                          MVP5-5 (도그푸딩)
                               │
                          ──── MVP6 (LLM 활성화) ────
```

---

_본 문서는 코드 변경 없이 계획 수립만을 위한 문서입니다. MVP5 구현은 단계별 Claude Code 프롬프트(13절)를 사용합니다._
