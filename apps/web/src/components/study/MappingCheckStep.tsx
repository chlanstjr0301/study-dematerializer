import { useState } from 'react';
import type {
  MappingTaskItem,
  MappingSubmitResult,
  ConfusionMapData,
} from '../../api/types';

interface MappingCheckStepProps {
  sessionId: string;
  tasks: MappingTaskItem[];
  results: MappingSubmitResult[];
  confusionMap: ConfusionMapData | null;
  readOnly: boolean;
  onTaskSubmit: (taskId: string, response: string) => Promise<MappingSubmitResult>;
  onAllComplete: () => void;
}

const TASK_TYPE_LABELS: Record<string, string> = {
  formal_to_counterexample: 'Formal → 반례',
  counterexample_to_formal: '반례 → Formal',
  formal_counterexample_to_proof_schema: 'Formal+반례 → 증명 구조',
};

export default function MappingCheckStep({
  tasks,
  results: initialResults,
  readOnly,
  onTaskSubmit,
  onAllComplete,
}: MappingCheckStepProps) {
  const [currentTaskIndex, setCurrentTaskIndex] = useState(
    () => Math.min(initialResults.length, tasks.length - 1),
  );
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [results, setResults] = useState<MappingSubmitResult[]>(initialResults);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submittedIds = new Set(results.map((r) => r.task_id));
  const allSubmitted = tasks.length > 0 && tasks.every((t) => submittedIds.has(t.task_id));

  // Loading state
  if (tasks.length === 0) {
    return (
      <div>
        <h2 style={{ marginBottom: 16 }}>매핑 과제</h2>
        <p className="loading">매핑 과제를 불러오는 중...</p>
      </div>
    );
  }

  async function handleSubmit(task: MappingTaskItem) {
    const text = responses[task.task_id] ?? '';
    if (text.trim().length < 10) return;

    setSubmitting(true);
    setError(null);
    try {
      const result = await onTaskSubmit(task.task_id, text);
      setResults((prev) => [...prev, result]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '제출에 실패했습니다.');
    } finally {
      setSubmitting(false);
    }
  }

  function handleNextTask() {
    if (currentTaskIndex < tasks.length - 1) {
      setCurrentTaskIndex((i) => i + 1);
    }
  }

  // Read-only: show all tasks with their results
  if (readOnly) {
    return (
      <div>
        <h2 style={{ marginBottom: 16 }}>매핑 과제</h2>
        {tasks.map((task, i) => {
          const result = results.find((r) => r.task_id === task.task_id);
          return (
            <div key={task.task_id} className="card" style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 13, color: '#888', marginBottom: 4 }}>
                과제 {i + 1}/{tasks.length}: {TASK_TYPE_LABELS[task.task_type] ?? task.task_type}
              </div>
              <p style={{ fontSize: 14, marginBottom: 8 }}>{task.prompt}</p>
              {result && <ResultFeedback result={result} />}
              {!result && (
                <p style={{ fontSize: 13, color: '#94a3b8', fontStyle: 'italic' }}>미제출</p>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  const currentTask = tasks[currentTaskIndex];
  const currentResult = results.find((r) => r.task_id === currentTask.task_id);
  const currentResponse = responses[currentTask.task_id] ?? '';

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>매핑 과제</h2>

      {/* Task tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {tasks.map((task, i) => {
          const done = submittedIds.has(task.task_id);
          const active = i === currentTaskIndex;
          return (
            <button
              key={task.task_id}
              onClick={() => setCurrentTaskIndex(i)}
              style={{
                padding: '6px 14px',
                borderRadius: 16,
                border: active ? '2px solid #1a1a2e' : '1px solid #d1d5db',
                background: done ? '#d1fae5' : active ? '#eef2ff' : '#fff',
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: active ? 600 : 400,
                color: done ? '#065f46' : '#333',
              }}
            >
              {done ? '\u2713 ' : ''}{i + 1}
            </button>
          );
        })}
        <span style={{ fontSize: 13, color: '#888', alignSelf: 'center', marginLeft: 4 }}>
          ({results.length}/{tasks.length} 완료)
        </span>
      </div>

      {/* Current task card */}
      <div className="card">
        <div style={{ fontSize: 13, color: '#888', marginBottom: 4 }}>
          과제 {currentTaskIndex + 1}: {TASK_TYPE_LABELS[currentTask.task_type] ?? currentTask.task_type}
        </div>
        <div style={{ fontSize: 12, color: '#aaa', marginBottom: 8 }}>
          {currentTask.source_representations.join(', ')} → {currentTask.target_representation}
        </div>
        <p style={{ fontSize: 14, color: '#1e293b', marginBottom: 12 }}>
          {currentTask.prompt}
        </p>

        {/* Textarea — only if not yet submitted */}
        {!currentResult && (
          <>
            <textarea
              className="recall-textarea"
              value={currentResponse}
              onChange={(e) =>
                setResponses((prev) => ({ ...prev, [currentTask.task_id]: e.target.value }))
              }
              placeholder="답변을 10자 이상 작성하세요..."
              style={{ minHeight: 120 }}
              disabled={submitting}
            />
            {currentResponse.trim().length < 10 && currentResponse.trim().length > 0 && (
              <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
                최소 10자 이상 작성해 주세요. ({currentResponse.trim().length}/10)
              </p>
            )}
            <button
              className="submit-btn"
              onClick={() => handleSubmit(currentTask)}
              disabled={currentResponse.trim().length < 10 || submitting}
              style={{ marginTop: 12 }}
            >
              {submitting ? '평가 중...' : '제출하기'}
            </button>
          </>
        )}

        {/* Feedback for submitted task */}
        {currentResult && <ResultFeedback result={currentResult} />}

        {/* Next task button */}
        {currentResult && !allSubmitted && currentTaskIndex < tasks.length - 1 && (
          <button
            className="submit-btn"
            onClick={handleNextTask}
            style={{ marginTop: 12, background: '#374151' }}
          >
            다음 과제 →
          </button>
        )}
      </div>

      {error && <div className="error-box" style={{ marginTop: 12 }}>{error}</div>}

      {/* All done summary */}
      {allSubmitted && (
        <div style={{
          background: '#f0fdf4', border: '1px solid #bbf7d0',
          borderRadius: 8, padding: '16px 20px', marginTop: 20,
        }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#15803d', marginBottom: 8 }}>
            모든 매핑 과제를 완료했습니다!
          </div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, flexWrap: 'wrap' }}>
            {results.map((r) => (
              <span
                key={r.task_id}
                style={{
                  fontSize: 12, padding: '3px 10px', borderRadius: 12,
                  background: r.passed ? '#d1fae5' : '#fee2e2',
                  color: r.passed ? '#065f46' : '#991b1b',
                }}
              >
                {TASK_TYPE_LABELS[r.task_type] ?? r.task_type}: {r.passed ? '통과' : '실패'}
                {' '}({Math.round(r.score * 100)}%)
              </span>
            ))}
          </div>
          <button className="submit-btn" onClick={onAllComplete}>
            다음 단계로 →
          </button>
        </div>
      )}
    </div>
  );
}

/* ---- Inline feedback sub-component ---- */

function ResultFeedback({ result }: { result: MappingSubmitResult }) {
  return (
    <div style={{
      background: result.passed ? '#f0fdf4' : '#fef2f2',
      border: `1px solid ${result.passed ? '#bbf7d0' : '#fecaca'}`,
      borderRadius: 6, padding: '12px 16px', marginTop: 12,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{
          fontSize: 13, fontWeight: 600,
          color: result.passed ? '#15803d' : '#b91c1c',
        }}>
          {result.passed ? '통과' : '실패'}
        </span>
        <span style={{
          fontSize: 12, padding: '2px 8px', borderRadius: 4,
          background: result.passed ? '#bbf7d0' : '#fecaca',
          color: result.passed ? '#15803d' : '#b91c1c',
        }}>
          {Math.round(result.score * 100)}%
        </span>
      </div>

      {result.feedback && (
        <p style={{ fontSize: 13, color: '#374151', marginBottom: 6 }}>
          {result.feedback}
        </p>
      )}

      {result.missing_elements.length > 0 && (
        <div style={{ fontSize: 12, color: '#92400e', marginTop: 4 }}>
          <span style={{ fontWeight: 500 }}>누락:</span>{' '}
          {result.missing_elements.join(', ')}
        </div>
      )}

      {result.misconception_tags.length > 0 && (
        <div style={{ fontSize: 12, color: '#b91c1c', marginTop: 4 }}>
          <span style={{ fontWeight: 500 }}>오개념:</span>{' '}
          {result.misconception_tags.join(', ')}
        </div>
      )}

      {result.next_recall_trigger && (
        <div style={{ fontSize: 12, color: '#1e40af', marginTop: 4, fontStyle: 'italic' }}>
          → {result.next_recall_trigger}
        </div>
      )}
    </div>
  );
}
