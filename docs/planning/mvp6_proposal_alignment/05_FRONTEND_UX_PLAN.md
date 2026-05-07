# 05 — Frontend UX Plan

## Purpose

Define all frontend changes for MVP6: new components, page modifications, API client
updates, layout changes, and browser smoke checklist.

---

## Current Frontend Files (Inspection Targets)

| File | Lines | Purpose |
|------|-------|---------|
| `apps/web/src/pages/StudySession.tsx` | 406 | 6-step study session page |
| `apps/web/src/components/study/StudyStepper.tsx` | 44 | Step progress indicator |
| `apps/web/src/components/study/DiagnosisStep.tsx` | ~80 | Step 1 |
| `apps/web/src/components/study/PrerequisiteStep.tsx` | ~60 | Step 2 |
| `apps/web/src/components/study/RepresentationStep.tsx` | ~80 | Step 3 |
| `apps/web/src/components/study/MisconceptionStep.tsx` | ~60 | Step 5 (will be step 5 in MVP6) |
| `apps/web/src/components/study/WhiteRecallStep.tsx` | ~80 | Step 6 (will be step 6 in MVP6) |
| `apps/web/src/components/study/SessionSummaryStep.tsx` | ~60 | Step 7 (will be step 7 in MVP6) |
| `apps/web/src/api/client.ts` | 202 | Fetch-based API wrapper |
| `apps/web/src/api/types.ts` | 419 | TypeScript interfaces |
| `apps/web/src/App.tsx` | ~50 | Route definitions |
| `apps/web/src/components/Layout.tsx` | ~40 | Nav bar |

---

## New Components

### 1. MappingCheckStep.tsx

**Location**: `apps/web/src/components/study/MappingCheckStep.tsx`

**Purpose**: Display 3 mapping tasks sequentially. Learner submits answer for each.
After all 3 submitted, auto-advances to misconception step.

**Props**:
```typescript
interface MappingCheckStepProps {
  sessionId: string;
  tasks: MappingTaskItem[];
  results: MappingResultItem[];  // Already submitted (for read-only mode)
  confusionMap: ConfusionMapData | null;
  readOnly: boolean;
  onTaskSubmit: (taskId: string, response: string) => Promise<MappingSubmitResult>;
  onAllComplete: () => void;
}
```

**UI Layout**:
```
┌─────────────────────────────────┬──────────────────────────┐
│ 매핑 과제 (3/3)                 │ 혼동 지도                 │
│                                 │                          │
│ ┌─────────────────────────────┐ │ 선행 개념:               │
│ │ 과제 1: Formal → 반례       │ │ ○ metric_space: unknown  │
│ │                             │ │ ○ open_cover: unsure     │
│ │ 옹골성의 정의를 사용하여     │ │                          │
│ │ (0,1)이 왜 compact하지      │ │ 매핑 결과:               │
│ │ 않은지 설명하세요.          │ │ ✗ formal → 반례: 실패    │
│ │                             │ │ ✓ 반례 → formal: 통과    │
│ │ ┌───────────────────────┐   │ │ ○ formal+CE → 증명: 미제출│
│ │ │ [답변 입력 textarea]  │   │ │                          │
│ │ │                       │   │ │ 오개념:                  │
│ │ │                       │   │ │ • misuses_heine_borel    │
│ │ └───────────────────────┘   │ │                          │
│ │                             │ │ 다음 인출 과제:          │
│ │ [제출하기]                  │ │ • open cover로 (0,1)이   │
│ └─────────────────────────────┘ │   compact하지 않음을 ...  │
│                                 │                          │
│ ── 피드백 (제출 후) ──          │                          │
│ Score: 0.3 | 실패               │                          │
│ 누락: open cover, finite sub... │                          │
│ 오개념: Heine-Borel 오용        │                          │
│ 피드백: "open cover로 직접..."  │                          │
└─────────────────────────────────┴──────────────────────────┘
```

**State Management**:
```typescript
const [currentTaskIndex, setCurrentTaskIndex] = useState(0);
const [responses, setResponses] = useState<Record<string, string>>({});
const [results, setResults] = useState<MappingResultItem[]>([]);
const [submitting, setSubmitting] = useState(false);
```

**Behavior**:
1. Display one task at a time (tabs or sequential cards)
2. Textarea for learner response (min 10 chars to submit)
3. On submit: call `onTaskSubmit(taskId, response)` → show feedback inline
4. After feedback shown: enable "다음 과제" button
5. After all 3 submitted: show summary, enable "다음 단계" button → call `onAllComplete()`
6. Read-only mode: show all results, no edit

