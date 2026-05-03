# 02. 연구 근거 — 코퍼스 기반 이론 매핑

이 문서는 `docs/brainstorming/paper-corpus/` 코퍼스에서 직접 읽은 chunk 텍스트를 근거로
Gonghaebun의 핵심 설계 주장에 대응하는 이론적 증거를 정리한다.

> **표기 규칙**
> - `[chunk_id]` — 코퍼스에서 직접 확인한 chunk
> - `TODO: verify` — 코퍼스에 해당 논문이 있으나 chunk가 없거나, 내용이 확인되지 않음

---

## 1. Cognitive Load Theory (Sweller et al. 2019)

**paper_id**: `cognitive-load-theory_s10648-019-09465-5`

### 핵심 주장과 chunk 근거

**주장 1**: 학습 과제의 element interactivity(요소 상호작용 수)가 working memory 부하를 결정한다.
> "Cognitive load theory aims to explain how the information processing load induced by learning tasks can affect students' ability to process new information"
> [`cognitive-load-theory_s10648-019-09465-5_s03_c01`]

**주장 2**: Split-attention effect — 공간적으로 분리된 정보 원천은 working memory를 과부하시킨다.
> "Replace multiple sources of information, distributed either in space (spatial split attention) or time (temporal split attention), with one integrated source of information."
> [`cognitive-load-theory_s10648-019-09465-5_s03_c05`]

**주장 3**: 초보 학습자에게는 worked examples가 문제 풀기보다 효과적이다 (expertise reversal effect).
> "Worked examples benefit novices. With increasing knowledge, practice at solving problems becomes increasingly important rather than having negative effects."
> [`cognitive-load-theory_s10648-019-09465-5_s03_c14`]

**주장 4**: 고립된 요소 먼저 제시 → 통합 제시 순서가 전체 반복 제시보다 우월.
> "Learners presented all of the information twice were unable to process it properly on either occasion due to an excessive working memory load. In contrast, learners only presented the isolated elements could easily process them."
> [`cognitive-load-theory_s10648-019-09465-5_s03_c16`]

**주장 5**: 학습자가 높은 인지 부하를 "많이 배웠다"는 신호로 오해할 수 있다.
> "a learner who is solving a conventional problem using means-ends-analysis may use the high cognitive load as an invalid cue for learning"
> [`cognitive-load-theory_s10648-019-09465-5_s04_c03`]

**설계 함의**: Gonghaebun은 개념 분해 시 isolated elements → integrated view 순서를 따르고, 초보자에게 worked proof schema를 먼저 제시한다.

---

## 2. Multiple Representations — DeFT Framework (Ainsworth 2006)

**paper_id**: `multiple-representations_ainsworth-2006-learning-and-instruction`

### 핵심 주장과 chunk 근거

**주장 1**: 다중 표현의 효과는 자동이 아니며, 세 가지 함수(complementing, constraining, constructing deeper understanding)로 분류된다.
> "Multiple (external) representations can provide unique benefits when people are learning complex new ideas. Unfortunately, many studies have shown this promise is not always achieved."
> [`multiple-representations_ainsworth-2006-learning-and-instruction_s01_c01`]

**주장 2**: 표현을 이해하기 위해 학습자는 format, operators, relation-to-domain을 모두 학습해야 한다.
> "Learners must know how a representation encodes and presents information (the 'format'). [...] They must also learn what the 'operators' are for a given representation."
> [`multiple-representations_ainsworth-2006-learning-and-instruction_s07_c01`]

**주장 3**: 학습자는 표현 간 번역을 어려워하며, 이것이 다중 표현의 실패 원인이다.
> "a very large number of studies have observed that learners find translating between representations difficult"
> [`multiple-representations_ainsworth-2006-learning-and-instruction_s18_c01`]

**주장 4**: 다중 표현이 deeper understanding을 구성할 때, 그 이해는 새로운 상황에 전이될 가능성이 높다.
> "Multiple representations support the construction of deeper understanding when learners integrate information from MERs to achieve insight that would be difficult to achieve with only a single representation. Furthermore, insight achieved in this way increases the likelihood that it will be transferred to new situations."
> [`multiple-representations_ainsworth-2006-learning-and-instruction_s16_c01`]

