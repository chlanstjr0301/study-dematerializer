# 05. 사용자 세션 흐름 — Gonghaebun

## 세션 유형

| 유형 | 트리거 | 목적 |
|---|---|---|
| **New Concept Session** | 학습자가 새 개념 입력 | 개념 분해 + prerequisite graph 생성 |
| **Review Session** | STUDY.md의 next_review_date 도달 | White Recall Loop + mastery_state 업데이트 |
| **Deep Dive Session** | 학습자가 특정 표현/증명 요청 | 단일 표현 심화 또는 proof 워크스루 |

---

## New Concept Session 흐름

```
[1] 개념 입력
    └─ 학습자: "compactness를 공부하고 싶어요"

[2] 진단 단계 (Diagnostic)
    └─ 시스템: "이 개념에 대해 지금 알고 있는 것을 자유롭게 적어 주세요."
    └─ 시스템: "어디서 막히거나 헷갈리나요?"
    └─ → mastery_state 초기 추정치 설정

[3] Prerequisite Graph 생성
    └─ 선행 개념 DAG 자동 생성
    └─ 각 prerequisite에 대해 mastery_state 확인 질문
        예: "metric space에 대해 편안하게 말할 수 있나요?"
    └─ unknown 선행 개념 경고:
        "⚠️ open set의 mastery_state = unknown. 먼저 살펴볼까요?"
    └─ → 학습자 선택: 선행 개념 먼저 or 강행

[4] 분해 (Decomposition)
    └─ 표현 1: formal definition
        "ε-δ/위상적 정의 제시 + 기호 각 항목 설명"
    └─ Self-explanation 프롬프트:
        "이 정의에서 '열린 덮개'가 무엇인지 자신의 말로 써 보세요."
    └─ 표현 2: intuitive description
    └─ Self-explanation 프롬프트
    └─ 표현 3: visual (텍스트 기반 다이어그램 또는 그림 설명)
    └─ Self-explanation 프롬프트
    └─ 표현 4: counterexample
        "(0,1)이 compact하지 않음을 보이는 예 + why 설명"
    └─ Self-explanation 프롬프트
    └─ 표현 5: proof_schema
        "표준 compact set 증명의 뼈대 제시"

[5] 오개념 점검 (Misconception Check)
    └─ 시스템: "다음 중 맞는 것은? (MCQ 형식)"
        예: "compact set의 부분집합은 항상 compact하다 — 참/거짓?"
    └─ 즉각 피드백 + 반례 제시

[6] White Recall Loop
    └─ 시스템: "이제 교재를 덮고, compactness를 처음부터 설명해 보세요."
        - 정의를 쓰세요.
        - 직관을 설명하세요.
        - 반례를 하나 제시하세요.
        - 이 개념을 사용하는 증명의 첫 단계는 무엇인가요?
    └─ LLM이 응답을 평가:
        - 정확한 항목: ✓
        - 누락된 추론: "이 부분이 빠졌어요: ..."
        - 오류: "이 주장은 틀렸어요: ..." + 반례

[7] STUDY.md 업데이트
    └─ mastery_state per representation 업데이트
    └─ 확인된 오개념 기록
    └─ next_review_date 설정 (1일 후)
    └─ prerequisite_status 업데이트

[8] 세션 요약
    └─ "오늘 다룬 내용: compactness (5개 표현)"
    └─ "다음 복습: [날짜]"
    └─ "남은 선행 개념: open set (unknown)"
```

---

## Review Session 흐름

```
[1] STUDY.md에서 오늘 복습 대상 개념 로드
    └─ next_review_date ≤ today인 개념 목록

[2] White Recall Loop (자료 없이)
    └─ "지난번에 compactness를 배웠어요. 지금 정의를 써 주세요."
    └─ mastery_state = unknown인 표현 우선 대상

[3] 응답 평가
    └─ 성공: mastery_state 상승, next_review_date = 3일 후
    └─ 부분: 해당 표현 재학습 + next_review_date = 1일 후
    └─ 실패: 해당 표현 전체 재분해 + next_review_date = 당일

[4] STUDY.md 업데이트
```

---

## Deep Dive Session 흐름

```
[1] 학습자 요청
    예: "compactness의 proof_schema를 더 자세히 보고 싶어요"

[2] 해당 표현 + schema 로드
    └─ 현재 mastery_state 확인

[3] Scaffolded walkthrough
    └─ mastery_state = unknown → 전체 스키마 제시 + 단계별 설명
    └─ mastery_state = partial → 빈 칸 채우기 형식
    └─ mastery_state = solid → 변형 문제 제시 (예: 다른 compact set에 적용)

[4] Self-explanation + 피드백

[5] STUDY.md 업데이트 (해당 표현의 mastery_state만)
```

---

## 세션 상태 전이도

```
                    [New Concept Session]
                           │
                    첫 White Recall Loop
                           │
              ┌────────────┴────────────┐
          성공 (≥3/5)               부분/실패
              │                        │
    mastery_state 상승         mastery_state 유지/하락
    next_review = 3일           next_review = 1일
              │                        │
              └────────────┬───────────┘
                    [Review Session]
                    (STUDY.md 기반)
```

---

## UX 원칙

1. **학습자가 항상 주도**: LLM은 제안하고, 학습자는 다음 단계를 선택한다.
2. **짧은 세션 가능**: 각 세션은 독립적으로 완결될 수 있어야 한다 (15-30분).
3. **진도가 보인다**: 세션 시작과 끝에 prerequisite graph 상태 변화를 요약한다.
4. **오류는 즉시 교정**: 학습자의 self-explanation 오류에 즉각 피드백.
5. **강요하지 않는다**: 선행 개념 경고는 강제 우회가 아닌 권장.
