# 08. 평가 계획

## 평가 목표

1. Gonghaebun이 실제 학습 효과를 내는지 확인한다.
2. 어느 파이프라인 단계가 효과적인지 식별한다.
3. LLM 출력의 수학적 정확성을 보장한다.
4. 사용자 경험이 학습을 방해하지 않음을 확인한다.

---

## 평가 계층

### Layer 1: 수학적 정확성 (자동 + 수동)

**목적**: LLM이 생성한 정의, 반례, proof schema가 수학적으로 올바른지.

**지표**:
- `definition_accuracy_rate` — 생성된 정의 중 교재 기준 정확한 비율
- `counterexample_validity_rate` — 반례가 실제 반례인지
- `proof_schema_correctness` — proof schema의 논리적 흐름 오류 유무

**측정 방법**:
- **수동 검토 (v1)**: Real Analysis 전문가 (교수, 대학원생)가 샘플 출력 검토.
  - 초기 3개 개념에 대해 10회 생성 → 전수 검토.
- **자동 검토 (v2)**: 알려진 정의 목록과 semantic similarity 비교.
  TODO: 수식 검증 도구 선택.

**기준**:
- `definition_accuracy_rate` ≥ 0.95 (5% 미만 오류 허용)
- `counterexample_validity_rate` = 1.0 (반례 오류 0% 목표)

---

### Layer 2: 학습 효과 — 세션 내 (단기)

**목적**: 단일 세션에서 mastery_state가 유의미하게 변화하는지.

**지표**:
- `pre_post_recall_delta` — 세션 전후 White Recall 점수 변화
- `self_explanation_quality_score` — LLM 평가 accuracy_score 분포
- `misconception_correction_rate` — 오개념 MCQ에서 세션 후 정답률

**측정 방법**:
- 세션 전: "지금 알고 있는 것을 써 보세요" (blind recall)
- 세션 후: White Recall Loop 점수
- 차이 = `post_score - pre_score`

**기준 (파일럿 목표)**:
- `pre_post_recall_delta` > 0.3 (30% 향상)
- `misconception_correction_rate` ≥ 0.80

---

### Layer 3: 학습 효과 — 세션 간 (장기 파지)

**목적**: 며칠 후 Review Session에서 지식이 파지되었는지.

**이론 근거**:
- Roediger et al. (2011): retrieval practice effects maintained for several months.
  → `retrieval-practice_roediger-agarwal-etal-2011-jepa_s04_c01`
- Bjork & Bjork: storage strength vs retrieval strength distinction.
  → `desirable-difficulties_itow-introducing-desirable-difficulties-into-practice-and-instruction-bjork_s00_c03`

**지표**:
- `retention_rate_1d` — 1일 후 Review Session White Recall 점수
- `retention_rate_7d` — 7일 후 점수
- `forgetting_curve_slope` — 시간에 따른 mastery_state 하락 속도

**측정 방법**:
- STUDY.md의 `next_review_date` 기반 Review Session 추적.
- 각 Review Session에서 blind recall 점수 기록.

**기준 (파일럿 목표)**:
- `retention_rate_7d` ≥ 0.70 (1주 후 70% 파지)

---

### Layer 4: 파이프라인 단계별 기여 분석 (A/B)

**목적**: 어느 단계가 학습에 가장 기여하는지.

**실험 설계** (v2 이후):

| 조건 | 설명 |
|---|---|
| Full pipeline | 모든 5개 표현 + White Recall Loop |
| No counterexample | counterexample 표현 없음 |
| No proof_schema | proof_schema 없음 |
| No White Recall | White Recall Loop 없음 |
| Single representation | formal definition만 |

**측정**: 조건별 `retention_rate_7d` 비교.

**주의**: 소규모 파일럿에서는 통계적 유의성 달성이 어려울 수 있음.
         n ≥ 20 / 조건 권장.

---

### Layer 5: 사용자 경험 평가

**목적**: 세션이 너무 길거나 복잡하지 않은지, 학습자가 지속하는지.

**지표**:
- `session_completion_rate` — 시작한 세션 중 완료한 비율
- `dropout_stage` — 어느 단계에서 이탈하는지
- `self_reported_clarity` — "이 설명이 이해에 도움이 되었나요?" (1-5점)
- `self_reported_load` — "이 세션이 너무 어렵게 느껴졌나요?" (1-5점)

**측정**: 세션 말미 짧은 자기 보고 (2-3개 질문).

---

## 파일럿 계획

### Phase 1: 전문가 정확성 검토 (구현 전)

- **대상**: compactness, connectedness, uniform continuity 각각에 대해
  LLM에게 5가지 표현 생성 요청 (수동 실행)
- **검토자**: Real Analysis 배경의 대학원생 2인
- **기간**: 구현 완료 전
- **결과물**: 정확성 보고서 + 시스템 프롬프트 개선 사항

### Phase 2: 소규모 파일럿 (n=5-10)

- **대상**: 해석학 공부 중인 학부 3-4학년
- **기간**: 2주
- **프로토콜**: 각자 3개 개념 학습 (New Concept Session × 3 + Review Session × 3)
- **데이터 수집**: STUDY.md 로그 + 세션 말미 설문
- **주요 질문**: White Recall Loop가 실제로 gap을 드러내는가?

### Phase 3: 비교 실험 (n=30+)

- **조건**: Full pipeline vs. No White Recall (대조군)
- **도메인**: Real Analysis
- **측정**: 2주 후 blind recall 테스트
- TODO: IRB 승인 필요 여부 검토.

---

## 평가 데이터 수집 위치

| 데이터 | 저장 위치 |
|---|---|
| mastery_state 변화 | STUDY.md |
| recall 점수 | STUDY.md (세션 요약) |
| 세션 완료 여부 | STUDY.md (session log) |
| 자기 보고 설문 | 별도 파일 `feedback.md` (v1) |
| LLM 출력 원문 | 세션 중 임시; v2에서 `sessions/` 저장 |

---

## 미결 사항

- TODO: 수식 자동 검증 도구 선택 (SymPy? Lean? 수동?)
- TODO: 파일럿 참가자 모집 방법
- TODO: 장기 파지 측정을 위한 30일 추적 설계
