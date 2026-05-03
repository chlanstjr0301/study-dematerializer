# 09. 위험 요소 및 가드레일

---

## R1: 수학적 환각 (Mathematical Hallucination)

**위험**: LLM이 틀린 정의, 존재하지 않는 반례, 논리적으로 결함 있는 proof schema를 생성.

**심각도**: 최고 (High) — 잘못된 수학은 학습자의 이해를 적극적으로 오염시킨다.

**발생 맥락**:
- 정확한 ε-δ 부등식 방향 혼동
- 반례가 실제로는 반례가 아닌 경우
- proof schema의 논리 순서 오류

**가드레일**:
1. **System prompt에 불확실성 표현 강제**: "확실하지 않으면 '이 부분은 교재에서 확인하세요'라고 말하라."
2. **전문가 검토 우선**: v1에서는 초기 3개 개념의 출력을 전수 수동 검토 후 배포.
3. **출력에 교재 참조 병기**: "이 정의는 Rudin Principles of Mathematical Analysis Ch.2를 기준으로 합니다."
4. **학습자에게 경고 배너**: 모든 LLM 생성 수학 내용에 "이 내용을 신뢰하기 전 교재에서 확인하세요" 표시.
5. TODO: 자동 수식 검증 (SymPy 또는 증명 보조기) — v2 목표.

**잔여 위험**: 미탐지 수학 오류는 v1에서 완전히 제거 불가. 전문가 검토로 최소화.

---

## R2: 과의존 (Over-Reliance)

**위험**: 학습자가 LLM 설명을 수동적으로 소비하고, 스스로 생각하는 능력을 기르지 못함.

**심각도**: 높음 (High) — 제품의 핵심 목표(자기 주도 이해)를 훼손.

**발생 맥락**:
- 어려운 단계에서 LLM에게 바로 답을 요청하는 패턴
- White Recall Loop를 건너뛰고 표현만 읽는 패턴

**근거**:
- Shi et al. 2025: over-reliance는 LLM 교육 적용의 두 번째로 빈번한 위험 (n=17).
  → `llm-based-education_1-s20-s2666920x25001699-main_s15_c01`
- Wood et al. 1976: "The major risk is in creating too much dependency on the tutor."
  → `scaffolding_child-psychology-psychiatry-april-1976-wood-the-role-of-tutoring-in-problem_s06_c01`

**가드레일**:
1. **White Recall Loop 필수화**: 각 세션에서 자료 없는 인출 없이 세션 완료 불가.
2. **"답 보여주기" 버튼 딜레이**: 학습자가 self-explanation 시도 없이 답을 볼 수 없도록.
3. **LLM은 질문으로 응답**: 학습자가 "이게 뭔가요?"라고 물으면 → "어디까지 이해했나요?"로 응답.
4. **STUDY.md에 의존 패턴 기록**: 세션에서 "힌트 요청" 횟수를 기록, 증가 추세면 학습자에게 알림.

---

## R3: 범위 외 요청 (Scope Creep Requests)

**위험**: 학습자가 Real Analysis 외 개념, 숙제 대신 풀기, 시험 예측 등을 요청.

**심각도**: 중간 (Medium).

**가드레일**:
1. **Stage 1 Concept Resolver에서 필터**: MVP 도메인 외 개념은 정중히 거부.
2. **숙제 대리 작성 방지**: "이 문제의 답을 써줘" → "이 문제를 풀기 위해 어떤 개념이 필요한가요?"로 전환.
3. **명확한 제품 설명**: 시작 화면에 "Gonghaebun은 개념 이해를 돕습니다. 숙제 답안을 제공하지 않습니다."

---

## R4: 선행 개념 무한 회귀 (Prerequisite Infinite Regress)

**위험**: prerequisite graph가 너무 깊어져 학습자가 "이걸 이해하려면 저걸 먼저, 저걸 이해하려면 그걸 먼저..." 무한 루프에 빠짐.

**심각도**: 중간 (Medium).

**가드레일**:
1. **최대 depth 3 제한**: Stage 2에서 depth > 3인 선행 개념은 "기본 배경 지식"으로 처리, 분해 생략.
2. **Minimum viable prerequisite**: 각 개념에 대해 "이 정도는 가정한다" 기준선 명시.
   예: compactness → "metric space에 대한 기본 친숙함은 가정합니다."
3. **학습자 선택권**: "선행 개념 먼저 vs. 현재 개념 강행" 학습자가 결정.

---

## R5: 오개념 강화 (Misconception Reinforcement)

**위험**: 시스템이 오개념을 "학습자가 점검해야 할 사항"으로 제시하다가, 표현 방식이 잘못되어 오개념을 강화함.

**심각도**: 높음 (High).

**가드레일**:
1. **오개념은 항상 "판단해 보세요" 형식**: 오개념을 사실처럼 서술 금지.
2. **정정은 즉각적이고 명확하게**: 오개념 MCQ 오답 → 즉시 반례 + 설명.
3. **Misconception prompt 전문가 검토**: v1에서는 3개 개념의 오개념 MCQ 전수 수동 검토.

---

## R6: STUDY.md 손상 (Data Corruption)

**위험**: STUDY.md가 잘못 파싱되거나 덮어써져 학습 기록이 손실됨.

**심각도**: 중간 (Medium).

**가드레일**:
1. **쓰기 전 백업**: STUDY.md 업데이트 전 `STUDY.md.bak` 생성.
2. **Append-only log**: 세션 요약을 STUDY.md 끝에만 추가하고, 기존 항목은 명시적 업데이트로만 변경.
3. **파싱 검증**: 업데이트 후 STUDY.md 재파싱하여 유효성 확인.

---

## R7: LLM 비용 폭주 (API Cost Explosion)

**위험**: 학습자가 같은 개념을 반복 요청하거나 긴 세션으로 API 비용 급증.

**심각도**: 낮음 (Low, v1 파일럿 단계).

**가드레일**:
1. **세션당 토큰 상한**: 최대 ~30,000 tokens/session.
2. **표현 캐싱 (v2)**: 동일 개념의 표현은 재생성 없이 캐시 사용.
3. **비용 모니터링**: 파일럿 기간 중 일별 API 비용 추적.

---

## 위험 요약 매트릭스

| 위험 | 심각도 | 가능성 | 우선 가드레일 |
|---|---|---|---|
| 수학적 환각 | High | High | 전문가 검토 + 불확실성 표현 강제 |
| 과의존 | High | Medium | White Recall 필수화 + LLM 질문 응답 |
| 오개념 강화 | High | Low | MCQ 형식 고정 + 즉각 정정 |
| 범위 외 요청 | Medium | Medium | Stage 1 필터 |
| 선행 개념 회귀 | Medium | Medium | depth 3 상한 |
| STUDY.md 손상 | Medium | Low | 백업 + 파싱 검증 |
| API 비용 폭주 | Low | Low | 토큰 상한 |
