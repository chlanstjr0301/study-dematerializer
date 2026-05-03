# 03. 제품 원칙 — Gonghaebun 설계 지침

이 원칙들은 `02_research_basis.md`의 이론 근거에서 도출되며,
구체적인 기능 결정 시 우선순위를 정하는 기준이 된다.

---

## 원칙 1: 다중 표현 우선 (Multiple Representations First)

**선언**: 어떤 개념도 단일 표현으로만 제시되어서는 안 된다.

**운용 규칙**:
- 모든 개념에 대해 최소 **5가지 표현 유형**을 생성한다:
  1. `formal` — ε-δ 정의, 집합론적 기술
  2. `intuitive` — 비유, 일상 언어 설명
  3. `visual` — 그림, 위상 다이어그램, 수직선 예시
  4. `counterexample` — "이것은 compact하지 않다"의 구체적 예
  5. `proof_schema` — 해당 개념을 사용하는 증명의 구조적 뼈대
- 표현 간 **번역 태스크**를 포함한다 (예: "formal 정의를 intuitive 언어로 다시 써 보세요").

**근거**: Ainsworth 2006 DeFT framework — complementing, constraining, constructing deeper understanding.
→ `multiple-representations_ainsworth-2006-learning-and-instruction_s12_c01`, `s16_c01`

---

## 원칙 2: 인지 부하 통제 (Cognitive Load Control)

**선언**: 개념 분해의 순서는 학습자의 working memory 용량을 초과하지 않도록 설계한다.

**운용 규칙**:
- **Isolated elements first**: 상호작용 요소가 적은 정의·기본 속성을 먼저 제시한다.
- **Worked schema before problem-solving**: 초보자에게는 증명 구조 전체를 먼저 보여준다.
- **No split attention**: 텍스트와 시각 자료를 물리적으로 통합하여 제시한다.
- **Expertise fading**: mastery_state가 높아질수록 지원 정보를 줄인다.

**근거**: Sweller et al. 2019 — element interactivity, expertise reversal, isolation effect.
→ `cognitive-load-theory_s10648-019-09465-5_s03_c03`, `s03_c14`, `s03_c16`

---

## 원칙 3: 선행지식 그래프 명시 (Explicit Prerequisite Graph)

**선언**: 모든 개념 학습은 prerequisite graph를 참조하여 진행된다.

**운용 규칙**:
- 개념 입력 시 **prerequisite graph**를 자동 생성한다.
- 각 prerequisite 노드는 mastery_state를 가진다: `unknown` | `partial` | `solid`.
- `unknown` 선행 개념이 존재하면 학습자에게 경고하고 해당 개념을 먼저 다루도록 권장한다.
- 그래프는 학습 진행에 따라 갱신되며 STUDY.md에 반영된다.

**근거**: Novak 1990 (concept mapping); Sweller 2019 (element interactivity와 선행 지식의 관계).
→ `concept-mapping_novak1990_s00_c01`, `cognitive-load-theory_s10648-019-09465-5_s03_c12`

---

## 원칙 4: 스캐폴딩과 자율성 균형 (Scaffolding with Fading)

**선언**: 지원은 학습자가 스스로 할 수 없는 부분만 채우며, 자립을 목표로 감소한다.

**운용 규칙**:
- 새 개념: 전체 proof schema + 단계별 힌트 제공.
- mastery_state = `partial`: proof schema는 제공하되 개별 단계 힌트는 요청 시에만.
- mastery_state = `solid`: 빈 틀만 제공하고 학습자가 스스로 채우게 한다.
- LLM의 역할: 답을 주는 것이 아니라 **"다음에 무엇을 생각해야 하는지"를 묻는 것**.

**근거**: Wood, Bruner & Ross 1976 — scaffolding의 핵심은 task reduction과 frustration control, 의존성 위험 경계.
→ `scaffolding_child-psychology-psychiatry-april-1976-wood-the-role-of-tutoring-in-problem_s03_c01`, `s06_c01`

