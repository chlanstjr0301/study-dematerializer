# Decision Log — Gonghaebun Planning

의사결정 로그. 날짜 역순 정렬.

---

## DEC-007 | 2026-05-04

**결정**: STUDY.md를 유일한 영구 저장소로 사용 (v1)

**맥락**: DB 도입 시 배포 복잡도가 높아지고, MVP 단계에서 과도한 인프라.

**근거**: 파일 기반 설계는 사용자가 자신의 학습 데이터를 직접 소유하고 열람 가능. Git으로 버전 관리도 가능.

**대안 검토**:
- SQLite — 구조화된 쿼리 가능하지만 사람이 직접 읽기 어려움
- Markdown + JSON 혼합 — 복잡도 증가

**결론**: v1 = STUDY.md 단일 파일. v2에서 `sessions/` 디렉터리 및 SQLite 병행 검토.

---

## DEC-006 | 2026-05-04

**결정**: Representation-specific mastery_state 도입 (개념 전체가 아닌 표현별 추적)

**맥락**: 학습자가 formal definition은 외웠지만 proof_schema를 모르는 경우, 전체 mastery_state를 하나로 표현하면 gap을 숨김.

**근거**: Ainsworth 2006 — DeFT framework에서 각 표현은 서로 다른 인지 과제를 요구함.
→ `multiple-representations_ainsworth-2006-learning-and-instruction_s07_c01`, `s18_c01`

**대안 검토**:
- 개념 전체 단일 mastery_state — 단순하지만 gap 식별 불가
- 표현별 세분화 — 복잡하지만 정확한 진단

**결론**: 표현별 mastery_state 채택. 종합 mastery_state = weakest link.

---

## DEC-005 | 2026-05-04

**결정**: White Recall Loop를 모든 세션의 필수 단계로 설정

**맥락**: 학습자가 자료를 읽고 이해했다고 느끼지만 실제로는 illusion of knowing인 경우가 많음.

**근거**:
- Chi et al. 1994: prompting self-explanation improves understanding.
  → `self-explanation-effect_cognitive-science-july-1994-chi-eliciting-selfexplanations-improves-underst_s05_c02`
- Roediger et al. 2011: retrieval practice > repeated reading.
  → `retrieval-practice_roediger-agarwal-etal-2011-jepa_s04_c01`
- Sweller 2019: 높은 인지 부하를 학습의 증거로 오해.
  → `cognitive-load-theory_s10648-019-09465-5_s04_c03`

**대안 검토**:
- 선택적 White Recall — 학습자 자율에 맡기면 건너뛸 가능성 높음

**결론**: 필수 단계로 고정. 단 완전히 막히면 힌트 요청 허용.

---

## DEC-004 | 2026-05-04

**결정**: MVP 도메인을 Real Analysis로 한정

**맥락**: 개념 간 dependency가 명확하고, 오개념 패턴이 잘 알려져 있으며, 표현 다양성이 풍부함.

**대안 검토**:
- Linear Algebra — 시각 표현 풍부하지만 해석학보다 도메인 다양성 낮음
- Abstract Algebra — 선행 개념 구조 복잡, 표현 표준화 어려움
- Calculus — 너무 넓고 학습자 수준 다양

**결론**: Real Analysis (compactness, connectedness, uniform continuity) 로 시작.

---

## DEC-003 | 2026-05-04

**결정**: 5가지 표현 유형을 표준으로 고정 (formal, intuitive, visual, counterexample, proof_schema)

**맥락**: "몇 개의 표현이 필요한가"에 대한 이론적 최솟값을 결정해야 함.

**근거**: Ainsworth 2006 — DeFT framework에서 MER의 세 함수(complementing, constraining, constructing)를 모두 충족하려면 서로 다른 유형의 표현이 필요.
→ `multiple-representations_ainsworth-2006-learning-and-instruction_s12_c01`, `s15_c01`, `s16_c01`

**결론**: formal (constraining), intuitive (complementing), visual (complementing), counterexample (constraining), proof_schema (constructing deeper understanding). 5가지로 DeFT의 세 함수를 커버.

---

## DEC-002 | 2026-05-04

**결정**: prerequisite graph의 최대 depth를 3으로 제한

**맥락**: 무한 회귀를 방지하면서도 의미 있는 선행 개념을 포함해야 함.

**근거**: Sweller 2019 — element interactivity가 높을수록 학습 부하 급증.
이미 너무 많은 선행 개념이 드러나면 오히려 affective friction 유발.

**결론**: depth 1 (직접 선행), depth 2 (간접), depth 3 (배경 지식) 까지만. depth > 3 = "기본 배경 가정."

---

## DEC-001 | 2026-05-04

**결정**: v1에서 LLM API 호출 구현 제외 — 설계 단계만 완료

**맥락**: 현재 태스크는 product planning and system design only. 구현은 다음 단계.

**결론**: 이 planning 문서 세트 완성 후 구현 착수.

---

## 미결 결정 사항 (OPEN)

| ID | 질문 | 우선순위 | 담당 |
|---|---|---|---|
| OPEN-001 | LLM 모델 선택 (GPT-4o vs Claude vs Gemini) — 수학 정확성 벤치마크 필요 | High | — |
| OPEN-002 | White Recall Loop 평가에서 LLM 자동 채점의 신뢰도 | High | — |
| OPEN-003 | Spaced repetition 간격 알고리즘 (고정 1/3/7/21 vs SM-2) | Medium | — |
| OPEN-004 | ITS 논문 (Corbett & Anderson 1995) OCR 재처리 후 BKT 도입 여부 | Medium | — |
| OPEN-005 | 시각 표현을 텍스트 기반으로 유지할지 실제 이미지 생성으로 확장할지 | Low | — |