**주장 5**: 학습자에게 표현을 통합하도록 강제하는 활동이 분리 제시보다 우월.
> "learners did better when required to integrate representations"
> [`multiple-representations_ainsworth-2006-learning-and-instruction_s22_c04`]

**설계 함의**: Gonghaebun은 표현을 병렬로 보여주는 데 그치지 않고, 학습자가 표현 간 **번역 작업**을 수행하는 태스크를 포함한다.

---

## 3. Retrieval Practice — Testing Effect (Roediger & Karpicke 2006; Roediger et al. 2011)

**paper_id**: `retrieval-practice_2006-roediger-karpicke-psychsci`, `retrieval-practice_roediger-agarwal-etal-2011-jepa`

### 핵심 주장과 chunk 근거

**주장 1**: 시험/인출 행위 자체가 기억을 강화한다 (testing effect).
> "Taking a memory test not only assesses what one knows, but also enhances later retention, a phenomenon known as the testing effect."
> [`retrieval-practice_2006-roediger-karpicke-psychsci_s00_c01`]

**주장 2**: 반복 읽기보다 퀴즈가 실제 교실 환경에서도 우월하다.
> "Repeated quizzing led to better performance than did repeated reading."
> [`retrieval-practice_roediger-agarwal-etal-2011-jepa_s04_c01`]

**주장 3**: 퀴즈 효과는 한 학년도 동안 유지되며 letter grade 수준의 향상을 만든다.
> "Three experiments showed retrieval practice (testing) effects in middle school classrooms with actual course content, effects that lifted students' performance by a letter grade and that were maintained for several months."
> [`retrieval-practice_roediger-agarwal-etal-2011-jepa_s04_c01`]

**주장 4**: 피드백이 있는 경우 testing effect가 강화된다.
> "the power of testing seems to increase with the number of tests taken and also when tests are followed by feedback"
> [`retrieval-practice_roediger-agarwal-etal-2011-jepa_s00_c03`]

**설계 함의**: White Recall Loop는 이 증거에 직접 기반한다. 각 세션 말미에 인출 과제를 수행하고, LLM이 피드백을 제공한다.

---

## 4. Desirable Difficulties (Bjork & Bjork)

**paper_id**: `desirable-difficulties_itow-introducing-desirable-difficulties-into-practice-and-instruction-bjork`

### 핵심 주장과 chunk 근거

**주장 1**: 학습에 유익한 조건(spacing, interleaving, retrieval practice)은 학습 중 수행을 저해하기 때문에 학습자와 교사 모두 잘못 판단하기 쉽다.
> "desirable difficulties are still difficulties from a learner's standpoint, and doing anything that might impair one's performance during the learning process is not very appealing"
> [`desirable-difficulties_itow-introducing-desirable-difficulties-into-practice-and-instruction-bjork_s00_c02`]

**주장 2**: Storage strength와 retrieval strength는 독립적이다. 빠른 인출 성공이 장기 기억을 보장하지 않는다.
> "If something is well learned and frequently accessed [...] that address has both high storage strength and high retrieval strength"
> [`desirable-difficulties_itow-introducing-desirable-difficulties-into-practice-and-instruction-bjork_s00_c03`]

**주장 3**: Massed study는 빠른 수행 향상처럼 보이지만 장기 파지를 저해한다.
> "their opposites (such as massing or blocking of study or practice trials) often make performance improve rapidly and can appear to be enhancing learning"
> [`desirable-difficulties_itow-introducing-desirable-difficulties-into-practice-and-instruction-bjork_s00_c04`]

**설계 함의**: Gonghaebun은 같은 개념을 간격을 두고 반복하는 spaced retrieval 세션을 STUDY.md scheduling에 반영한다.

---

## 5. Scaffolding (Wood, Bruner & Ross 1976)

**paper_id**: `scaffolding_child-psychology-psychiatry-april-1976-wood-the-role-of-tutoring-in-problem`

### 핵심 주장과 chunk 근거

**주장 1**: 효과적인 튜터는 과제를 학습자가 "fit"을 인식할 수 있는 수준으로 축소한다.
> "'scaffolding' tutor fills in the rest and leaves the learner to carry out only those acts of which he/she is capable."
> [`scaffolding_child-psychology-psychiatry-april-1976-wood-the-role-of-tutoring-in-problem_s03_c01`]