---

## 원칙 5: 자기 설명 강제 (Self-Explanation Prompting)

**선언**: 학습자가 자료를 받은 후 반드시 자신의 말로 설명하는 단계를 거친다.

**운용 규칙**:
- 각 표현 노출 후: "이 내용을 자신의 말로 설명해 보세요 (교재 보지 말고)."
- 증명 스키마 학습 후: "이 증명의 핵심 아이디어는 무엇인가요?"
- LLM은 설명의 정확성을 평가하고, 누락된 추론 단계를 지적한다.

**근거**: Chi et al. 1994 — prompting self-explanation improves understanding, even without explicit instruction.
→ `self-explanation-effect_cognitive-science-july-1994-chi-eliciting-selfexplanations-improves-underst_s00_c01`, `s05_c02`

---

## 원칙 6: 인출 연습과 간격 반복 (Retrieval Practice + Spaced Repetition)

**선언**: 모든 학습 세션은 인출 태스크로 끝나며, STUDY.md는 다음 복습 일정을 기록한다.

**운용 규칙**:
- **White Recall Loop**: 세션 말미에 자료 없이 개념을 처음부터 서술하게 한다.
- 퀴즈 → 즉각 피드백 → 오답 개념 재학습 사이클.
- STUDY.md에 `next_review_date`를 기록하고, 다음 세션 시작 시 우선 인출 과제를 제시한다.
- Spacing 간격: 1일 → 3일 → 7일 → 21일 (초기 기본값; 추후 조정 가능).

**근거**: Roediger et al. 2011 — quizzing produces letter-grade improvement maintained months.
→ `retrieval-practice_roediger-agarwal-etal-2011-jepa_s04_c01`
Bjork & Bjork — storage strength vs retrieval strength distinction.
→ `desirable-difficulties_itow-introducing-desirable-difficulties-into-practice-and-instruction-bjork_s00_c03`

---

## 원칙 7: Representation-Specific Mastery State

**선언**: 개념의 이해는 표현 유형별로 독립적으로 추적된다.

**운용 규칙**:
- 하나의 개념은 5가지 표현 각각에 대해 별도의 mastery_state를 가진다.
- 예: compactness에 대해 `formal: solid`, `visual: partial`, `proof_schema: unknown`.
- 종합 mastery_state는 개별 표현 mastery_state의 가중 평균이 아니라 **최솟값(weakest link)**으로 정의된다.

**근거**: Ainsworth 2006 — learners can fail in relation to one representation while succeeding with another; DeFT framework emphasizes different cognitive tasks per representation.
→ `multiple-representations_ainsworth-2006-learning-and-instruction_s07_c01`, `s18_c01`

---

## 원칙 8: STUDY.md는 단일 진실 원천 (STUDY.md as Single Source of Truth)

**선언**: 학습자의 모든 진도, 오개념, 복습 일정은 STUDY.md 파일에 기록된다.

**운용 규칙**:
- STUDY.md는 사람이 읽을 수 있는 Markdown 포맷.
- 각 개념에 대한 항목: concept / mastery_state / representations / prerequisite_status / next_review_date / misconceptions / notes.
- 세션 종료 시 자동 업데이트.
- 외부 DB 없이도 동작 가능한 파일 기반 설계 (v1).

**근거**: 이 원칙은 product 설계 결정으로, 직접적 논문 근거는 없음. knowledge tracing의 외부화 개념에서 영감 (TODO: Corbett & Anderson 1995 검증 후 연결).

---

## 원칙 우선순위

학습자 경험이 원칙들 사이에서 충돌할 때의 우선순위:

```
(높음) Multiple Representations
      Cognitive Load Control
      Prerequisite Graph
      Scaffolding + Fading
      Self-Explanation
      Retrieval Practice
(낮음) STUDY.md 자동화 편의성
```

편의 기능은 학습 효과를 훼손해서는 안 된다.
