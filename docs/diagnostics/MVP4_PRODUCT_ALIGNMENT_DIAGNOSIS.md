# MVP4 제품 정렬 진단 보고서

_작성일: 2026-05-06_
_대상: MVP4-R0 (대화형 한국어 컴파일러) + MVP4-K (프로덕션 경화) 이후 현 상태_
_목적: 원래 설계 문서(00\_vision ~ 09\_risks\_and\_guardrails)와 실제 구현 사이의 정렬도 진단_

---

## 목차

**Part I — 진단**
1. [진단 요약](#1-진단-요약)
2. [비전 대비 현 상태 비교](#2-비전-대비-현-상태-비교)
3. [세션 흐름 정렬 분석](#3-세션-흐름-정렬-분석)
4. [LLM 파이프라인 정렬 분석](#4-llm-파이프라인-정렬-분석)
5. [인지 부하 원칙 준수도](#5-인지-부하-원칙-준수도)
6. [한국어 UX 커버리지](#6-한국어-ux-커버리지)
7. [Source Grounding 준수도](#7-source-grounding-준수도)
8. [위험 가드레일 준수도](#8-위험-가드레일-준수도)
9. [화면 아키텍처 제안](#9-화면-아키텍처-제안)
10. [API 엔드포인트 제안](#10-api-엔드포인트-제안)

**Part II — 구현 계획**
11. [단계별 로드맵](#11-단계별-로드맵)
12. [엔지니어링 태스크 우선순위표](#12-엔지니어링-태스크-우선순위표)
13. [구현 준비 부록 (Implementation Readiness Addendum)](#13-구현-준비-부록)
14. [API 스키마 스케치](#14-api-스키마-스케치)
15. [LLM 정책](#15-llm-정책)
16. [다음 행동 권고](#16-다음-행동-권고)

---

## 1. 진단 요약

### 핵심 결론

현 구현은 **개발자 파이프라인 검증 도구**로서는 완성도가 높다. 그러나 원래 비전 문서가 정의한 **학습자 중심 통합 학습 루프**와는 심각하게 괴리되어 있다.

### 심각도 분류

| 심각도 | 정의 | 해당 갭 수 |
|--------|------|-----------|
| **S0** | 제품 존재 이유(core value proposition) 부재 — 이것 없이는 "공부 해체 분석기"가 아님 | 3 |
| **S1** | 학습 효과에 직접적 영향 — 연구 기반 설계 원칙 미구현 | 5 |
| **S2** | UX/접근성 장벽 — 대상 사용자가 사용할 수 없음 | 3 |
| **S3** | 완성도/편의성 — 있으면 좋지만 없어도 핵심 루프는 작동 | 2 |

### S0 갭 요약

| # | 갭 | 근거 |
|---|---|------|
| S0-1 | **통합 학습 세션이 존재하지 않음** | `05_user_session_flow.md`의 "New Concept Session" 8단계가 단일 사용자 흐름으로 구현되지 않음. 현재는 Sources → Bank Build → Review → Export → Recall로 5개 페이지를 개발자가 수동 탐색해야 함 |
| S0-2 | **5가지 표현이 정적 하드코딩** | `04_mvp_scope.md`의 "5 representations generated accurately" 성공 기준 미충족. `compiler_analyzer_service.py:65-137`의 `REPRESENTATION_PREVIEWS`는 소스 자료에서 생성된 것이 아니라 수동 작성된 고정 텍스트 |
| S0-3 | **대화형 진단 부재** | `05_user_session_flow.md` [2단계] "지금 알고 있는 것을 적어 주세요 / 어디서 막히나요?" 대화형 진단이 미구현. 현재는 키워드 매칭(`compiler_analyzer_service.py`)으로 갭을 추론할 뿐 |

---

## 2. 비전 대비 현 상태 비교

### 2.1 제품 정체성

| 항목 | 비전 (`00_vision.md`) | 현 상태 | 심각도 |
|------|----------------------|---------|--------|
| 정의 | "어려운 수학/과학 개념을 입력하면 소화 가능한 단위로 완전 분해하는 AI 학습 컴파일러" | 한국어 채팅에서 개념명을 키워드 매칭하고 하드코딩된 미리보기를 표시하는 규칙 기반 분석기 | **S0** |
| 핵심 가치 1 | "정의를 읽었는데 이해 안 됨" → 5가지 표현으로 재구성 | 5가지 표현은 `REPRESENTATION_PREVIEWS`에 하드코딩됨 — 소스 자료 기반 생성 아님 | **S0** |
| 핵심 가치 2 | "선행 지식이 뭔지 모르겠음" → 선행 그래프 자동 생성 | `knowledge/real_analysis.py`에 하드코딩된 `PREREQUISITE_EDGES`를 읽음 — LLM 생성 아님 (단, 비전도 MVP에서는 하드코딩 허용) | S3 |
| 핵심 가치 3 | "증명 구조가 안 보임" → proof schema 분해 | proof\_schema fixture만 존재. 대화형 walkthrough 없음 | **S1** |
| 핵심 가치 4 | "공부했는데 시험에서 틀림" → White Recall Loop | `/recall` 페이지에 구현됨. 단, 첫 사용 시 bank가 없어 사용 불가 | **S1** |
| 핵심 가치 5 | "오늘 뭘 공부했는지 기억 안 남" → STUDY.md 누적 기록 | 구현됨 (`study_md/writer.py`, `parser.py`, `validate.py`). STUDY.md 자동 업데이트 작동 | ✅ |

### 2.2 대상 사용자 접근성

| 항목 | 비전 | 현 상태 | 심각도 |
|------|------|---------|--------|
| 대상 | 학부 3-4학년, 실해석학 독학자 | 개발자 도구 4개 (Sources, BankBrowser, ConceptCompiler, SessionHistory)가 영어이고 학습자에게 노출됨 | **S2** |
| 진입 장벽 | 개념명 입력 → 바로 학습 시작 | 소스 업로드 → 뱅크 빌드 → 리뷰 → 익스포트 → 리콜의 5단계 수동 설정 필요 | **S0** |
| 언어 | 한국어 우선 | 랜딩(ChatCompiler)과 네비게이션은 한국어. 나머지 7개 페이지는 영어 | **S2** |

---

## 3. 세션 흐름 정렬 분석

### 3.1 New Concept Session (8단계) — `05_user_session_flow.md`

| 단계 | 비전 명세 | 현 구현 | 구현 위치 | 심각도 |
|------|----------|---------|-----------|--------|
| [1] 개념 입력 | 학습자가 "compactness 공부하고 싶어" 입력 | ✅ ChatCompiler에서 자유 텍스트 입력 | `ChatCompiler.tsx`, `POST /api/compiler/analyze` | ✅ |
| [2] 진단 | "지금 알고 있는 것 적어 주세요" + "어디서 막히나요?" → 초기 mastery 추정 | ❌ **미구현**. 한국어 단서어(`모르겠`, `헷갈`) 키워드 매칭만 수행. 학습자 응답을 받지 않음 | `compiler_analyzer_service.py:157-170` | **S0** |
| [3] 선행 그래프 | DAG 자동 생성 + 선행 mastery 확인 질문 + 미학습 선행 경고 | ⚠️ 부분 구현. 선행 목록은 표시하지만 mastery 확인 질문 없음. "선행부터 볼래요?" 선택지 없음 | `ChatCompiler.tsx` (inline 선행 목록) | **S1** |
| [4] 5가지 표현 + 자기 설명 | 각 표현 후 "이것을 자기 말로 설명해 보세요" 프롬프트 | ❌ **미구현**. 표현은 하드코딩 미리보기로만 표시. 자기 설명 프롬프트 없음. 대화형 상호작용 없음 | `REPRESENTATION_PREVIEWS` in `compiler_analyzer_service.py:65-137` | **S0** |
| [5] 오개념 체크 | MCQ 형식으로 제시 + 즉시 피드백 | ❌ **미구현**. `diagnosis.json`은 파이프라인에서 생성되지만 학습자에게 MCQ로 제시되지 않음 | `misconception_checker.py` (생성만), UI 없음 | **S1** |
| [6] White Recall Loop | "교재 덮고 처음부터 설명해 보세요" — 4가지 태스크 | ⚠️ 부분 구현. `/recall` 페이지에서 텍스트 입력 가능하지만, 첫 사용 시 bank 필요. 직접 진입 불가 | `RecallSession.tsx` | **S1** |
| [7] STUDY.md 업데이트 | 표현별 mastery 업데이트 + 오개념 기록 + next\_review 설정 | ✅ 구현됨 | `study_md/writer.py`, `apply_patch()` | ✅ |
| [8] 세션 요약 | "오늘 다룬 내용 / 다음 복습일 / 남은 선행" | ⚠️ 부분 구현. `SessionDetail` 페이지에서 아티팩트 조회 가능하지만 학습자 친화적 요약이 아님 | `SessionDetail.tsx` | S3 |

**구현율: 8단계 중 2단계 완전 구현, 3단계 부분 구현, 3단계 미구현 = 31% 완전 구현**

### 3.2 Review Session (4단계) — `05_user_session_flow.md`

| 단계 | 비전 명세 | 현 구현 | 심각도 |
|------|----------|---------|--------|
| [1] 복습 대상 로드 | STUDY.md에서 `next_review ≤ today` 개념 로드 | ✅ `GET /api/due`로 구현 | ✅ |
| [2] White Recall (무자료) | "지난번에 compactness 공부했습니다. 정의를 적어 보세요" | ⚠️ `/recall?concept=X` 경로 존재하지만 자동 진입 흐름 없음. Dashboard에서 수동 클릭 필요 | **S1** |
| [3] 응답 평가 | 성공 → mastery↑ / 부분 → 재학습 / 실패 → 전체 재분해 | ⚠️ mock grader만 작동. 실패 시 "전체 재분해" 로직 없음 | **S1** |
| [4] STUDY.md 업데이트 | mastery + next\_review 갱신 | ✅ `apply_patch()` | ✅ |

**구현율: 4단계 중 2단계 완전, 2단계 부분 = 50%**

### 3.3 Deep Dive Session (5단계) — `05_user_session_flow.md`

| 단계 | 비전 명세 | 현 구현 | 심각도 |
|------|----------|---------|--------|
| [1] 학습자 요청 | "compactness proof\_schema 자세히 보고 싶어" | ❌ 미구현. 특정 표현 딥다이브 진입점 없음 | **S1** |
| [2] 표현 + 스키마 로드 | mastery\_state 확인 | ❌ 미구현 | **S1** |
| [3] 스캐폴딩 | unknown→전체 / partial→빈칸 / solid→변형 | ❌ **미구현. 난이도 조절 로직 전무** | **S1** |
| [4] 자기 설명 + 피드백 | | ❌ 미구현 | **S1** |
| [5] STUDY.md 업데이트 | 해당 표현만 | ❌ 미구현 | **S1** |

**구현율: 0%**

---

## 4. LLM 파이프라인 정렬 분석

### 4.1 7단계 파이프라인 — `06_llm_orchestration.md`

| 단계 | 비전 명세 | 현 구현 | 구현 파일 | LLM 사용 | 심각도 |
|------|----------|---------|-----------|---------|--------|
| Stage 1: Concept Resolver | 자유 텍스트 → concept\_id 정규화 + 도메인 체크 | ✅ 구현됨 (사전 기반 정규화) | `concept_resolver.py`, `real_analysis.py:_ALIAS_MAP` | 불필요 (결정적) | ✅ |
| Stage 2: Prerequisite Graph | DAG 생성 + mastery 질의 | ✅ 하드코딩 DAG 사용 (MVP 범위 내 허용) | `real_analysis.py:PREREQUISITE_EDGES` | 불필요 (MVP) | ✅ |
| Stage 3: Representation Gen | 5가지 표현 생성 | ⚠️ MockLLMClient 전용. fixture 반환만 가능 | `representation_gen.py` (5회 LLM 호출) | Mock만 | **S0** |
| Stage 4: Misconception Checker | 오개념 MCQ 생성 | ⚠️ MockLLMClient 전용 + **학습자 MCQ UI 없음** | `misconception_checker.py` | Mock만 | **S1** |
| Stage 5: Self-Explanation Eval | 학습자 설명 평가 → accuracy\_score + missing\_elements | ❌ **템플릿만 존재**. `render_self_explanation_prompt()`은 프롬프트 텍스트만 생성. `evaluate_self_explanation()`은 학습자 응답이 없으면 호출 안 됨 | `self_explanation.py` | 미사용 | **S1** |
| Stage 6: Recall Orchestrator | 인출 태스크 생성 | ⚠️ MockLLMClient 전용 | `recall_orchestrator.py` | Mock만 | S2 |
| Stage 7: STUDY.md Writer | 세션 결과 → STUDY.md 패치 | ✅ 결정적 로직, LLM 불필요 | `study_md/writer.py` | 불필요 | ✅ |

### 4.2 LLM 활성화 상태

```python
# apps/api/services/concept_service.py
llm = MockLLMClient()  # 하드코딩 — 실제 LLM 호출 불가

# .env.example
GONGHAEBUN_LLM_DISABLED=1  # 기본값: LLM 비활성화
```

**현실**: LLM이 기본 비활성화 상태(`LLM_DISABLED=1`)이며, `concept_service.py`에서 `MockLLMClient()`가 하드코딩되어 있어 `.env`에서 활성화해도 컴파일 경로에서는 실제 LLM을 사용할 수 없다. 실제 LLM 호출은 **그레이딩 경로**(POST /api/sessions에서 `grader="llm"`)에서만 가능하다.

**심각도**: **S0** — 소스 자료 기반 5가지 표현 생성이 제품의 핵심 가치인데, 현재 실제 LLM 생성 경로가 프로덕션에서 작동하지 않는다.

---

## 5. 인지 부하 원칙 준수도

`03_product_principles.md`의 8가지 설계 원칙 대비:

| 원칙 | 우선순위 | 비전 요구 | 현 구현 | 심각도 |
|------|---------|----------|---------|--------|
| P1: Multiple Representations First | 1위 | 모든 개념에 정확히 5가지 표현 + 표현 간 번역 과제 | 하드코딩 미리보기만 존재. 번역 과제 없음 | **S0** |
| P2: Cognitive Load Control | 2위 | 격리 요소 먼저 → 통합 뷰 / 분할 주의 방지 / worked schema | 학습자가 5개 페이지를 수동 탐색 — 분할 주의 극대화 | **S1** |
| P3: Explicit Prerequisite Graph | 3위 | DAG 자동 생성 + mastery 확인 + unknown 선행 경고 | 선행 목록은 표시되나 mastery 확인 질문 / 선택지 없음 | S2 |
| P4: Scaffolding with Fading | 4위 | unknown→전체 / partial→요청 시 / solid→빈 프레임 | **전혀 미구현**. 모든 질문이 동일 난이도 | **S1** |
| P5: Self-Explanation Prompting | 5위 | 각 표현 후 "자기 말로 설명" + LLM 평가 | 템플릿만 존재. 대화형 프롬프트 없음. 학습자 응답 수집 없음 | **S1** |
| P6: Retrieval Practice + Spaced Repetition | 6위 | 매 세션 종료 시 White Recall 필수 + 간격 반복 스케줄 | Recall 페이지 존재하나 세션 내 필수 단계가 아님. 간격 반복은 STUDY.md에 기록됨 | **S1** |
| P7: Representation-Specific Mastery | 7위 | 표현별 독립 mastery + overall = 최약 링크 | ✅ 구현됨 (`parser.py`, `writer.py`) | ✅ |
| P8: STUDY.md as Single Source of Truth | 8위 | 모든 진행, 오개념, 복습 일정을 하나의 Markdown 파일에 | ✅ 구현됨 + 검증(`validate.py`) + 자동 복구 | ✅ |

**준수율: 8원칙 중 2개 완전 준수, 1개 부분 준수, 5개 미준수 = 25% 완전 준수**

---

## 6. 한국어 UX 커버리지

### 6.1 페이지별 언어 분석

| 페이지 | 경로 | UI 언어 | 대상 사용자 | 문제 |
|--------|------|---------|------------|------|
| ChatCompiler | `/` | 🇰🇷 한국어 | 학습자 | ✅ |
| Layout (네비게이션) | 전체 | 🇰🇷 한국어 (기본) + 영어 (개발자 토글) | 학습자 | ✅ |
| Dashboard | `/dashboard` | 🇬🇧 영어 | 학습자 | **S2** — "API Status", "Review Due", "Mastery", "Weak Representations" 모두 영어 |
| RecallSession | `/recall` | 혼합 | 학습자 | **S2** — 제목/레이블 영어 ("Recall Session", "Submit"), 빈 상태만 한국어 |
| SourceUpload | `/sources` | 🇬🇧 영어 | 개발자 | S3 — 개발자 도구 토글 뒤에 숨겨져 있어 학습자 영향 제한적 |
| BankReview | `/review/:id` | 🇬🇧 영어 | 개발자 | S3 — 개발자 도구 |
| ConceptCompiler | `/concepts` | 🇬🇧 영어 | 개발자 | S3 — 개발자 도구 |
| SessionHistory | `/sessions` | 🇬🇧 영어 | 개발자 | S3 — 개발자 도구 |
| SessionDetail | `/sessions/:id` | 🇬🇧 영어 | 개발자 | S3 — 개발자 도구 |

### 6.2 학습자 대면 페이지 한국어화 현황

학습자가 직접 사용하는 3개 페이지 중:

- **ChatCompiler**: ✅ 완전 한국어
- **Dashboard**: ❌ 완전 영어 — 학습자가 "무엇을 복습해야 하는지" 확인하는 핵심 페이지인데 영어
- **RecallSession**: ❌ 혼합 — 핵심 학습 활동 페이지인데 주요 UI 요소가 영어

**심각도: S2** — 대상 사용자(학부 3-4학년 한국어 사용자)가 핵심 학습 흐름에서 영어 장벽에 부딪힘

---

## 7. Source Grounding 준수도

### 7.1 비전 요구 (`00_vision.md`, `06_llm_orchestration.md`)

> "모든 출력은 교재 자료에 근거해야 한다" (source grounding)
> "Based on Rudin Principles of Mathematical Analysis Ch.2" — 출력마다 출처 표기

### 7.2 현 상태

| 항목 | 요구 | 현 상태 | 심각도 |
|------|------|---------|--------|
| 표현 생성 소스 추적 | 생성된 표현마다 원본 소스 참조 | `representation_gen.py`에서 grounding footer 추가됨 (소스 해시 + 면책 조항) | ✅ |
| 질문 은행 소스 추적 | 각 질문에 Evidence(sha256, source pointer) | ✅ `recall_orchestrator.py:convert_tasks_to_questions()` | ✅ |
| ChatCompiler 표현 | 소스에서 생성된 표현 | ❌ `REPRESENTATION_PREVIEWS`는 하드코딩 — 소스 추적 불가 | **S0** |
| 오개념 체크 근거 | 반례마다 교재 참조 | `diagnosis.json`에 반례 포함되나 교재 페이지 참조 없음 | S2 |

### 7.3 핵심 문제

ChatCompiler가 학습자의 첫 접점인데, 여기서 보여주는 5가지 표현 미리보기(`REPRESENTATION_PREVIEWS`)는 **소스 자료와 무관한 하드코딩 텍스트**다. 원래 비전의 핵심인 "소스 기반 생성"이 학습자 대면 경로에서 완전히 빠져 있다.

---

## 8. 위험 가드레일 준수도

`09_risks_and_guardrails.md`의 7가지 위험 대비:

| 위험 | 심각도 | 비전 가드레일 | 현 구현 | 준수 |
|------|--------|-------------|---------|------|
| **R1: 수학적 환각** | HIGH | 시스템 프롬프트에 불확실성 표현 강제 + 전문가 리뷰 + 교재 참조 + 경고 배너 | MockLLM만 사용하여 환각 위험 자체가 없음. 단, LLM 활성화 시 가드레일 미구현 | ⚠️ 현재 안전하나 LLM 활성화 시 위험 |
| **R2: 과잉 의존** | HIGH | White Recall 필수 + "답 보기" 지연 + LLM은 질문으로 응답 | White Recall이 세션 내 필수 단계가 아님. "답 보기" 지연 없음 | ❌ |
| **R3: 범위 확장 요청** | MEDIUM | Stage 1 필터 + 숙제 대행 방지 | `concept_resolver.py`에서 미인식 개념 거부. 숙제 대행 방지 메시지 없음 | ⚠️ |
| **R4: 선행 무한 회귀** | MEDIUM | 깊이 3 제한 + 최소 선행 명시 + 학습자 선택 | 하드코딩 DAG이므로 무한 회귀 불가. 학습자 선택("선행부터 vs 계속") 미구현 | ⚠️ |
| **R5: 오개념 강화** | HIGH | "판단해 보세요" 형식 + 즉시 교정 + 전문가 리뷰 | `diagnosis.json` 생성되지만 학습자에게 MCQ로 제시되지 않아 강화 위험 자체가 없음. 동시에 교정 기회도 없음 | ⚠️ 안전하나 효과 없음 |
| **R6: STUDY.md 손상** | MEDIUM | 쓰기 전 백업 + append-only + 파싱 검증 | ✅ `.bak` 백업 + `validate_study_md()` + `apply_patch()` 후 재검증 | ✅ |
| **R7: API 비용 폭발** | LOW | 세션당 토큰 한도 + 캐싱 | MockLLM만 사용하여 비용 없음 | ✅ (해당 없음) |

**요약**: LLM이 비활성화된 덕분에 R1/R5/R7은 현재 안전하지만, 이는 **가드레일이 작동해서가 아니라 위험 자체를 회피한 것**이다. LLM을 활성화하면 가드레일 대부분이 미구현 상태로 노출된다.

---

## 9. 화면 아키텍처 제안

### 9.1 현재 구조 vs 제안 구조

**현재 (9개 라우트, 개발자/학습자 혼재)**:

```
/                    ChatCompiler        [학습자, 한국어]
/dashboard           Dashboard           [학습자, 영어]
/recall              RecallSession       [학습자, 혼합]
/sources             SourceUpload        [개발자, 영어]
/bank                BankBrowser         [개발자, 영어]  ← 현재 존재하지 않음 (Layout에만 링크)
/review/:conceptId   BankReview          [개발자, 영어]
/concepts            ConceptCompiler     [개발자, 영어]
/sessions            SessionHistory      [개발자, 영어]
/sessions/:sessionId SessionDetail       [개발자, 영어]
```

**제안 (학습자 루프 우선)**:

```
학습자 흐름 (한국어):
/                    LearnerHome         새로운 랜딩 — "무엇을 공부할까요?" + 복습 알림
/study/:conceptId    StudySession        통합 학습 세션 (8단계를 하나의 페이지에서)
/review              ReviewSession       복습 세션 (STUDY.md due 기반)
/progress            ProgressDashboard   학습 현황 (한국어 대시보드)

개발자 흐름 (기존 유지, 토글 뒤):
/dev/sources         SourceUpload
/dev/bank            BankBrowser
/dev/review/:id      BankReview
/dev/compiler        ConceptCompiler
/dev/sessions        SessionHistory
/dev/sessions/:id    SessionDetail
```

### 9.2 통합 학습 세션 (`/study/:conceptId`) 화면 설계

```
┌─────────────────────────────────────────────┐
│  공부 해체 분석기 — compactness (옹골성)      │
│                                              │
│  ┌─ 진행 표시 ─────────────────────────────┐ │
│  │ [1 진단] → [2 선행] → [3 표현] →        │ │
│  │ [4 오개념] → [5 인출] → [6 정리]        │ │
│  └──────────────────────────────────────────┘ │
│                                              │
│  ── 1단계: 진단 ──────────────────────────── │
│  이 개념에 대해 알고 있는 것을 적어 주세요:   │
│  ┌──────────────────────────────────────────┐ │
│  │ (학습자 자유 텍스트 입력)                  │ │
│  └──────────────────────────────────────────┘ │
│  어디서 막히거나 헷갈리나요?                   │
│  ┌──────────────────────────────────────────┐ │
│  │ (학습자 갭 서술)                           │ │
│  └──────────────────────────────────────────┘ │
│                               [다음 단계 →]  │
│                                              │
│  ── 2단계: 선행 지식 확인 ────────────────── │
│  compactness를 공부하려면 다음 개념이 필요:   │
│  ☑ metric space — 편하게 설명할 수 있나요?    │
│  ☐ open set — 편하게 설명할 수 있나요?        │
│  ☐ open cover — 편하게 설명할 수 있나요?      │
│  ⚠️ open cover mastery = unknown              │
│  → 선행부터 학습 | 그래도 계속               │
│                                              │
│  ── 3단계: 5가지 표현 ───────────────────── │
│  [1/5] 정의 (formal)                        │
│  ┌──────────────────────────────────────────┐ │
│  │ (LLM 생성 formal definition)              │ │
│  └──────────────────────────────────────────┘ │
│  💬 이 정의를 자기 말로 설명해 보세요:        │
│  ┌──────────────────────────────────────────┐ │
│  │ (학습자 자기 설명 입력)                    │ │
│  └──────────────────────────────────────────┘ │
│  🤖 평가: ✓ 정확합니다. 누락: "유한 부분덮개" │
│                          [다음 표현 →]        │
│  ...                                         │
│                                              │
│  ── 4단계: 오개념 체크 ──────────────────── │
│  Q1: "모든 콤팩트 집합은 유계이다" — 참/거짓?  │
│  ○ 참  ● 거짓                                │
│  ✅ 정답! 반례: 이산 위상에서...               │
│                                              │
│  ── 5단계: White Recall ─────────────────── │
│  이제 교재를 덮고, compactness를 처음부터     │
│  설명해 보세요.                              │
│  ┌──────────────────────────────────────────┐ │
│  │ (학습자 무자료 인출)                       │ │
│  └──────────────────────────────────────────┘ │
│                               [제출 →]       │
│                                              │
│  ── 6단계: 세션 정리 ───────────────────── │
│  오늘 다룬 내용: compactness (5가지 표현)     │
│  mastery 변화: formal solid → intuitive       │
│  partial                                     │
│  다음 복습일: 2026-05-07                     │
│  남은 선행: open_cover (unknown)              │
└─────────────────────────────────────────────┘
```

### 9.3 핵심 차이

| 현재 | 제안 |
|------|------|
| 5개 페이지 수동 탐색 | 1개 페이지에서 6단계 자동 진행 |
| 개발자 bank 빌드/리뷰 필수 | 학습자 진입 시 자동 컴파일 |
| 하드코딩 표현 미리보기 | LLM 실시간 생성 |
| 자기 설명 없음 | 매 표현 후 자기 설명 + LLM 평가 |
| 오개념 MCQ 없음 | 대화형 MCQ + 즉시 피드백 |
| White Recall 선택적 | White Recall 필수 (건너뛸 수 없음) |

---

## 10. API 엔드포인트 제안

### 10.1 신규 필요 엔드포인트

| 엔드포인트 | 메서드 | 목적 | 우선순위 |
|-----------|--------|------|---------|
| `/api/study-session` | `POST` | 통합 학습 세션 시작 — concept\_id로 자동 컴파일 + 세션 생성 | **P0** |
| `/api/study-session/{id}/diagnose` | `POST` | 진단 단계 — 학습자 사전 지식 + 갭 서술 수신 → LLM 평가 | **P0** |
| `/api/study-session/{id}/self-explain` | `POST` | 자기 설명 제출 — representation\_type + 학습자 설명 → LLM 평가 (Stage 5) | **P0** |
| `/api/study-session/{id}/misconception-check` | `POST` | 오개념 MCQ 응답 제출 — 즉시 피드백 반환 | **P1** |
| `/api/study-session/{id}/recall` | `POST` | White Recall 응답 제출 — 기존 POST /api/sessions 로직 재사용 | **P1** |
| `/api/study-session/{id}/complete` | `POST` | 세션 완료 — STUDY.md 패치 적용 + 요약 반환 | **P1** |
| `/api/representations/{concept_id}/generate` | `POST` | 실시간 LLM 표현 생성 (source\_path 필수) — Stage 3 단독 호출 | **P0** |

### 10.2 기존 엔드포인트 수정

| 엔드포인트 | 현 상태 | 변경 사항 |
|-----------|---------|----------|
| `POST /api/compiler/analyze` | 규칙 기반 분석 | → 통합 세션 시작 트리거로 전환하거나, `/api/study-session` POST로 리다이렉트 |
| `POST /api/concepts/{id}/compile` | MockLLMClient 하드코딩 | → LLM\_DISABLED 설정에 따라 실제 LLM 사용 가능하도록 |
| `POST /api/sessions` | `grader: 'mock'` 하드코딩 (프론트엔드) | → 프론트엔드에서 `grader` 선택 가능하도록 |

---

## 11. 단계별 로드맵

> **이름 충돌 방지**: MVP4-L은 Oracle 배포 리허설에 이미 사용됨. 한국어화는 MVP4-KO 또는 MVP4-R0.1로 명명.

---

### MVP4-R0.1: 즉시 UX 보정

| 항목 | 내용 |
|------|------|
| **목표** | 학습자 대면 페이지에서 영어 UI 문자열 제거, 빈 상태 안내 개선 |
| **사용자 스토리** | "한국어 사용자로서, 핵심 학습 페이지를 모국어로 사용하고 싶다" |

**범위**:
- Dashboard 전체 한국어화: "Review Due" → "복습 예정", "Weak Representations" → "취약 표현", "Recent Sessions" → "최근 세션" 등 약 40개 문자열
- RecallSession 전체 한국어화: "Recall Session" → "인출 연습", "Submit" → "제출", "Mastery Changes" → "숙련도 변화" 등 약 30개 문자열
- Recall 빈 상태: accepted bank 없을 때 "컴파일러에서 문제를 먼저 생성하세요" 안내
- Layout 브랜드명 "공부해체분석기" 일관성 확인

**비범위**: 개발자 도구 한국어화, 새 페이지 생성, API 변경, i18n 라이브러리 도입

**관련 파일**: `Dashboard.tsx`, `RecallSession.tsx`, `Layout.tsx`
**백엔드 엔드포인트**: 없음
**프론트엔드 화면**: Dashboard, RecallSession
**데이터 아티팩트**: 없음

**테스트 계획**: 기존 Playwright smoke 통과. 한국어 문자열 grep으로 영어 잔여 확인.
**수동 검증**: (1) Dashboard 모든 텍스트 한국어 확인 (2) RecallSession 빈 상태 안내 확인 (3) bank 없는 개념 선택 시 한국어 안내
**완료 기준**: 학습자 대면 3개 페이지(`/`, `/dashboard`, `/recall`)에서 영어 UI 문자열 0개
**롤백**: `git revert` — UI 문자열만 변경이므로 위험 없음

---

### MVP4-R1a: Study Session Shell

| 항목 | 내용 |
|------|------|
| **목표** | `/study/:conceptId` 라우트에 6단계 한국어 스텝퍼 UI 배치. LLM 생성 없이 기존 아티팩트로 동작 |
| **사용자 스토리** | "학습자로서, 개념을 선택하면 하나의 화면에서 학습 단계를 따라가고 싶다" |

**범위**:
- 신규 `StudySession.tsx` 페이지: 6단계 스텝퍼 (진단 → 선행 → 표현 → 오개념 → 인출 → 정리)
- 각 단계 placeholder 한국어 UI (실제 데이터 연결은 R1b)
- `/study/:conceptId` 라우트 등록 (`App.tsx`)
- ChatCompiler "공부 시작" → `/study/:conceptId` 연결 (`ChatCompiler.tsx`)
- 세션 상태: React state로 관리 (step index, 각 단계 완료 여부)

**비범위**: 백엔드 API 신설 없음. LLM 호출 없음. 실제 데이터 바인딩 없음 (R1b에서).

**관련 파일**: 신규 `apps/web/src/pages/StudySession.tsx`, 수정 `App.tsx`, `ChatCompiler.tsx`, `Layout.tsx`
**백엔드 엔드포인트**: 없음
**프론트엔드 화면**: StudySession (신규), ChatCompiler (수정)
**데이터 아티팩트**: 없음

**테스트 계획**: 컴포넌트 렌더 테스트 (6단계 표시, 단계 전환). Playwright: `/study/compactness` 진입 → 스텝퍼 표시.
**수동 검증**: (1) ChatCompiler에서 개념 인식 → "공부 시작" 클릭 → `/study/compactness` 이동 (2) 6단계 UI 표시 (3) 단계 간 이동 가능 (4) 전체 한국어
**완료 기준**: `/study/compactness` 접근 시 6단계 한국어 스텝퍼가 렌더링되고 단계 간 전환 가능
**롤백**: 신규 파일 삭제 + 라우트 제거

---

### MVP4-R1b: Study Session Backend

| 항목 | 내용 |
|------|------|
| **목표** | 통합 학습 세션의 백엔드 API — 세션 생성, 단계별 진행, 아티팩트 조회 |
| **사용자 스토리** | "학습자로서, 개념 선택 시 시스템이 자동으로 세션을 준비해 주길 원한다" |

**범위**:
- `POST /api/study-session` — concept\_id로 세션 생성. 기존 `run_new_concept_session()` 호출 (MockLLMClient). 세션 ID 반환
- `GET /api/study-session/{id}` — 세션 상태 + 현재 단계 + 아티팩트 경로 반환
- `POST /api/study-session/{id}/diagnose` — 학습자 진단 텍스트 수신 + 저장 (R1b에서는 결정적 평가만, LLM 평가는 R2)
- 세션 JSON 영속화: 기존 `runs/{session_id}/` 디렉토리 재사용
- 신규 라우터: `apps/api/routers/study_session.py`
- 신규 서비스: `apps/api/services/study_session_service.py`

**비범위**: LLM 실시간 생성 없음 (MockLLMClient 유지). 자기 설명 평가 API는 R1d. 프론트엔드 바인딩은 R1c.

**관련 파일**: 신규 `routers/study_session.py`, `services/study_session_service.py`, `schemas/api_schemas.py` (신규 스키마). 수정 `main.py` (라우터 등록)
**백엔드 엔드포인트**: `POST /api/study-session`, `GET /api/study-session/{id}`, `POST /api/study-session/{id}/diagnose`
**프론트엔드 화면**: 없음 (백엔드 전용)
**데이터 아티팩트**: `runs/{session_id}/study_session_state.json` (단계 진행 상태)

**테스트 계획**: pytest — 세션 생성/조회/진단 CRUD. 422: 미인식 개념. 404: 존재하지 않는 세션.
**수동 검증**: (1) `curl POST /api/study-session` → session\_id 반환 (2) `curl GET /api/study-session/{id}` → 상태 확인 (3) `runs/` 디렉토리에 아티팩트 생성 확인
**완료 기준**: 3개 엔드포인트 동작 + 기존 테스트 회귀 없음
**롤백**: 신규 파일 삭제 + 라우터 등록 제거

---

### MVP4-R1c: 기존 파이프라인 통합

| 항목 | 내용 |
|------|------|
| **목표** | StudySession 프론트엔드를 R1b 백엔드에 연결. 학습자 경로에서 수동 bank 빌드/리뷰 제거 |
| **사용자 스토리** | "학습자로서, 소스 업로드나 bank 리뷰 없이 바로 학습을 시작하고 싶다" |

**범위**:
- StudySession.tsx에서 `POST /api/study-session` 호출 → 세션 생성 → 아티팩트 로드
- 표현 단계: `representation_set.json`에서 5가지 표현 읽어 표시
- 선행 단계: `prerequisite_graph.json`에서 선행 목록 표시 + mastery 체크박스
- 오개념 단계: `diagnosis.json`에서 오개념 목록 읽기 (MCQ UI는 R3)
- 인출 단계: `recall_tasks.json` 또는 `questions.generated.json`에서 질문 로드 → 기존 `POST /api/sessions` 재사용
- 자동 bank 준비: `study_session_service.py`에서 컴파일 후 자동으로 `questions.generated.json` → `questions.accepted.json` 복사 (학습자 경로에서는 수동 리뷰 건너뜀)
- bank 리뷰는 개발자 도구 경로(`/review/:id`)에 유지

**비범위**: LLM 실시간 생성 없음. 자기 설명 수집/평가 없음 (R1d). 오개념 MCQ 상호작용 없음 (R3).

**관련 파일**: 수정 `StudySession.tsx`, `study_session_service.py`. 신규 `apps/web/src/api/client.ts` (study-session API 함수 추가)
**백엔드 엔드포인트**: 기존 API 재사용. `study_session_service.py` 내부에서 bank 자동 준비 로직 추가.
**프론트엔드 화면**: StudySession (데이터 바인딩)
**데이터 아티팩트**: 기존 `runs/` + `banks/` 아티팩트 재사용

**테스트 계획**: E2E Playwright — `/study/compactness` 진입 → 세션 생성 → 표현 표시 → 인출 제출 → STUDY.md 업데이트.
**수동 검증**: (1) ChatCompiler → "공부 시작" → 세션 자동 생성 (2) 표현 5개 표시 (3) 선행 목록 표시 (4) 인출 제출 → mastery 변화 표시 (5) 수동 bank 리뷰 없이 전체 흐름 완료
**완료 기준**: 학습자가 개념 입력부터 인출 완료까지 1개 페이지에서 완료 가능. STUDY.md 업데이트 확인.
**롤백**: StudySession.tsx의 API 바인딩 제거 → R1a의 placeholder UI로 복귀

---

### MVP4-R1d: 자기 설명 + White Recall 통합

| 항목 | 내용 |
|------|------|
| **목표** | 각 표현 후 자기 설명 수집 + 결정적 평가. White Recall을 세션 완료 필수 단계로 |
| **사용자 스토리** | "학습자로서, 각 표현을 읽은 뒤 자기 말로 설명하고 피드백을 받고 싶다" |

**범위**:
- 표현 단계: 각 표현 후 자기 설명 textarea + "제출" 버튼
- `POST /api/study-session/{id}/self-explain` — representation\_type + learner\_response 수신
- 결정적 평가: 키워드 매칭 기반 (R2에서 LLM 평가로 전환). `evaluate_self_explanation()` 호출하되 MockLLMClient 사용
- White Recall 필수화: 5단계(인출) 완료 전에는 6단계(정리) 진입 불가
- `POST /api/study-session/{id}/recall` — 기존 `POST /api/sessions` 로직 위임
- `POST /api/study-session/{id}/complete` — STUDY.md 패치 적용 + 세션 요약 반환
- 세션 요약: 한국어 ("오늘 다룬 내용", "mastery 변화", "다음 복습일")

**비범위**: LLM 실시간 자기 설명 평가 (R2). 오개념 MCQ (R3). 스캐폴딩 (R3).

**관련 파일**: 수정 `StudySession.tsx` (자기 설명 UI + 인출 필수화), `study_session_service.py` (self-explain/recall/complete 로직). 신규 엔드포인트 3개. 수정 `self_explanation.py` (MockLLM 경로 활성화)
**백엔드 엔드포인트**: `POST .../self-explain`, `POST .../recall`, `POST .../complete`
**프론트엔드 화면**: StudySession (자기 설명 UI + 인출 필수 + 세션 정리)
**데이터 아티팩트**: `runs/{session_id}/self_explanations.json`, `runs/{session_id}/recall_attempts.json`

**테스트 계획**: pytest — 자기 설명 제출 → 평가 반환. 인출 미완료 시 complete 거부. complete 후 STUDY.md 패치. E2E — 전체 6단계 완주.
**수동 검증**: (1) 표현 읽기 → 자기 설명 입력 → 피드백 표시 (2) 5단계 건너뛰기 시도 → 차단됨 (3) 인출 완료 → 세션 정리 → STUDY.md 업데이트 (4) 세션 요약 한국어
**완료 기준**: 비전 `05_user_session_flow.md`의 New Concept Session 8단계 중 6단계(진단/선행/표현+자기설명/인출/STUDY.md/요약) 작동. 오개념 MCQ만 placeholder.
**롤백**: self-explain/recall/complete 엔드포인트 제거 → R1c 상태로 복귀

---

### MVP4-R2: 소스 기반 LLM 생성

| 항목 | 내용 |
|------|------|
| **목표** | 하드코딩 표현 제거. 실제 LLM으로 소스 기반 5가지 표현 생성. 환각 가드레일 포함 |
| **사용자 스토리** | "학습자로서, 교재 내용에 근거한 표현을 보고 싶다 — 하드코딩이 아닌 실제 생성" |

**범위**:
- `concept_service.py`에서 `MockLLMClient()` → `config.LLM_DISABLED` 기반 분기 (`make_llm_client()`)
- `REPRESENTATION_PREVIEWS` 제거 또는 fallback으로 격하 (LLM 실패 시에만 사용)
- 시스템 프롬프트에 불확실성 표현 강제: "확실하지 않으면 '교재에서 확인하세요'라고 표시"
- 경고 배너: LLM 생성 표현에 "이 내용은 AI가 생성했습니다. 교재에서 검증하세요" 표시
- JSON 스키마 검증 + 재시도 (1회): `representation_gen.py`에서 출력 파싱 실패 시 1회 재시도
- 타임아웃: LLM 호출 30초 한도 (`llm/config.py`에 설정)
- 비용 제한: 세션당 30,000 토큰 상한 카운터
- 자기 설명 LLM 평가 활성화: `evaluate_self_explanation()`에서 실제 LLM 호출
- OPENAI\_API\_KEY는 `.env` 전용 — 코드에 하드코딩 절대 금지

**비범위**: 오개념 MCQ UI (R3). 스캐폴딩 (R3). 진단 LLM 평가 (R3에서 추가 검토).

**관련 파일**: 수정 `concept_service.py`, `representation_gen.py`, `self_explanation.py`, `llm/config.py`. 신규 `llm/client_factory.py` (또는 기존 `grading/factory.py` 확장)
**백엔드 엔드포인트**: 기존 `POST /api/study-session` 내부 동작 변경
**프론트엔드 화면**: StudySession (경고 배너 추가)
**데이터 아티팩트**: `runs/{session_id}/representation_set.json` (LLM 생성)

**테스트 계획**: 단위 — JSON 파싱 실패 → 재시도 → fallback. 통합 — LLM\_DISABLED=0 + API key로 실제 생성 확인 (CI에서는 mock). 비용 — 토큰 카운터 한도 초과 시 중단.
**수동 검증**: (1) LLM\_DISABLED=0 + API key → `/study/compactness` → LLM 생성 표현 표시 (2) 경고 배너 표시 (3) LLM 실패 시 fallback (4) 소스 해시 grounding footer 표시
**완료 기준**: LLM\_DISABLED=0일 때 소스 기반 5가지 표현이 실시간 생성되고 경고 배너 포함. LLM\_DISABLED=1일 때 기존 mock 동작 유지.
**롤백**: `config.LLM_DISABLED=1`로 즉시 mock 복귀

---

### MVP4-R3: 오개념 MCQ + 스캐폴딩

| 항목 | 내용 |
|------|------|
| **목표** | 오개념 MCQ 대화형 제시 + mastery 기반 난이도 조절 + Deep Dive 세션 |
| **사용자 스토리** | "학습자로서, 내 오개념을 발견하고 교정받고 싶고, 수준에 맞는 문제를 풀고 싶다" |

**범위**:
- 오개념 MCQ UI: `diagnosis.json`의 misconceptions를 참/거짓 MCQ로 제시 → 즉시 피드백 (반례 + 설명)
- `POST /api/study-session/{id}/misconception-check` — MCQ 응답 제출 → 결과 저장
- 스캐폴딩: mastery=unknown → 전체 schema + 힌트, partial → 빈칸 채우기, solid → 변형 문제
- 답 보기 지연: 자기 설명 미제출 시 다음 표현 잠금 (프론트엔드 상태)
- Deep Dive 진입점: Dashboard "특정 표현 강화" → `/study/:conceptId?focus=proof_schema`
- 진단 LLM 평가 (선택): 학습자 사전 지식 텍스트 → 초기 mastery 추정

**비범위**: 새 도메인 추가. 사용자 인증. 지식 추적(BKT).

**관련 파일**: 수정 `StudySession.tsx` (MCQ + 스캐폴딩 + 잠금), `study_session_service.py` (MCQ 로직). 수정 `recall_orchestrator.py` (mastery 기반 태스크 분기)
**백엔드 엔드포인트**: `POST .../misconception-check`
**프론트엔드 화면**: StudySession (MCQ 단계 + 스캐폴딩 UI)
**데이터 아티팩트**: `runs/{session_id}/misconception_responses.json`

**테스트 계획**: pytest — MCQ 정답/오답 시 피드백 검증. 스캐폴딩 분기 (mastery별 다른 질문 세트). E2E — 전체 8단계 완주.
**수동 검증**: (1) 오개념 MCQ 표시 → 정답/오답 피드백 (2) 자기 설명 미제출 시 다음 표현 잠금 (3) mastery=unknown vs solid에서 다른 난이도
**완료 기준**: 비전 8단계 전체 구현 완료. 오개념 MCQ + 스캐폴딩 + Deep Dive 작동.
**롤백**: MCQ 단계 → placeholder 복귀, 스캐폴딩 → 동일 난이도 복귀

---

### MVP4-M: 프로덕션 경화 (제품 적합성 수리 후에만)

| 항목 | 내용 |
|------|------|
| **목표** | 제품 적합성이 확인된 후에만 인프라 경화. 시기상조 배포 방지 |
| **사용자 스토리** | "운영자로서, 안정적으로 외부에 서비스하고 싶다" |

**범위**:
- systemd 서비스 파일
- nginx reverse proxy + HTTPS (Let's Encrypt)
- 도메인 설정
- 환경별 .env 분리 (dev/staging/prod)
- 로그 수집 + 모니터링
- 토큰 사용량 모니터링 대시보드

**비범위**: 사용자 인증 (v2). 다중 도메인 (v2). 부하 분산 (단일 서버).

**관련 파일**: `scripts/`, `docs/deployment/`, `.env.example`, 신규 systemd/nginx 설정
**백엔드 엔드포인트**: `GET /api/ready` 확장 (상세 health check)
**프론트엔드 화면**: 없음
**데이터 아티팩트**: 없음

**테스트 계획**: `scripts/smoke_local.py` 통과. HTTPS 인증서 검증.
**수동 검증**: (1) 외부 접근 가능 (2) HTTPS 동작 (3) API health check (4) 서버 재시작 후 자동 복구
**완료 기준**: 외부 HTTPS 접근 + 자동 재시작 + 모니터링
**롤백**: nginx 설정 제거 → 로컬 개발 모드 복귀

---

## 12. 엔지니어링 태스크 우선순위표

| 순위 | 태스크 | 심각도 | 마일스톤 | 관련 파일 | 의존성 |
|------|--------|--------|---------|-----------|--------|
| 1 | Dashboard 한국어화 (~40개 문자열) | S2 | R0.1 | `Dashboard.tsx` | — |
| 2 | RecallSession 한국어화 (~30개 문자열) | S2 | R0.1 | `RecallSession.tsx` | — |
| 3 | Recall 빈 상태 한국어 안내 개선 | S2 | R0.1 | `RecallSession.tsx` | — |
| 4 | StudySession.tsx 스텝퍼 UI 생성 | S0 | R1a | 신규 `StudySession.tsx` | — |
| 5 | `/study/:conceptId` 라우트 등록 | S0 | R1a | `App.tsx`, `Layout.tsx` | #4 |
| 6 | ChatCompiler "공부 시작" → `/study` 연결 | S0 | R1a | `ChatCompiler.tsx` | #4 |
| 7 | `POST /api/study-session` 구현 | S0 | R1b | 신규 `routers/study_session.py`, `services/study_session_service.py` | — |
| 8 | `GET /api/study-session/{id}` 구현 | S0 | R1b | 상동 | #7 |
| 9 | `POST .../diagnose` 구현 (결정적) | S0 | R1b | 상동 | #7 |
| 10 | StudySession → 백엔드 연결 (아티팩트 로드) | S0 | R1c | `StudySession.tsx`, `client.ts` | #7, #4 |
| 11 | 자동 bank 준비 (수동 리뷰 제거) | S0 | R1c | `study_session_service.py` | #7 |
| 12 | 자기 설명 UI + `POST .../self-explain` | S0 | R1d | `StudySession.tsx`, 신규 엔드포인트 | #10 |
| 13 | White Recall 필수화 + `POST .../recall` | S1 | R1d | `StudySession.tsx`, 신규 엔드포인트 | #10 |
| 14 | `POST .../complete` + 세션 요약 | S1 | R1d | 신규 엔드포인트 | #12, #13 |
| 15 | LLM 클라이언트 설정 기반 전환 | S0 | R2 | `concept_service.py`, `llm/config.py` | — |
| 16 | `REPRESENTATION_PREVIEWS` 제거/fallback | S0 | R2 | `compiler_analyzer_service.py` | #15 |
| 17 | 환각 가드레일 (시스템 프롬프트 + 경고 배너) | S1 | R2 | 파이프라인 프롬프트들, `StudySession.tsx` | #15 |
| 18 | JSON 스키마 검증 + 재시도 + 타임아웃 | S1 | R2 | `representation_gen.py`, `llm/config.py` | #15 |
| 19 | 토큰 한도 카운터 | S3 | R2 | 신규 미들웨어 | #15 |
| 20 | 오개념 MCQ UI + API | S1 | R3 | `StudySession.tsx`, 신규 엔드포인트 | #10 |
| 21 | 스캐폴딩 난이도 분기 | S1 | R3 | `recall_orchestrator.py`, `StudySession.tsx` | #15 |
| 22 | 답 보기 지연 (자기 설명 잠금) | S1 | R3 | `StudySession.tsx` | #12 |

---

## 부록 A: 근거 파일 인덱스

| 비전 문서 | 위치 | 핵심 요구사항 |
|----------|------|-------------|
| 00\_vision.md | `docs/gonghaebun-planning/` | 제품 정의, 핵심 가치 5가지, 대상 사용자 |
| 01\_problem\_definition.md | 상동 | 5가지 인지 실패 모드 + 개입 설계 |
| 02\_research\_basis.md | 상동 | 7개 이론 → 설계 근거 매핑 |
| 03\_product\_principles.md | 상동 | 8가지 설계 원칙 (우선순위 포함) |
| 04\_mvp\_scope.md | 상동 | 3개 초기 개념 + MVP 성공 기준 |
| 05\_user\_session\_flow.md | 상동 | 3가지 세션 유형 + 단계별 흐름 |
| 06\_llm\_orchestration.md | 상동 | 7단계 LLM 파이프라인 |
| 07\_data\_model.md | 상동 | STUDY.md 스키마 + 엔티티 정의 |
| 08\_evaluation\_plan.md | 상동 | 5계층 평가 프레임워크 |
| 09\_risks\_and\_guardrails.md | 상동 | 7가지 위험 + 가드레일 |

## 부록 B: 현 구현 핵심 파일

| 범주 | 파일 | 역할 |
|------|------|------|
| 랜딩 | `apps/web/src/pages/ChatCompiler.tsx` | 한국어 채팅 분석기 |
| 네비 | `apps/web/src/components/Layout.tsx` | 한국어 네비게이션 + 개발자 토글 |
| 대시보드 | `apps/web/src/pages/Dashboard.tsx` | 영어 학습 현황 |
| 인출 | `apps/web/src/pages/RecallSession.tsx` | 혼합 언어 인출 연습 |
| API 분석 | `apps/api/services/compiler_analyzer_service.py` | 규칙 기반 분석 + `REPRESENTATION_PREVIEWS` (L65-137) |
| API 컴파일 | `apps/api/services/concept_service.py` | 8단계 컴파일 (`MockLLMClient` 하드코딩) |
| 파이프라인 | `src/gonghaebun/pipeline/session.py` | 12 아티팩트 생성 오케스트레이터 |
| 표현 생성 | `src/gonghaebun/pipeline/representation_gen.py` | Stage 3 — 5회 LLM 호출 (mock) |
| 자기 설명 | `src/gonghaebun/pipeline/self_explanation.py` | Stage 5 — 템플릿만, 평가 미사용 |
| 오개념 | `src/gonghaebun/pipeline/misconception_checker.py` | Stage 4 — diagnosis.json 생성, UI 없음 |
| 지식 | `src/gonghaebun/knowledge/real_analysis.py` | 10개 개념 + DAG + 키워드 + 별칭 |
| STUDY.md | `src/gonghaebun/study_md/writer.py` | 패치 적용 + 백업 + 검증 |
| 검증 | `src/gonghaebun/study_md/validate.py` | E001-E005, W001-W003 자동 검증/복구 |

---

## 13. 구현 준비 부록 (Implementation Readiness Addendum)

### GAP S0-1: 통합 학습 세션 미존재

| 항목 | 내용 |
|------|------|
| **원래 요구** | `05_user_session_flow.md` — New Concept Session 8단계가 단일 흐름으로 실행. "개념 입력 → 진단 → 선행 → 5표현+자기설명 → 오개념 → White Recall → STUDY.md → 요약" |
| **현재 동작** | 학습자가 Sources(`/sources`) → Bank Build → Review(`/review/:id`) → Export → Recall(`/recall`)로 5개 페이지를 수동 탐색. 개발자 파이프라인이 학습자 경로에 노출됨 |
| **근본 원인** | MVP1-3가 파이프라인 각 단계를 독립 CLI/API로 구현. MVP4에서 웹 UI를 씌웠지만 통합 학습 흐름을 설계하지 않고 각 단계를 별도 페이지로 노출 |
| **관련 파일** | `ChatCompiler.tsx` (랜딩), `SourceUpload.tsx`, `BankReview.tsx`, `ConceptCompiler.tsx`, `RecallSession.tsx`, `concept_service.py` (컴파일), `session.py` (파이프라인 오케스트레이터) |
| **수정 제안** | 신규 `/study/:conceptId` 라우트 + `StudySession.tsx` 6단계 스텝퍼. 백엔드 `POST /api/study-session`이 컴파일+bank 자동 준비를 내부 처리. 학습자는 개념 선택만 하면 됨 |
| **최소 구현 슬라이스** | R1a(UI shell) → R1b(백엔드) → R1c(연결) 순서. R1a만으로도 학습 흐름 시각화 가능 |
| **수락 기준** | (1) 학습자가 ChatCompiler에서 개념 인식 → "공부 시작" → `/study/compactness`로 이동 (2) 1개 페이지에서 6단계 진행 가능 (3) 수동 bank 리뷰 없이 인출까지 도달 (4) STUDY.md 자동 업데이트 |
| **테스트 전략** | E2E Playwright: 전체 흐름 완주. pytest: 세션 생성/조회 API. 단위: 스텝 전환 로직 |
| **위험** | 기존 `run_new_concept_session()`이 동기 실행 (~수초). LLM 활성화 시 30초+ 가능 → 비동기 처리 또는 로딩 UI 필요 |
| **하지 말 것** | 기존 `/recall`, `/sources`, `/review` 페이지를 삭제하지 말 것 — 개발자 도구로 유지. `POST /api/sessions` 기존 API를 제거하지 말 것 — 내부 재사용 |

### GAP S0-2: 5가지 표현 하드코딩

| 항목 | 내용 |
|------|------|
| **원래 요구** | `03_product_principles.md` P1 — "모든 개념에 정확히 5가지 표현(formal, intuitive, visual, counterexample, proof\_schema)". `04_mvp_scope.md` 성공 기준 1: "5 representations generated accurately" |
| **현재 동작** | `compiler_analyzer_service.py:65-137`의 `REPRESENTATION_PREVIEWS`가 3개 seed 개념에 대해 하드코딩 텍스트 반환. 소스 자료 무관. `representation_gen.py`의 LLM 생성은 `MockLLMClient`로만 호출 가능 (`concept_service.py:95`) |
| **근본 원인** | MVP4-R0에서 ChatCompiler 즉시 응답을 위해 하드코딩 미리보기 도입. 실제 LLM 생성 경로(`representation_gen.py`)는 작동하지만 API에서 MockLLMClient로 고정 |
| **관련 파일** | `compiler_analyzer_service.py` (REPRESENTATION\_PREVIEWS), `concept_service.py:95` (MockLLMClient 하드코딩), `representation_gen.py` (Stage 3 — 5회 LLM 호출), `llm/config.py` (LLM\_DISABLED) |
| **수정 제안** | R2에서 `concept_service.py`의 `MockLLMClient()` → `make_llm_client()` (설정 기반). `REPRESENTATION_PREVIEWS`는 LLM 실패 시 fallback으로 격하. LLM 생성 표현에 경고 배너 + 소스 해시 표시 |
| **최소 구현 슬라이스** | `concept_service.py`에 `if config.LLM_DISABLED: MockLLMClient() else: OpenAIClient()` 분기 1줄 추가만으로 실제 생성 경로 활성화 가능. 단, 가드레일(스키마 검증, 재시도, 타임아웃) 없이 배포 금지 |
| **수락 기준** | (1) `LLM_DISABLED=0` + API key 시 소스 기반 표현 실시간 생성 (2) 생성 표현에 grounding footer (소스 해시) 포함 (3) 경고 배너 "AI 생성 — 교재 검증 필요" 표시 (4) `LLM_DISABLED=1`이면 기존 mock 동작 유지 |
| **테스트 전략** | 단위: JSON 파싱 실패 → 재시도 → fallback. 통합: 실제 LLM 생성 (CI에서는 mock). 수동: 생성 표현의 수학적 정확성 리뷰 |
| **위험** | 수학적 환각 — Stage 3 생성 표현에 잘못된 정의/반례 포함 가능. `09_risks_and_guardrails.md` R1의 가드레일 필수 |
| **하지 말 것** | R1에서 LLM을 활성화하지 말 것 — R2에서 가드레일과 함께 활성화. `REPRESENTATION_PREVIEWS`를 R2 전에 삭제하지 말 것 — fallback으로 유지 |

### GAP S0-3: 대화형 진단 부재

| 항목 | 내용 |
|------|------|
| **원래 요구** | `05_user_session_flow.md` [2단계] — "지금 알고 있는 것을 자유롭게 적어 주세요" + "어디서 막히거나 헷갈리나요?" → 초기 mastery 추정 |
| **현재 동작** | `compiler_analyzer_service.py:272-277`의 `_infer_gap()`이 한국어 단서어 7개(`모르겠`, `헷갈`, `증명` 등)를 단순 substring 매칭. 학습자 응답을 수집하지 않음 |
| **근본 원인** | ChatCompiler가 단일 메시지 분석기로 설계됨 — 대화형 질의응답 구조가 아님 |
| **관련 파일** | `compiler_analyzer_service.py` (GAP\_CUES, \_infer\_gap), `ChatCompiler.tsx` (단일 입력 → 분석 결과 표시) |
| **수정 제안** | StudySession 1단계에서 두 개의 textarea (사전 지식 / 갭 서술)를 수집. `POST /api/study-session/{id}/diagnose`에서 저장. R1b에서는 결정적 처리 (키워드 기반), R2에서 LLM 평가 전환 |
| **최소 구현 슬라이스** | R1a — 2개 textarea UI 배치. R1b — diagnose 엔드포인트에서 텍스트 저장만 (평가 없이). R2 — LLM 평가 추가 |
| **수락 기준** | (1) StudySession 1단계에서 학습자가 사전 지식과 갭을 텍스트로 입력 (2) 입력 내용이 세션 아티팩트에 저장 (3) R2 이후 LLM이 초기 mastery 추정 반환 |
| **테스트 전략** | pytest: diagnose 엔드포인트 CRUD. E2E: 텍스트 입력 → 다음 단계 이동 |
| **위험** | 낮음 — 텍스트 수집 단계는 복잡도 최소 |
| **하지 말 것** | ChatCompiler를 대화형으로 개조하지 말 것 — ChatCompiler는 개념 매칭 랜딩으로 유지하고, 대화형 진단은 StudySession에서 처리 |

### GAP S1-4: 오개념 MCQ 미제시

| 항목 | 내용 |
|------|------|
| **원래 요구** | `05_user_session_flow.md` [5단계] — MCQ 형식으로 제시 + 즉시 피드백 + 반례. `09_risks_and_guardrails.md` R5: "판단해 보세요" 형식 필수 |
| **현재 동작** | `misconception_checker.py`가 `diagnosis.json` 생성 (misconceptions 리스트: id, claim, is\_correct, counterexample). 그러나 학습자에게 MCQ로 제시하는 UI 없음. 데이터만 파일에 존재 |
| **근본 원인** | Stage 4 백엔드는 완성되었으나 프론트엔드 MCQ 컴포넌트가 미구현 |
| **관련 파일** | `misconception_checker.py` (백엔드 — 완성), `diagnosis.json` (아티팩트), `StudySession.tsx` (프론트엔드 — 미구현) |
| **수정 제안** | R3에서 StudySession 4단계에 MCQ 컴포넌트 추가. `diagnosis.json`의 misconceptions를 참/거짓 문제로 제시. 정답 시 "정답! 반례: ..." 표시. 오답 시 "반례: ... 해설: ..." 표시 |
| **최소 구현 슬라이스** | (1) `diagnosis.json` 로드 (2) MCQ 라디오 버튼 UI (3) 제출 → 즉시 결과 표시 — 백엔드 추가 없이 프론트엔드만으로 가능 (데이터는 이미 아티팩트에 존재) |
| **수락 기준** | (1) 각 misconception이 참/거짓 MCQ로 표시 (2) 제출 시 즉시 정답/오답 + 반례 표시 (3) 오개념을 사실로 제시하지 않음 (`09_risks_and_guardrails.md` R5 준수) |
| **테스트 전략** | 컴포넌트 테스트: MCQ 렌더링 + 정답/오답 피드백. E2E: 4단계 MCQ 응답 |
| **위험** | 오개념을 사실로 제시하는 UX 실수 — "이 주장이 맞습니까?" 형태로만 제시 |
| **하지 말 것** | 오개념 claim을 설명문처럼 표시하지 말 것 — 반드시 질문 형태로 |

### GAP S1-5: 자기 설명 미구현

| 항목 | 내용 |
|------|------|
| **원래 요구** | `03_product_principles.md` P5 — 각 표현 후 "자기 말로 설명해 보세요" + LLM 평가 (accuracy\_score, missing\_elements, errors) |
| **현재 동작** | `self_explanation.py:18-48`의 `render_self_explanation_prompt()`은 마크다운 템플릿만 생성. `evaluate_self_explanation()` (L51-80)은 학습자 응답이 제공될 때만 호출되는데, 현재 응답 수집 UI가 없어 한 번도 호출되지 않음 |
| **근본 원인** | Stage 5 백엔드(`evaluate_self_explanation`)는 구현되어 있으나, 학습자 응답을 수집하는 프론트엔드 + API 엔드포인트가 없음 |
| **관련 파일** | `self_explanation.py` (evaluate\_self\_explanation — 구현 완료), `StudySession.tsx` (UI — 미구현), `study_session_service.py` (API — 미구현) |
| **수정 제안** | R1d에서 각 표현 후 textarea + 제출 → `POST .../self-explain` → `evaluate_self_explanation()` 호출 → 결과 반환. R1d에서는 MockLLMClient, R2에서 실제 LLM |
| **최소 구현 슬라이스** | (1) 표현 카드 하단 textarea (2) 제출 버튼 (3) MockLLM 평가 결과 표시 |
| **수락 기준** | (1) 각 표현 후 "자기 말로 설명해 보세요" 프롬프트 (2) 학습자 텍스트 제출 가능 (3) 피드백 (accuracy + missing + errors) 표시 |
| **테스트 전략** | pytest: self-explain 엔드포인트 → RecallEvaluation 반환. 단위: MockLLM fixture 매칭 |
| **위험** | MockLLM 평가가 무의미할 수 있음 (fixture 고정 응답). R2에서 실제 LLM 평가로 전환 필수 |
| **하지 말 것** | 자기 설명을 선택적(건너뛸 수 있는) 단계로 만들지 말 것 — `03_product_principles.md`에서 필수로 규정 |

### GAP S1-6: White Recall 세션 미통합

| 항목 | 내용 |
|------|------|
| **원래 요구** | `03_product_principles.md` P6 — "매 세션 종료 시 White Recall Loop 필수". `09_risks_and_guardrails.md` R2: "White Recall 필수 — 세션 완료 불가" |
| **현재 동작** | `/recall` 페이지에 인출 연습 존재. 그러나 (1) 세션 내 필수 단계가 아님 — 건너뛸 수 있음 (2) 첫 사용 시 accepted bank 필요 — 수동 준비 없이 사용 불가 (3) `RecallSession.tsx`에서 `grader: 'mock'` 하드코딩 |
| **근본 원인** | Recall이 독립 페이지로 구현되어 학습 세션 흐름에 포함되지 않음. bank 의존성으로 진입 장벽 높음 |
| **관련 파일** | `RecallSession.tsx` (독립 페이지), `POST /api/sessions` (기존 세션 API), `study_session_service.py` (자동 bank 준비 필요) |
| **수정 제안** | R1c에서 StudySession 5단계에 인출 UI 내장. R1d에서 인출 미완료 시 complete 차단. 기존 `POST /api/sessions` 로직을 `POST .../recall`에서 위임 호출 |
| **최소 구현 슬라이스** | (1) StudySession 5단계에 질문 표시 + textarea (2) 제출 → `POST /api/sessions` 재사용 (3) 5단계 미완료 시 6단계 차단 |
| **수락 기준** | (1) StudySession에서 인출 단계 건너뛸 수 없음 (2) accepted bank 자동 준비 (수동 리뷰 불필요) (3) 인출 완료 → STUDY.md 자동 업데이트 |
| **테스트 전략** | E2E: 5단계 건너뛰기 시도 → 6단계 차단. pytest: recall 미제출 시 complete 거부 |
| **위험** | 기존 `/recall` 페이지와 중복 가능 — `/recall`은 독립 복습 세션용으로 유지 |
| **하지 말 것** | 기존 `/recall` 페이지를 삭제하지 말 것 — Review Session (STUDY.md due 기반 복습)에서 계속 사용 |

### GAP S2-7: 한국어 UX 불완전

| 항목 | 내용 |
|------|------|
| **원래 요구** | `00_vision.md` — 대상 사용자: 학부 3-4학년 한국어 사용자. 세션 흐름 프롬프트 전체 한국어 |
| **현재 동작** | Dashboard: 완전 영어 (~40개 문자열). RecallSession: 혼합 (~30개 영어 문자열). 학습자가 "무엇을 복습해야 하는지" 확인하는 Dashboard가 전체 영어 |
| **근본 원인** | Dashboard와 RecallSession은 MVP4-A/D에서 영어로 개발. MVP4-R0에서 ChatCompiler와 Layout만 한국어화 |
| **관련 파일** | `Dashboard.tsx` (~40개 문자열), `RecallSession.tsx` (~30개 문자열) |
| **수정 제안** | R0.1에서 두 파일의 모든 영어 UI 문자열을 한국어로 교체. i18n 라이브러리 불필요 — 상수 직접 교체 |
| **최소 구현 슬라이스** | 문자열 교체만 — 로직 변경 없음. 약 70개 문자열 × 2파일 |
| **수락 기준** | (1) Dashboard: "Review Due" → "복습 예정" 등 전체 한국어 (2) RecallSession: "Recall Session" → "인출 연습" 등 전체 한국어 (3) 개발자 도구는 영어 유지 |
| **테스트 전략** | 기존 Playwright 통과. 수동: 전체 학습자 경로에서 영어 문자열 0개 확인 |
| **위험** | 극히 낮음 — 순수 문자열 교체 |
| **하지 말 것** | i18n 라이브러리를 도입하지 말 것 — 단일 언어 제품이므로 과도한 추상화. 개발자 도구까지 한국어화하지 말 것 |

---

## 14. API 스키마 스케치

### POST /api/study-session — 통합 학습 세션 생성

요청:
```json
{
  "concept_id": "compactness",
  "source_path": "compactness/rudin_ch2.md"
}
```
`source_path`는 선택적. 미제공 시 해당 concept의 기존 소스 자동 탐색.

응답 (201):
```json
{
  "session_id": "a1b2c3d4-...",
  "concept_id": "compactness",
  "canonical_name_ko": "옹골성",
  "current_step": 1,
  "steps": ["diagnose", "prerequisites", "representations", "misconceptions", "recall", "summary"],
  "representations": {
    "formal": "...",
    "intuitive": "...",
    "visual": "...",
    "counterexample": "...",
    "proof_schema": "..."
  },
  "prerequisites": [
    {"concept_id": "metric_space", "mastery": "solid"},
    {"concept_id": "open_cover", "mastery": "unknown"}
  ],
  "misconceptions": [
    {"id": "compactness_m01", "claim": "콤팩트 집합은 유계이다", "is_correct": false}
  ]
}
```

### GET /api/study-session/{session\_id} — 세션 상태 조회

응답 (200):
```json
{
  "session_id": "a1b2c3d4-...",
  "concept_id": "compactness",
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

### POST /api/study-session/{session\_id}/diagnose — 진단 제출

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
  "identified_gaps": ["유한 부분덮개의 필요성", "컴팩트성과 유한성의 관계"],
  "recommendation": "formal 표현부터 시작하는 것을 권장합니다"
}
```
R1b에서는 결정적 응답 (키워드 기반). R2에서 LLM 평가.

### POST /api/study-session/{session\_id}/self-explain — 자기 설명 제출

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

### POST /api/study-session/{session\_id}/recall — White Recall 제출

요청:
```json
{
  "answers": [
    {
      "question_id": "q_formal_001",
      "learner_response": "콤팩트 집합은..."
    },
    {
      "question_id": "q_counterexample_001",
      "learner_response": "(0,1) 구간은 콤팩트가 아닌데..."
    }
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
      "mastery_before": "partial",
      "mastery_after": "solid"
    }
  ],
  "overall_summary": "2개 질문 중 2개 정답. formal: partial → solid."
}
```

### POST /api/study-session/{session\_id}/complete — 세션 완료

요청: 없음 (빈 body 또는 `{}`)

응답 (200):
```json
{
  "session_id": "a1b2c3d4-...",
  "summary_ko": "오늘 다룬 내용: compactness (5가지 표현)\nmastery 변화: formal partial→solid, intuitive unknown→partial\n다음 복습일: 2026-05-09\n남은 선행: open_cover (unknown)",
  "mastery_changes": [
    {"representation": "formal", "before": "partial", "after": "solid"},
    {"representation": "intuitive", "before": "unknown", "after": "partial"}
  ],
  "next_review_date": "2026-05-09",
  "study_md_updated": true
}
```
전제 조건: recall 단계 완료 필수. 미완료 시 `400 {"detail": "인출 연습을 먼저 완료해야 합니다"}`.

---

## 15. LLM 정책

### 단계별 LLM 활성화 원칙

1. **MVP4-R0.1 / R1a / R1b / R1c / R1d**: LLM 생성 활성화 금지
   - `MockLLMClient()` 유지
   - `LLM_DISABLED=1` (기본값) 변경 금지
   - 제품 흐름은 mock/fixture로 전체 동작해야 함

2. **MVP4-R2에서만 실제 LLM 생성 활성화**
   - 다음 가드레일이 모두 구현된 후에만:
     - JSON 스키마 검증 (출력 파싱 실패 감지)
     - 1회 재시도 (파싱 실패 시)
     - 30초 타임아웃 (`llm/config.py`)
     - 세션당 30,000 토큰 상한
     - 시스템 프롬프트: 불확실성 표현 강제 + 교재 참조
     - UI 경고 배너: "AI 생성 — 교재에서 검증하세요"
   - `LLM_DISABLED=0` + `OPENAI_API_KEY` 설정으로 활성화

3. **LLM 그레이딩은 로컬 테스트 가능** (기존 `LLMGrader` via `POST /api/sessions`)
   - 단, 학습 세션 제품 흐름(`/study`)에서는 R1d까지 `grader: 'mock'` 유지

4. **OPENAI\_API\_KEY 관리**
   - `.env` 파일에서만 로드 (환경 변수)
   - 코드, 설정 파일, 커밋에 절대 포함 금지
   - `.env.example`에는 placeholder만 (`OPENAI_API_KEY=sk-...your-key-here`)

---

## 16. 다음 행동 권고

### 지금 즉시 해야 할 것

**MVP4-R0.1 구현 시작** — Dashboard와 RecallSession 한국어화.
- 이유: 코드 변경량 최소 (~70개 문자열 교체), 위험 없음, 학습자 대면 UX 즉시 개선
- 예상 소요: 1 세션
- Claude Code 프롬프트 예시:

```
Dashboard.tsx와 RecallSession.tsx의 모든 영어 UI 문자열을 한국어로 교체하세요.
개발자 도구 페이지는 변경하지 마세요.
기존 테스트가 통과해야 합니다.
```

### R0.1 완료 후 다음

**MVP4-R1a 구현** — StudySession.tsx 6단계 스텝퍼 shell.
- 이유: S0-1 해소의 첫 단계. 학습 흐름 시각화만으로도 제품 정체성 개선
- Claude Code 프롬프트 예시:

```
/study/:conceptId 라우트에 6단계 한국어 스텝퍼 UI를 만드세요.
단계: 진단 → 선행 → 표현 → 오개념 → 인출 → 정리.
백엔드 API 없이 프론트엔드 placeholder로 구현.
ChatCompiler에서 "공부 시작" 클릭 시 /study/:conceptId로 이동.
```

### 지금 하지 말아야 할 것

1. **서버 경화(MVP4-M) 진행 금지** — 제품 적합성이 수리되기 전에 인프라를 경화하는 것은 시기상조. R1d 완료 후 재검토
2. **재배포 금지** — 현 상태는 개발자 도구가 학습자에게 노출되는 상태. R0.1 + R1a 최소 완료 후 배포
3. **LLM 활성화 금지** — 가드레일 없이 LLM 활성화 시 수학적 환각 위험. R2에서만 활성화
4. **새 도메인/개념 추가 금지** — 기존 3개 seed 개념에서 핵심 루프가 작동하지 않는 상태에서 범위 확장은 낭비

### 배포 시점

| 마일스톤 | 배포 적합성 |
|---------|-----------|
| 현재 | ❌ — 개발자 도구가 학습자에 노출, 영어 UI, 통합 세션 없음 |
| R0.1 완료 | ❌ — 한국어는 개선되나 통합 세션 없음 |
| R1d 완료 | ⚠️ — 통합 세션 작동하나 mock만 사용. 내부 테스트 배포 가능 |
| R2 완료 | ✅ — 소스 기반 LLM 생성 + 가드레일. 파일럿 배포 가능 |

---

## 부록 C: 마일스톤 의존 관계

```
MVP4-R0.1 (한국어화)
    │
    ├── 독립 — 다른 마일스톤과 병행 가능
    │
MVP4-R1a (UI shell) ──→ MVP4-R1c (통합)
    │                        │
MVP4-R1b (백엔드)  ──→ MVP4-R1c
                             │
                        MVP4-R1d (자기설명+인출)
                             │
                        MVP4-R2 (LLM 생성)
                             │
                        MVP4-R3 (MCQ+스캐폴딩)
                             │
                        MVP4-M (프로덕션)
```

R0.1은 R1과 완전 독립 — 병렬 진행 가능.
R1a와 R1b는 병렬 진행 가능 (프론트/백 분리).
R1c는 R1a + R1b 양쪽 완료 필요.

---

_본 보고서는 코드 변경 없이 문서 분석만을 수행한 진단 보고서입니다._
_다음 행동: MVP4-R0.1 (한국어화) 즉시 시작, 이후 MVP4-R1a (StudySession shell) 진행._
