# 06. LLM 오케스트레이션 설계

## 설계 원칙

1. **LLM은 학습 지원 도구이지 답 생성기가 아니다.**
   → `llm-based-education_1-s20-s2666920x25001699-main_s20_c01`
2. **각 파이프라인 단계는 단일 책임**을 가진다.
3. **수학적 정확성이 흥미보다 우선**한다.
4. **출력은 검증 가능해야** 한다 — 모든 주장에 근거 또는 반례가 따른다.

---

## 파이프라인 개요

```
학습자 입력 (개념 이름 + 맥락)
        │
        ▼
[Stage 1] Concept Resolver
        │  → 개념 정규화, 도메인 확인
        ▼
[Stage 2] Prerequisite Graph Builder
        │  → DAG 생성, mastery_state 쿼리
        ▼
[Stage 3] Representation Generator
        │  → formal / intuitive / visual / counterexample / proof_schema
        ▼
[Stage 4] Misconception Checker
        │  → 알려진 오개념 패턴 → MCQ 생성
        ▼
[Stage 5] Self-Explanation Evaluator
        │  → 학습자 서술 평가, gap 식별
        ▼
[Stage 6] White Recall Orchestrator
        │  → 인출 태스크 생성, 응답 평가
        ▼
[Stage 7] STUDY.md Writer
           → mastery_state 업데이트, next_review_date 계산
```

---

## Stage별 상세 설계

### Stage 1: Concept Resolver

**입력**: 자유형 텍스트 (예: "compactness", "콤팩트", "compact set이란")
**출력**: `{ concept_id, canonical_name, domain, aliases }`

**프롬프트 계층**:
```
System: 너는 Real Analysis 전문가이다. 입력된 개념 이름을 정규화하라.
        - 도메인이 Real Analysis인지 확인하라.
        - 범위를 벗어난 개념은 명시적으로 알린다.
User: [입력 텍스트]
```

**실패 모드**: 개념이 MVP 범위 밖 → 사용자에게 알리고 중단.

---

### Stage 2: Prerequisite Graph Builder

**입력**: `concept_id`
**출력**: `{ nodes: [{ concept_id, name, mastery_state }], edges: [{ from, to }] }`

**프롬프트 계층**:
```
System: 너는 Real Analysis 교육과정 전문가이다.
        주어진 개념을 이해하기 위해 반드시 선행되어야 하는 개념들의
        방향 그래프(DAG)를 생성하라.
        - 각 노드는 { concept_id, canonical_name, depth } 를 포함한다.
        - depth 1: 직접 선행 / depth 2: 간접 선행
        - 최대 depth 3까지만 포함한다.
        - 순환이 없어야 한다.
User: concept: compactness
```

**검증**:
- 출력 JSON을 파싱하여 cycle 검사.
- depth > 3이면 truncate.

**STUDY.md 연동**: 기존 STUDY.md에 해당 concept_id의 mastery_state가 있으면 그 값을 사용.

---

### Stage 3: Representation Generator

**입력**: `concept_id`, `mastery_state` (현재 학습자 수준)
**출력**: `{ formal, intuitive, visual_description, counterexample, proof_schema }`

**프롬프트 계층 (formal)**:
```
System: 너는 Real Analysis 교재(Rudin, Bartle 수준)를 기준으로 하는
        수학 교육 전문가이다.
        - 정의는 수학적으로 완전하고 정확해야 한다.
        - 기호와 용어는 표준을 따른다.
        - 추측이나 불확실한 내용은 절대 포함하지 않는다.
User: {concept}의 formal definition을 제시하라.
      다음 형식으로: (1) 정의 (2) 각 기호 설명 (3) 동치 특성화 (있는 경우)
```

**프롬프트 계층 (proof_schema)**:
```
System: 수학 증명 구조 분석 전문가.
        "{concept}를 사용하는 표준 증명"의 뼈대를 제시하라.
        - Goal (무엇을 증명하는가)
        - Strategy (왜 이 전략인가)
        - Key steps (핵심 단계 3-5개)
        - Common pitfalls (주의할 점)
User: compactness를 사용하는 표준 증명 스키마를 생성하라.
```

**mastery_state 조건부 로직**:
- `unknown` → 모든 표현 전체 생성
- `partial` → 학습자가 모른다고 한 표현만 재생성
- `solid` → 변형 문제 또는 심화 표현 생성

---

### Stage 4: Misconception Checker

**입력**: `concept_id`
**출력**: `{ misconceptions: [{ claim, is_correct, counterexample, explanation }] }`

