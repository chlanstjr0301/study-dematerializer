# 04. MVP 범위 — Real Analysis 도메인

## MVP 정의

**목표**: Gonghaebun의 핵심 루프(개념 입력 → 분해 → 표현 생성 → prerequisite graph → White Recall Loop → STUDY.md)가 실제로 작동하는 최소 버전.

**도메인**: Real Analysis (해석학)
**초기 개념**: compactness, connectedness, uniform continuity

---

## 도메인 선택 근거

| 기준 | Real Analysis가 적합한 이유 |
|---|---|
| 개념 간 dependency 명확 | compactness ← closed & bounded ← metric space ← completeness |
| 오개념 패턴이 잘 알려짐 | "compact = bounded", "연속 = uniformly continuous" 등 |
| 표현 다양성 | ε-δ, 수열 특성화, 위상적 특성화, Heine-Borel, 그림 모두 존재 |
| 증명 스키마가 뚜렷 | 표준 compact set 증명 구조 반복 사용 가능 |
| 학습자 고통 지점 명확 | 대학원 입시 수학 최빈출 실패 영역 |

---

## 초기 3개념 상세

### Concept 1: Compactness (옹골성)

**Formal 정의**: 위상 공간 X의 부분집합 K가 compact ⟺ K의 임의의 열린 덮개에 유한 부분 덮개가 존재한다.

**핵심 prerequisite 노드**:
- metric space (거리 공간)
- open set / closed set
- open cover (열린 덮개)
- Heine-Borel theorem (ℝⁿ 특수 케이스)
- sequential compactness (수열 특성화)

**주요 표현**:
1. `formal` — 위상적 정의
2. `intuitive` — "유한 개의 지역 정보로 전체를 덮을 수 있다"
3. `visual` — ℝ²에서 닫힌 유계 집합 vs 열린 집합 그림
4. `counterexample` — (0, 1)은 compact하지 않음 (열린 덮개 (1/n, 1) 유한 부분 덮개 없음)
5. `proof_schema` — "K가 compact임을 증명하라" 표준 구조

**알려진 오개념**:
- "compact = bounded" (반례: 이산 거리 공간에서 무한 집합)
- "closed → compact" (반례: ℝ 전체)
- "compact set의 부분집합은 compact" (반례: 열린 부분집합)

---

### Concept 2: Connectedness (연결성)

**Formal 정의**: 위상 공간 X가 connected ⟺ X를 두 개의 disjoint non-empty open set의 합집합으로 표현할 수 없다.

**핵심 prerequisite 노드**:
- open set / closed set
- separation (분리)
- path-connectedness (경로 연결성, 강한 조건)
- intermediate value theorem과의 관계

**주요 표현**:
1. `formal` — 분리 불가능 정의
2. `intuitive` — "한 점에서 다른 점으로 끊기지 않고 이동 가능"
3. `visual` — ℝ²에서 connected vs disconnected 집합 그림
4. `counterexample` — ℚ (유리수 집합)는 connected가 아님
5. `proof_schema` — "f가 connected set에서 연속이면 치역도 connected" 증명 구조

**알려진 오개념**:
- "path-connected = connected" (역방향은 거짓; topologist's sine curve)
- "connected의 여집합은 connected가 아님"

---

### Concept 3: Uniform Continuity (균등 연속성)

**Formal 정의**: f: X→Y가 uniformly continuous ⟺ ∀ε>0 ∃δ>0 s.t. d(x,y)<δ ⟹ d(f(x),f(y))<ε, 여기서 δ는 x에 무관.

**핵심 prerequisite 노드**:
- pointwise continuity (점별 연속성)
- ε-δ 언어와 quantifier 순서
- compact set에서 연속함수의 균등 연속성 정리

**주요 표현**:
1. `formal` — quantifier 순서 강조 정의
2. `intuitive` — "δ를 함수 전체에서 동시에 작동하도록 고를 수 있다"
3. `visual` — pointwise continuous vs uniformly continuous 그래프 비교
4. `counterexample` — f(x) = x²은 ℝ 전체에서 uniformly continuous하지 않음
5. `proof_schema` — compact set → uniform continuity 증명 구조

**알려진 오개념**:
- "연속 = uniformly continuous" (반례: f(x)=x² on ℝ)
- quantifier 순서 혼동: ∃δ∀x vs ∀x∃δ

---

## MVP 기능 경계

### In Scope (v1)

| 기능 | 설명 |
|---|---|
| 개념 입력 | 개념 이름 (예: "compactness") 입력 |
| Prerequisite graph 생성 | 선행 개념 DAG 생성, mastery_state 초기화 |
| 5가지 표현 생성 | formal, intuitive, visual (텍스트 설명), counterexample, proof_schema |
| 오개념 목록 생성 | 해당 개념의 알려진 오개념 패턴 |
| Self-explanation 프롬프트 | 각 표현 후 강제 서술 요청 |
| White Recall Loop | 세션 말미 자료 없는 인출 과제 |
| STUDY.md 업데이트 | mastery_state, next_review_date 기록 |

### Out of Scope (v1)

| 기능 | 이유 |
|---|---|
| 자동 채점 (수식 검증) | 수식 파서 복잡도, v2로 이연 |
| 실시간 그래프 시각화 | UI 의존성, v2로 이연 |
| 사용자 계정 / 진도 서버 동기화 | 로컬 STUDY.md로 충분, v2로 이연 |
| 문제 자동 생성 | 범위 과다, v2로 이연 |
| Real Analysis 외 도메인 | 초기 집중, v3으로 이연 |
| Knowledge tracing (BKT) | ITS 논문 청크 없음, 구현 복잡도 높음 |

---

## MVP 성공 기준

1. 3개 초기 개념 각각에 대해 5가지 표현이 정확하게 생성된다.
2. Prerequisite graph가 Real Analysis 교재(Rudin/Bartle 기준)와 일치한다.
3. STUDY.md가 세션 후 올바르게 업데이트된다.
4. White Recall Loop가 학습자의 자기 평가와 일치하는 gap을 식별한다.
5. 수학적 오류(잘못된 정의, 거짓 counterexample)가 없다.
