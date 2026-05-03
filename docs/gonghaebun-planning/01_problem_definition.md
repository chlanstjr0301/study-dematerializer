# 01. 문제 정의 — 왜 어려운 개념은 공부해도 이해되지 않는가

## 핵심 전제

학습 실패는 대부분 "노력 부족"이 아니라 **인지 구조적 실패**에서 비롯된다.
Gonghaebun은 다음 5가지 메커니즘을 각각 식별하고, 각각에 대응하는 개입을 설계한다.

---

## Failure Mode 1: Representational Bottleneck

**정의**: 학습자가 개념을 단 하나의 표현(예: formal definition)으로만 접근하여, 그 표현이 이해되지 않으면 학습 자체가 차단되는 현상.

**예시 (compactness)**:
> "모든 열린 덮개에 유한 부분 덮개가 존재한다"는 ε-δ 정의를 외웠지만, 실제로 집합이 compact한지 판단하지 못함.

**근거**:
- Ainsworth (2006)은 단일 표현이 충분한 학습을 보장하지 않으며, 표현의 함수(function)는 complementing, constraining, constructing deeper understanding으로 구분된다고 논한다.
  → `multiple-representations_ainsworth-2006-learning-and-instruction_s01_c01`, `s12_c01`, `s16_c01`
- "learners find translating between representations difficult"
  → `multiple-representations_ainsworth-2006-learning-and-instruction_s18_c01`

**Gonghaebun 개입**: 단일 개념에 대해 **5가지 표현** (formal definition, intuitive description, visual/geometric, counterexample, proof-schema) 을 강제 생성.

---

## Failure Mode 2: Prerequisite Graph Blindness

**정의**: 학습자가 어떤 개념을 이해하기 위해 무엇을 먼저 알아야 하는지 인식하지 못한 채, 선행 개념의 공백을 모른 채 전진하는 현상.

**예시**:
> uniform continuity를 이해하려 하지만 pointwise continuity, quantifier order, Cauchy sequence의 개념이 불안정한 상태.

**근거**:
- Novak (1990)의 concept mapping은 개념 간 명시적 연결 관계를 시각화함으로써 이해 구조를 드러낼 수 있음을 보인다.
  → `concept-mapping_novak1990_s00_c01`
- Sweller (2019)에서 element interactivity 개념: 상호작용하는 요소 수가 많을수록 working memory 부하가 기하급수적으로 증가함.
  → `cognitive-load-theory_s10648-019-09465-5_s03_c03`, `s03_c12`

**Gonghaebun 개입**: 개념 입력 시 **prerequisite graph 자동 생성**. 미달성 선행 개념은 mastery_state = `unknown`으로 표시하고 우선 학습 유도.

---

## Failure Mode 3: Schema Acquisition Failure

**정의**: 학습자가 증명이나 풀이의 개별 단계를 따라가지만, 전체 구조(schema)를 추상화하지 못해 새로운 문제에 적용하지 못하는 현상.

**예시**:
> "이 compactness 증명은 이해했는데, 다른 compact set 증명은 어떻게 시작해야 할지 모른다."

**근거**:
- Sweller (2019)는 worked examples가 novice에게 유리한 이유를 element interactivity 감소와 schema 형성 촉진으로 설명한다.
  → `cognitive-load-theory_s10648-019-09465-5_s03_c14`
- TODO: verify against corpus chunk — `example-based-learning_ayres2012`는 코퍼스에서 읽기 불가 (mislabeled PDF). Renkl (2013) worked example 이론은 CLT 논문 참고 목록에 있으나 chunk 없음.

**Gonghaebun 개입**: 증명을 **proof schema** (목표 → 전략 선택 → 핵심 단계 → 결론 구조) 로 분해. 학습자가 스키마를 먼저 익히고, 세부 단계는 fading 방식으로 노출.

---

## Failure Mode 4: Metacognitive Failure

**정의**: 학습자가 자신이 개념을 이해했다고 믿지만 실제로는 이해하지 못한 상태 — "illusion of knowing".

**예시**:
> 교재를 읽으며 고개를 끄덕였지만, "이 개념을 설명해 보라"는 요청에 막힘.

**근거**:
- Chi et al. (1994): self-explanation을 많이 생성한 학습자(high explainers)는 적게 생성한 학습자(low explainers)에 비해 사후 이해 검사에서 현저히 높은 점수를 보임. 단순 읽기는 이해 착각을 유발함.
  → `self-explanation-effect_cognitive-science-july-1994-chi-eliciting-selfexplanations-improves-underst_s05_c02`, `s05_c05`
- Bjork & Bjork: 학습자는 massed study처럼 유창하게 느껴지는 조건을 실제 학습과 혼동하는 경향이 있음.
  → `desirable-difficulties_itow-introducing-desirable-difficulties-into-practice-and-instruction-bjork_s00_c04`
- Sweller (2019): 높은 인지 부하가 학습의 증거라는 잘못된 신호로 작용할 수 있음.
  → `cognitive-load-theory_s10648-019-09465-5_s04_c03`

**Gonghaebun 개입**: **White Recall Loop** — 자료를 덮고 개념을 직접 서술하게 하는 강제 인출 세션. 결과를 self-explanation 프롬프트와 연결.

---

## Failure Mode 5: Affective Friction

**정의**: 학습 초기의 혼란, 좌절, "내가 수학에 소질이 없는 것 같다"는 감정이 학습 지속을 차단하는 현상.

**예시**:
> compactness 정의를 처음 접하고, 이해가 안 되자 공부를 중단하거나 더 쉬운 자료를 찾아 방황.

**근거**:
- Bjork & Bjork: desirable difficulties는 학습자 관점에서 여전히 어렵게 느껴지기 때문에 도입에 장벽이 있다.
  → `desirable-difficulties_itow-introducing-desirable-difficulties-into-practice-and-instruction-bjork_s00_c02`
- Wood, Bruner & Ross (1976): 튜터의 역할 중 하나는 frustration control — "should be less dangerous or stressful with a tutor than without."
  → `scaffolding_child-psychology-psychiatry-april-1976-wood-the-role-of-tutoring-in-problem_s06_c01`
- TODO: verify against corpus chunk — 감정 및 동기 변수에 대한 체계적 이론은 현재 코퍼스에 포함된 논문 범위 밖. LLM 교육 리뷰(`llm-based-education_1-s20-s2666920x25001699-main_s24_c01`)에서 engagement 향상 효과가 언급되나 affective friction에 특화된 근거는 부족.

**Gonghaebun 개입**: 세션 시작 시 "현재 이 개념에서 어디서 막히나요?"를 묻는 진단 단계. 난이도를 prerequisite 단계부터 fading 방식으로 조정. 작은 성공(micro-win)을 STUDY.md에 명시적으로 기록.

---

## 요약 매트릭스

| Failure Mode | 학습자 경험 | 이론적 근거 | Gonghaebun 개입 |
|---|---|---|---|
| Representational Bottleneck | "정의를 모르겠다" | Ainsworth 2006 (DeFT) | 5가지 표현 강제 생성 |
| Prerequisite Graph Blindness | "뭘 먼저 알아야 하는지 모른다" | Novak 1990, Sweller 2019 | prerequisite graph |
| Schema Acquisition Failure | "증명을 따라가지만 못 쓴다" | Sweller 2019 (CLT) | proof schema 분해 |
| Metacognitive Failure | "공부한 것 같은데 틀린다" | Chi 1994, Bjork & Bjork | White Recall Loop |
| Affective Friction | "나는 수학 체질이 아닌가 봐" | Wood et al. 1976, Bjork & Bjork | 진단 + fading 난이도 |