**주장 2**: 튜터의 핵심 기능 중 하나는 frustration control.
> "should be less dangerous or stressful with a tutor than without"
> [`scaffolding_child-psychology-psychiatry-april-1976-wood-the-role-of-tutoring-in-problem_s06_c01`]

**주장 3**: 과도한 튜터 의존이 가장 큰 위험이다.
> "The major risk is in creating too much dependency on the tutor."
> [`scaffolding_child-psychology-psychiatry-april-1976-wood-the-role-of-tutoring-in-problem_s06_c01`]

**설계 함의**: Gonghaebun의 scaffolding은 **fading 원칙**을 따른다 — 학습자 mastery_state가 높아질수록 힌트와 스키마 지원을 줄인다.

---

## 6. Self-Explanation Effect (Chi et al. 1994)

**paper_id**: `self-explanation-effect_cognitive-science-july-1994-chi-eliciting-selfexplanations-improves-underst`

### 핵심 주장과 chunk 근거

**주장 1**: Self-explaining은 새로운 정보를 기존 지식과 통합하는 과정을 촉진한다.
> "Learning involves the integration of new information into existing knowledge. Generating to oneself (self-explaining) facilitates that integration process."
> [`self-explanation-effect_cognitive-science-july-1994-chi-eliciting-selfexplanations-improves-underst_s00_c01`]

**주장 2**: 자발적 self-explanation이 적은 학습자도, 명시적 프롬프트를 받으면 이해가 향상된다.
> "the greater gain was obtained by merely eliciting self-explanations; no ex[tensive instruction needed]"
> [`self-explanation-effect_cognitive-science-july-1994-chi-eliciting-selfexplanations-improves-underst_s05_c02`]

**주장 3**: High explainers는 텍스트를 다시 참조할 필요가 없었다 — 이해의 내면화를 시사.
> "High explainers, on average, referred to the text for only 2 of the 54 posttest questions"
> [`self-explanation-effect_cognitive-science-july-1994-chi-eliciting-selfexplanations-improves-underst_s05_c06`]

**설계 함의**: 각 표현 노출 후 "이걸 자신의 말로 설명해 보세요" 프롬프트를 삽입한다.

---

## 7. LLM in Education (Shi et al. 2025; Xu et al. 2024)

**paper_id**: `llm-based-education_1-s20-s2666920x25001699-main`, `llm-based-education_240513001v1`

### 핵심 주장과 chunk 근거

**주장 1**: LLM 기반 intelligent tutoring systems는 실시간, context-aware 학습 안내를 제공할 수 있다.
> "These systems are characterized by dynamic adaptability, offering real-time, context-aware learning guidance"
> [`llm-based-education_1-s20-s2666920x25001699-main_s21_c01`]

**주장 2**: Hallucination과 over-reliance가 가장 빈번하게 보고된 위험이다.
> "technical reliability and hallucination emerged as the most frequently discussed challenges (n = 28), followed by over-reliance (n = 17)"
> [`llm-based-education_1-s20-s2666920x25001699-main_s15_c01`]

**주장 3**: LLM은 task completion aid가 아닌 knowledge construction support로 사용되어야 한다.
> "LLMs function as powerful learning support tools rather than serving as task completion aids"
> [`llm-based-education_1-s20-s2666920x25001699-main_s20_c01`]

**설계 함의**: Gonghaebun은 LLM이 답을 대신 쓰는 것이 아니라, 학습자의 자기 설명·인출·오류 수정을 돕는 역할로 제한한다.

---

## 8. TODO 목록 — 검증 필요 항목

| 항목 | 이유 | 우선순위 |
|---|---|---|
| Knowledge tracing / BKT | `intelligent-tutoring-systems_893corbettanderson1995` — needs_ocr, 0 chunks | High |
| Example-based learning / worked examples (Renkl) | `example-based-learning_ayres2012` mislabeled — 실제 내용은 Watson 전기 | High |
| Schema acquisition failure 명칭 | 코퍼스 어느 논문도 이 용어를 직접 사용하지 않음 | Medium |
| Affective friction 이론적 근거 | 현재 코퍼스에 감정/동기 전문 논문 없음 | Medium |
| Concept mapping → prerequisite graph 변환 | Novak (1990) chunks에 그래프 구조 상세 없음 | Low |
