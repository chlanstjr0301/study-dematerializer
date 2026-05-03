# 07. 데이터 모델

v1에서는 외부 DB 없이 **파일 기반** 설계를 따른다.
핵심 영구 저장소는 `STUDY.md` 하나이며, 세션 중 상태는 메모리(또는 임시 JSON)에 유지된다.

---

## 핵심 엔티티

### 1. Concept

학습 대상 개념의 정의.

```typescript
interface Concept {
  concept_id: string;          // "compactness", "connectedness"
  canonical_name: string;      // "Compactness"
  domain: string;              // "real_analysis"
  aliases: string[];           // ["compact set", "옹골성"]
  prerequisites: string[];     // concept_id 목록 (직접 선행만)
}
```

**저장**: 코드에 하드코딩 (MVP) 또는 `concepts.json` (v2).

---

### 2. PrerequisiteGraph

개념 간 의존 관계를 표현하는 DAG.

```typescript
interface PrerequisiteGraph {
  root_concept_id: string;
  nodes: PrerequisiteNode[];
  edges: PrerequisiteEdge[];
  generated_at: string;        // ISO 8601
}

interface PrerequisiteNode {
  concept_id: string;
  canonical_name: string;
  depth: number;               // 1 = 직접 선행, 2 = 간접 ...
  mastery_state: MasteryLevel;
}

interface PrerequisiteEdge {
  from: string;                // concept_id (선행)
  to: string;                  // concept_id (후행)
}

type MasteryLevel = "unknown" | "partial" | "solid";
```

**저장**: 세션 중 메모리. STUDY.md에 mastery_state만 기록.

---

### 3. RepresentationSet

하나의 개념에 대한 5가지 표현 묶음.

```typescript
interface RepresentationSet {
  concept_id: string;
  representations: {
    formal:          Representation;
    intuitive:       Representation;
    visual:          Representation;   // v1: 텍스트 기반
    counterexample:  Representation;
    proof_schema:    Representation;
  };
  generated_at: string;
  model_used: string;                  // 생성에 사용된 LLM 모델
}

interface Representation {
  type: RepresentationType;
  content: string;                     // Markdown 텍스트
  mastery_state: MasteryLevel;
  last_reviewed: string | null;        // ISO 8601
}

type RepresentationType =
  | "formal"
  | "intuitive"
  | "visual"
  | "counterexample"
  | "proof_schema";
```

**저장**: 세션 중 메모리. mastery_state만 STUDY.md에 기록.
캐싱: 동일 개념의 표현은 세션 간 재사용 가능 (v2에서 구현).

---

### 4. MisconcepionSet

개념에 대한 오개념 목록.

```typescript
interface MisconceptionSet {
  concept_id: string;
  misconceptions: Misconception[];
}

interface Misconception {
  id: string;                    // "compactness_m01"
  claim: string;                 // "compact set의 부분집합은 compact하다"
  is_correct: false;
  counterexample: string;        // "ℝ에서 (0,1)의 열린 부분집합..."
  explanation: string;
  checked_in_session: boolean;
  learner_was_correct: boolean | null;   // null = 아직 확인 안 됨
}
```

---

### 5. RecallAttempt

White Recall Loop의 개별 시도 기록.

```typescript
interface RecallAttempt {
  session_id: string;
  concept_id: string;
  representation_type: RepresentationType;
  learner_response: string;
  evaluation: RecallEvaluation;
  attempted_at: string;
}

interface RecallEvaluation {
  accuracy_score: number;         // 0.0 - 1.0
  missing_elements: string[];
  errors: string[];
  feedback: string;               // LLM 생성 피드백
}
```

**저장**: v1에서는 세션 중만 유지. 향후 STUDY.md 히스토리에 요약 추가.

---

### 6. StudySession

단일 학습 세션.

```typescript
interface StudySession {
  session_id: string;            // UUID
  session_type: "new_concept" | "review" | "deep_dive";
  concept_ids: string[];
  started_at: string;
  ended_at: string | null;
  recall_attempts: RecallAttempt[];
  mastery_updates: MasteryUpdate[];
}

interface MasteryUpdate {
  concept_id: string;
  representation_type: RepresentationType;
  before: MasteryLevel;
  after: MasteryLevel;
  next_review_date: string;      // ISO 8601
}
```

---

## STUDY.md 스키마

사람이 읽을 수 있는 Markdown. LLM과 코드 모두 파싱 가능한 구조.

```markdown
# STUDY.md
_last_updated: 2026-05-04_

---

## compactness

**domain**: real_analysis
**overall_mastery**: partial
**next_review**: 2026-05-07

### Representations

| type           | mastery | last_reviewed |
|----------------|---------|---------------|
| formal         | solid   | 2026-05-04    |
| intuitive      | partial | 2026-05-04    |
| visual         | unknown | —             |
| counterexample | solid   | 2026-05-04    |
| proof_schema   | unknown | —             |

### Prerequisites

| concept        | mastery | note |
|----------------|---------|------|
| metric_space   | solid   |      |
| open_set       | partial |      |
| open_cover     | unknown | ⚠️ 선행 필요 |

### Misconceptions Encountered

- [x] "compact = bounded" → 오개념 확인됨 (2026-05-04)
- [ ] "closed → compact" → 미확인

### Notes

> 열린 덮개 직관이 아직 약함. visual 표현 재학습 필요.

---

## connectedness

...
```

---

## 데이터 흐름 다이어그램

```
[학습자 입력]
      │
      ▼
[Concept Resolver] ──→ Concept (in-memory)
      │
      ▼
[Prerequisite Graph Builder] ──→ PrerequisiteGraph (in-memory)
      │  reads ←──────────────────────── STUDY.md
      ▼
[Representation Generator] ──→ RepresentationSet (in-memory)
      │
      ▼
[Misconception Checker] ──→ MisconceptionSet (in-memory)
      │
      ▼
[Self-Explanation Evaluator] ──→ RecallEvaluation (in-memory)
      │
      ▼
[White Recall Orchestrator] ──→ RecallAttempt[] (in-memory)
      │
      ▼
[STUDY.md Writer] ──────────→ STUDY.md (영구 저장)
                    writes ─────────────────────────────→ STUDY.md
```

---

## v1 제약

- **단일 사용자**: 사용자별 STUDY.md 분리 없음.
- **단일 도메인**: real_analysis만 지원.
- **파일 충돌**: STUDY.md 동시 쓰기 보호 없음 (단일 프로세스 가정).
- **표현 캐싱 없음**: 매 세션마다 LLM 재생성.

---

## v2 확장 고려사항

- `concepts.json` — 개념 DB 외부화
- `sessions/` 디렉터리 — 세션별 JSON 저장
- `graph.json` — 전체 prerequisite graph 영구 저장
- 표현 캐시 — 동일 개념의 표현 재사용
- Knowledge tracing (BKT) — mastery_state 추정 고도화
  (TODO: `intelligent-tutoring-systems_893corbettanderson1995` 검토 후 설계)
