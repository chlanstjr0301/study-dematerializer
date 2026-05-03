# 00. 비전 — 공부 해체 분석기 (Gonghaebun)

## 제품 이름

**공부 해체 분석기 (Gonghaebun)**
— "공부를 해체하여 다시 조립하는 AI 컴파일러"

## 한 줄 정의

> 어려운 수학/과학 개념을 입력하면, AI가 선행지식 그래프·다중 표현·증명 스키마·오개념 점검·인출 훈련을 통해 **개념을 완전히 소화 가능한 단위로 분해**하고, 학습자의 `STUDY.md`에 누적 지식을 기록하는 **AI 공부 컴파일러**다.

## 제품 범주

- **아님**: 범용 챗봇, AI 튜터, 요약 도구
- **맞음**: AI study compiler — 개념 분해 + 표현 합성 + 인출 루프를 실행하는 학습 파이프라인

## 핵심 가치 제안

| 사용자 고통 | Gonghaebun의 응답 |
|---|---|
| "정의는 읽었는데 무슨 뜻인지 모르겠다" | 정의를 5가지 표현으로 재구성 |
| "이 개념을 이해하려면 뭘 먼저 알아야 하는지 모른다" | prerequisite graph 자동 생성 |
| "증명 구조가 안 보인다" | proof schema 분해 |
| "공부한 것 같은데 시험에서 틀린다" | White Recall Loop로 인출 훈련 |
| "오늘 뭘 공부했는지 흐릿하다" | STUDY.md에 mastery_state 누적 기록 |

## 목표 사용자

**Primary**: 대학원 진학 준비 중이거나 혼자 해석학을 공부하는 학부 3-4학년
- 교재(Rudin, Bartle 등)를 읽지만 개념 간 연결이 끊기는 경험
- 문제는 풀 수 있어도 "왜"를 설명 못하는 상태

**Secondary**: 경쟁시험(대학원 입시, 수학올림피아드) 준비생

## MVP 도메인

**Real Analysis** — 해석학
- 초기 3개념: compactness, connectedness, uniform continuity
- 이유: 개념 간 dependency가 명확하고, 오개념 패턴이 잘 알려져 있으며, 표현의 다양성이 풍부함

## 장기 비전

1. **v1** — Real Analysis 단일 도메인, CLI/웹 인터페이스, STUDY.md 출력
2. **v2** — 사용자별 prerequisite graph 누적, knowledge tracing 도입
3. **v3** — 다중 도메인 확장 (Abstract Algebra, Topology, Probability)
4. **v4** — 협업 학습 그래프 (여러 사용자의 STUDY.md 비교)

## 비설계 범위 (Out of Scope)

- 문제 자동 생성 채점 시스템 (v1)
- 실시간 음성 인터페이스 (v1)
- 일반 교육과정 (초중고 수준) 지원 (v1)
- 사용자 인증 / 소셜 기능 (v1)
