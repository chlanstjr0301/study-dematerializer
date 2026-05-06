import { useState } from 'react';
import type { DiagnoseResponse } from '../../api/types';

interface DiagnosisStepProps {
  initialKnowledge?: string;
  initialGap?: string;
  onSubmit: (priorKnowledge: string, gap: string) => Promise<void>;
  submitting?: boolean;
  result?: DiagnoseResponse | null;
  onConfirm: () => void;
  readOnly?: boolean;
}

export default function DiagnosisStep({
  initialKnowledge = '',
  initialGap = '',
  onSubmit,
  submitting = false,
  result,
  onConfirm,
  readOnly = false,
}: DiagnosisStepProps) {
  const [knowledge, setKnowledge] = useState(initialKnowledge);
  const [gap, setGap] = useState(initialGap);

  async function handleSubmit() {
    await onSubmit(knowledge, gap);
  }

  // After diagnosis result is available, show result card
  if (result) {
    return (
      <div>
        <h2 style={{ marginBottom: 16 }}>진단 결과</h2>

        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 14, color: '#555', marginBottom: 4 }}>
            <strong>사전 지식:</strong> {initialKnowledge || '(미입력)'}
          </p>
          <p style={{ fontSize: 14, color: '#555' }}>
            <strong>어려운 부분:</strong> {initialGap || '(미입력)'}
          </p>
        </div>

        <div style={{
          background: '#f8fafc', border: '1px solid #e2e8f0',
          borderRadius: 8, padding: '16px 20px', marginBottom: 16,
        }}>
          <p style={{ marginBottom: 8 }}>
            <strong>초기 숙련도:</strong>{' '}
            <span className={`badge badge-${result.initial_mastery_estimate === 'unknown' ? 'overdue' : 'partial'}`}>
              {result.initial_mastery_estimate === 'unknown' ? '미확인' : '부분'}
            </span>
          </p>
          {result.identified_gaps.length > 0 && (
            <p style={{ marginBottom: 8, fontSize: 14 }}>
              <strong>취약점:</strong> {result.identified_gaps.join(', ')}
            </p>
          )}
          <p style={{ fontSize: 14, color: '#475569' }}>
            <strong>권장사항:</strong> {result.recommendation}
          </p>
        </div>

        {!readOnly && (
          <button className="submit-btn" onClick={onConfirm}>
            확인, 다음 단계로 &rarr;
          </button>
        )}
      </div>
    );
  }

  // Input form (before submission)
  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>진단</h2>

      <div style={{ marginBottom: 20 }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14 }}>
          이 개념에 대해 알고 있는 것을 적어 주세요
        </label>
        <textarea
          className="recall-textarea"
          value={knowledge}
          onChange={(e) => setKnowledge(e.target.value)}
          placeholder="현재 이해하고 있는 내용을 자유롭게 적어보세요..."
          style={{ minHeight: 100 }}
          disabled={submitting || readOnly}
        />
      </div>

      <div style={{ marginBottom: 20 }}>
        <label style={{ display: 'block', fontWeight: 600, marginBottom: 6, fontSize: 14 }}>
          어디서 막히거나 헷갈리나요?
        </label>
        <textarea
          className="recall-textarea"
          value={gap}
          onChange={(e) => setGap(e.target.value)}
          placeholder="모르는 부분, 헷갈리는 부분을 적어보세요..."
          style={{ minHeight: 100 }}
          disabled={submitting || readOnly}
        />
      </div>

      {!readOnly && (
        <button
          className="submit-btn"
          onClick={handleSubmit}
          disabled={submitting}
        >
          {submitting ? '제출 중...' : '다음 단계 →'}
        </button>
      )}
    </div>
  );
}