**Loading/Error/Empty States**:
- Loading: "매핑 과제를 불러오는 중..." spinner
- Error: "과제를 불러올 수 없습니다. 다시 시도해 주세요."
- Empty (no tasks): should not happen if card exists; show error

---

### 2. ConfusionMapPanel.tsx

**Location**: `apps/web/src/components/study/ConfusionMapPanel.tsx`

**Purpose**: Display the current confusion map state as a side panel.
Updated after every step and mapping submission.

**Props**:
```typescript
interface ConfusionMapPanelProps {
  confusionMap: ConfusionMapData | null;
  loading: boolean;
}
```

**UI Layout**:
```
┌──────────────────────────┐
│ 혼동 지도                 │
│ (마지막 갱신: mapping)     │
│                          │
│ ── 선행 개념 ──           │
│ ● metric_space: known    │
│ ○ open_cover: unsure     │
│ ○ heine_borel: known     │
│                          │
│ ── 매핑 연결 ──           │
│ ✗ formal → 반례  (0.3)   │
│ ✓ 반례 → formal  (0.8)   │
│ ○ formal+CE → 증명 (—)   │
│                          │
│ ── 활성 오개념 ──         │
│ • misuses_heine_borel    │
│ • bounded_implies_compact│
│                          │
│ ── 인출 과제 ──           │
│ → open cover로 (0,1)이   │
│   compact하지 않음을      │
│   설명하라.               │
│                          │
│ ── 증거 ──               │
│ [mapping] "(0,1)은 닫혀  │
│ 있지 않아서..."           │
│ → Heine-Borel 오용       │
└──────────────────────────┘
```

**Visual indicators**:
- Prerequisite mastery: ● solid (green), ◐ partial (yellow), ○ unknown (gray)
- Mapping edges: ✓ passed (green), ✗ failed (red), ○ not attempted (gray)
- Misconception tags: red bullet points
- Recall triggers: arrow prefix, italic text
- Evidence snippets: collapsible, gray background

**Loading state**: Skeleton placeholder (gray bars)
**Empty state**: "진단을 시작하면 혼동 지도가 생성됩니다."
**Null state**: Don't render panel at all (pre-session)

---

## Page Modifications

### StudySession.tsx

**Changes**:

1. **Step count**: 6 → 7 steps
   ```typescript
   const STEPS = [
     { key: 'diagnosis', label: '진단' },
     { key: 'prerequisites', label: '선행 확인' },
     { key: 'representations', label: '표현 학습' },
     { key: 'mapping', label: '매핑 과제' },        // NEW
     { key: 'misconceptions', label: '오개념 체크' },
     { key: 'recall', label: '인출 연습' },
     { key: 'summary', label: '세션 정리' },
   ];
   ```

2. **Layout**: Two-column layout for steps 3+ (mapping, misconceptions, recall)
   ```
   ┌─────────────────────────────────┬──────────────────────────┐
   │ [Current Step Content]          │ [ConfusionMapPanel]      │
   │ (takes ~65% width)              │ (takes ~35% width)       │
   └─────────────────────────────────┴──────────────────────────┘
   ```
   Steps 0-2 (diagnosis, prerequisites, representations): full width, no confusion map panel.

3. **New state**:
   ```typescript
   const [confusionMap, setConfusionMap] = useState<ConfusionMapData | null>(null);
   const [mappingTasks, setMappingTasks] = useState<MappingTaskItem[]>([]);
   const [mappingResults, setMappingResults] = useState<MappingResultItem[]>([]);
   ```

4. **New API calls**:
   ```typescript
   // After session creation or on restore
   const loadConfusionMap = async () => {
     const cmap = await getConfusionMap(sessionId);
     setConfusionMap(cmap);
   };

   // When entering mapping step
   const loadMappingTasks = async () => {
     const resp = await getMappingTasks(sessionId);
     setMappingTasks(resp.tasks);
   };

   // On mapping task submit
   const handleMappingSubmit = async (taskId: string, response: string) => {
     const result = await submitMapping(sessionId, taskId, response);
     setMappingResults(prev => [...prev, result]);
     setConfusionMap(result.confusion_map);
     return result;
   };
   ```