**프롬프트 계층**:
```
System: Real Analysis 학습자가 자주 갖는 오개념 전문가.
        주어진 개념에 대해 흔한 오개념 3-5개를 MCQ 또는 참/거짓 형식으로 제시하라.
        각 항목: { claim, is_correct: bool, counterexample (오류인 경우), explanation }
User: compactness에 대한 오개념 목록을 생성하라.
```

**주의**: 오개념을 사실인 것처럼 제시했다가 정정하는 방식 금지.
         반드시 학습자에게 "이것이 맞는지 판단해 보세요" 형식으로 제시.

---

### Stage 5: Self-Explanation Evaluator

**입력**: `{ concept_id, representation_type, student_explanation (텍스트) }`
**출력**: `{ accuracy_score: 0-1, missing_elements: [...], errors: [...], feedback }`

**프롬프트 계층**:
```
System: Real Analysis 수학 교수자.
        학습자의 설명을 다음 기준으로 평가하라:
        (1) 수학적 정확성 (오류 있는지)
        (2) 완전성 (핵심 요소가 포함되었는지)
        (3) 논리적 연결 (추론 단계가 명시적인지)
        - 틀린 수학적 주장은 반드시 명시하고 반례를 제시한다.
        - 격려 메시지는 짧게, 오류 수정은 명확하게.
User: 개념: compactness (formal definition)
      학습자 설명: [학습자 입력]
      평가 기준: [정의의 핵심 요소 목록]
```

---

### Stage 6: White Recall Orchestrator

**입력**: `concept_id`, `mastery_state`
**출력**: 인출 태스크 세트

**프롬프트 계층**:
```
System: 인출 연습 설계 전문가.
        다음 원칙에 따라 인출 태스크를 설계하라:
        - 자료 없이 수행 가능한 태스크만
        - mastery_state = unknown: 정의 재서술 + 반례 1개
        - mastery_state = partial: 증명 스키마 재구성
        - mastery_state = solid: 변형 증명 또는 응용 문제
        - 답을 먼저 제시하지 않는다.
User: concept: compactness, mastery_state: {state}
```

---

### Stage 7: STUDY.md Writer

**입력**: 세션 결과 (accuracy_scores per representation, misconceptions identified)
**출력**: STUDY.md 패치 (diff)

**로직** (LLM 없음, 결정론적):
```python
def compute_mastery_state(accuracy_score):
    if accuracy_score >= 0.85: return "solid"
    if accuracy_score >= 0.50: return "partial"
    return "unknown"

def compute_next_review(current_state, prev_state):
    if current_state == "solid":
        return today + timedelta(days=7)
    if current_state == "partial":
        return today + timedelta(days=3)
    return today + timedelta(days=1)
```

---

## 프롬프트 계층 구조

```
┌─────────────────────────────────────────┐
│ Global System Prompt (모든 stage 공통)  │
│ - 수학적 정확성 최우선                  │
│ - 확실하지 않은 것은 "모른다"고 말함   │
│ - 학습자를 위한 설명이지 답 제공이 아님│
└─────────────────────────────────────────┘
        │
┌───────┴────────────────────────┐
│ Stage-specific System Prompt   │
│ (각 stage 역할 정의)           │
└───────┬────────────────────────┘
        │
┌───────┴────────────────────────┐
│ User Prompt (동적 내용)        │
│ (개념, 학습자 입력, context)   │
└────────────────────────────────┘
```

---

## 오케스트레이션 실패 모드

| 실패 | 감지 방법 | 대응 |
|---|---|---|
| JSON 파싱 실패 | try/except | 재시도 1회, 실패 시 사용자에게 알림 |
| 수학적 오류 의심 | 출력에 "might", "I think" 등 불확실 표현 | 경고 플래그 + 사용자에게 검토 요청 |
| 범위 외 개념 | Stage 1에서 감지 | 중단 + 사용자 안내 |
| 과도하게 긴 출력 | 토큰 수 체크 | 단계 분할 또는 요약 요청 |
| Hallucination (가짜 반례) | TODO: 자동 검증 어려움 | 사용자에게 "수학 교재에서 확인하세요" 경고 |

---

## 비고

- LLM API 호출 구현은 이 문서의 범위 밖 (v1 설계 단계).
- 모델 선택: 수학적 정확성이 요구되므로 reasoning 능력이 강한 모델 권장.
  TODO: 실제 모델 벤치마크 후 결정.
- Streaming vs batch: 사용자 경험상 streaming 권장 (각 표현을 순차 출력).