5. **Step rendering** (add mapping step case):
   ```typescript
   case 3: // mapping
     return (
       <MappingCheckStep
         sessionId={sessionId}
         tasks={mappingTasks}
         results={mappingResults}
         confusionMap={confusionMap}
         readOnly={viewedStep < currentStep}
         onTaskSubmit={handleMappingSubmit}
         onAllComplete={() => advanceStep()}
       />
     );
   ```

6. **Confusion map refresh**: After each step's API call completes, re-fetch confusion map:
   ```typescript
   // After diagnose, advance, self-explain, recall, etc.
   await loadConfusionMap();
   ```

---

### StudyStepper.tsx

**Changes**:
- Step count: 6 → 7
- Labels updated (add "매핑 과제" at index 3)
- No structural changes needed (already renders from array)

---

### SessionSummaryStep.tsx

**Changes**:
- Add confusion map summary section:
  ```
  ── 혼동 지도 요약 ──
  실패한 매핑: formal → counterexample
  활성 오개념: misuses_heine_borel, bounded_implies_compact
  다음 인출 과제: "open cover로 (0,1)이 compact하지 않음을 설명하라."
  ```
- Add "학습 보조" label for intuitive/visual mastery (not scored):
  ```
  | 직관적 설명 | — | — | 학습 보조 (미채점) |
  | 시각적 표현 | — | — | 학습 보조 (미채점) |
  ```

---

## API Client Updates

### New types in `apps/web/src/api/types.ts`

```typescript
// Mapping Tasks
export interface MappingTaskItem {
  task_id: string;
  task_type: string;
  prompt: string;
  source_representations: string[];
  target_representation: string;
}

export interface MappingTasksResponse {
  session_id: string;
  concept_id: string;
  tasks: MappingTaskItem[];
}

export interface MappingSubmitRequest {
  task_id: string;
  learner_response: string;
}

export interface MappingSubmitResult {
  task_id: string;
  task_type: string;
  score: number;
  passed: boolean;
  missing_elements: string[];
  misconception_tags: string[];
  mapping_failures: string[];
  feedback: string;
  next_recall_trigger: string;
  confusion_map: ConfusionMapData;
}

// Confusion Map
export interface PrerequisiteNodeItem {
  concept_id: string;
  mastery: string;
  self_reported: string | null;
}

export interface MappingEdgeItem {
  from_rep: string;
  to_rep: string;
  task_type: string;
  passed: boolean;
  score: number;
}

export interface EvidenceSnippetItem {
  step: string;
  task_type: string | null;
  learner_text: string;
  issue: string;
}

export interface ConfusionMapData {
  concept_id: string;
  session_id: string;
  prerequisite_nodes: PrerequisiteNodeItem[];
  mapping_edges: MappingEdgeItem[];
  misconception_tags: string[];
  next_recall_triggers: string[];
  evidence_snippets: EvidenceSnippetItem[];
  last_updated_step: string;
}
```

### New functions in `apps/web/src/api/client.ts`

```typescript
export async function getMappingTasks(sessionId: string): Promise<MappingTasksResponse> {
  return get<MappingTasksResponse>(`/study-session/${sessionId}/mapping-tasks`);
}

export async function submitMapping(
  sessionId: string,
  taskId: string,
  learnerResponse: string
): Promise<MappingSubmitResult> {
  return post<MappingSubmitResult>(
    `/study-session/${sessionId}/mapping-submit`,
    { task_id: taskId, learner_response: learnerResponse }
  );
}

export async function getConfusionMap(sessionId: string): Promise<ConfusionMapData> {
  return get<ConfusionMapData>(`/study-session/${sessionId}/confusion-map`);
}
```

---

## Layout Strategy

### Side-by-side layout (steps 3–5)

For mapping, misconceptions, and recall steps, the learner benefits from seeing the
confusion map alongside the current task. Use CSS flexbox:

```css
.study-session-split {
  display: flex;
  gap: 1.5rem;
}

.study-session-split__main {
  flex: 2;
  min-width: 0;
}

.study-session-split__panel {
  flex: 1;
  min-width: 280px;
  max-width: 400px;
  position: sticky;
  top: 1rem;
  align-self: flex-start;
}

/* Full width for steps 0-2 and 6 (summary) */
.study-session-full {
  max-width: 800px;
}
```

### Responsive behavior

On narrow screens (< 768px), stack vertically:
```css
@media (max-width: 768px) {
  .study-session-split {
    flex-direction: column;
  }
  .study-session-split__panel {
    max-width: 100%;
  }
}
```

---

## State Restoration (Frontend)

When browser refreshes mid-session:

1. sessionStorage stores `study_session_id`
2. On mount: GET /api/study-session/{id} → restore step + all past data
3. GET /api/study-session/{id}/confusion-map → restore confusion map
4. GET /api/study-session/{id}/mapping-tasks → restore mapping tasks (if at or past mapping step)
5. For completed mapping tasks: results are included in session state response
6. Past steps render in read-only mode
7. Current step resumes where learner left off

---

## Browser Smoke Checklist

| # | Action | Expected |
|---|--------|----------|
| 1 | Navigate to /study/compactness | Session created, diagnosis step shown |
| 2 | Submit diagnosis text | Diagnosis stored, advance to prerequisites |
| 3 | Check prerequisites, advance | Prerequisites stored, advance to representations |
| 4 | View all 5 representations, self-explain formal + proof_schema | Self-explanations stored |
| 5 | Advance to mapping step | 3 mapping tasks displayed |
| 6 | Submit mapping task 1 | Feedback shown, confusion map panel updates |
| 7 | Submit mapping task 2 | Feedback shown, confusion map updates |
| 8 | Submit mapping task 3 | All tasks complete, auto-advance to misconceptions |
| 9 | Answer misconception quiz | Answers stored, advance to recall |
| 10 | Submit white recall | Recall graded, advance to summary |
| 11 | View summary | Mastery table shows scored reps only, confusion map summary visible |
| 12 | Click complete | STUDY.md updated, redirect to dashboard |
| 13 | Refresh at step 4 (mapping) | Session restores, past steps read-only, mapping tasks visible |
| 14 | Check confusion map panel | Shows prerequisite nodes, mapping edges, misconception tags |
| 15 | Navigate to dashboard | Due concepts reflect new session |

---

## Files Summary

### Files to add

| File | Purpose |
|------|---------|
| `apps/web/src/components/study/MappingCheckStep.tsx` | Mapping task UI |
| `apps/web/src/components/study/ConfusionMapPanel.tsx` | Confusion map side panel |

### Files to modify

| File | What Changes |
|------|-------------|
| `apps/web/src/pages/StudySession.tsx` | 7-step flow, split layout, confusion map state, mapping handlers |
| `apps/web/src/components/study/StudyStepper.tsx` | 7 steps |
| `apps/web/src/components/study/SessionSummaryStep.tsx` | Confusion map summary, learning aid labels |
| `apps/web/src/api/types.ts` | Mapping + confusion map types |
| `apps/web/src/api/client.ts` | getMappingTasks, submitMapping, getConfusionMap |
| `apps/web/src/styles.css` | Split layout CSS |

---

## Implementation Checklist

- [ ] Add TypeScript types for mapping + confusion map
- [ ] Add API client functions (3 new)
- [ ] Create ConfusionMapPanel.tsx
- [ ] Create MappingCheckStep.tsx
- [ ] Update StudyStepper.tsx (7 steps)
- [ ] Update StudySession.tsx (layout, state, handlers, step rendering)
- [ ] Update SessionSummaryStep.tsx (confusion summary, learning aid labels)
- [ ] Add split layout CSS
- [ ] Run `npm run build` (verify no TypeScript errors)
- [ ] Manual browser smoke (15-point checklist above)

## Acceptance Criteria

1. MappingCheckStep renders 3 tasks with Korean prompts
2. ConfusionMapPanel shows prerequisite nodes, mapping edges, misconception tags, triggers
3. Side-by-side layout works for steps 3-5
4. StudyStepper shows 7 steps with correct labels
5. Session summary shows scored vs unscored reps
6. State restoration works after browser refresh
7. `npm run build` succeeds with no errors

## Risks

- StudySession.tsx is already 406 lines; adding mapping + confusion map state increases
  complexity. Mitigate: extract state management into custom hooks if needed.
- Side-by-side layout may look cramped on small screens. Mitigate: responsive stacking.
- Confusion map panel must update after every API call. Risk of stale data. Mitigate:
  always re-fetch after mutation calls.

## Rollback Plan

- New components are additive: delete MappingCheckStep.tsx and ConfusionMapPanel.tsx
- StudySession.tsx changes: revert to 6-step flow by removing step 3 case and split layout
- Types/client: additive, no rollback needed
- CSS: additive, no rollback needed

## Dependencies

- Depends on: 04 (Backend API) — endpoints must exist
- Depends on: 03 (Data Model) — TypeScript types mirror Pydantic models
