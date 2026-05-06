import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import type { CompleteStudySessionResponse } from '../../api/types';

interface SessionSummaryStepProps {
  conceptId: string;
  canonicalNameKo: string;
  stepsCompleted: string[];
  onComplete: () => void;
  completing: boolean;
  completionResult: CompleteStudySessionResponse | null;
  completionError: string | null;
  onGoToStep?: (step: number) => void;
}

const REP_LABELS: Record<string, string> = {
  formal: '정의',
  intuitive: '직관',
  visual: '시각',
  counterexample: '반례',
  proof_schema: '증명 구조',
};

const MASTERY_LABELS: Record<string, string> = {
  unknown: '미확인',
  partial: '부분',
  solid: '숙련',
};

const TOTAL_STEPS = 6;

export default function SessionSummaryStep({
  // conceptId and canonicalNameKo available for future use (completion_summary uses them server-side)
  conceptId: _conceptId,
  canonicalNameKo: _canonicalNameKo,
  stepsCompleted,
  onComplete,
  completing,
  completionResult,
  completionError,
  onGoToStep,
}: SessionSummaryStepProps) {
  void _conceptId;
  void _canonicalNameKo;
  useEffect(() => {
    // Trigger completion on mount if not already completed/completing
    if (!completionResult && !completing && !completionError) {
      onComplete();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Loading state
  if (completing) {
    return (
      <div>
        <h2 style={{ marginBottom: 16 }}>세션 정리</h2>
        <p style={{ color: '#64748b' }}>학습 결과를 처리하고 있습니다...</p>
      </div>
    );
  }

  // Error state
  if (completionError) {
    return (
      <div>
        <h2 style={{ marginBottom: 16 }}>세션 정리</h2>
        <div style={{
          background: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: 8, padding: '16px 20px', marginBottom: 20,
        }}>
          <p style={{ fontWeight: 600, color: '#b91c1c', marginBottom: 8 }}>
            세션 완료 중 오류가 발생했습니다
          </p>
          <p style={{ fontSize: 13, color: '#991b1b' }}>{completionError}</p>
          {(completionError.includes('formal') || completionError.includes('proof_schema') || completionError.includes('자기 설명')) && (
            <div style={{ marginTop: 8 }}>
              <p style={{ fontSize: 13, color: '#92400e' }}>
                표현 학습 단계로 돌아가서 formal, proof_schema 자기 설명을 제출해 주세요.
              </p>
              {onGoToStep && (
                <button className="submit-btn" style={{ marginTop: 8, background: '#d97706', fontSize: 13 }} onClick={() => onGoToStep(3)}>
                  표현 학습으로 돌아가기
                </button>
              )}
            </div>
          )}
          {completionError.includes('인출') && (
            <div style={{ marginTop: 8 }}>
              <p style={{ fontSize: 13, color: '#92400e' }}>
                인출 연습 단계로 돌아가서 인출 응답을 제출해 주세요.
              </p>
              {onGoToStep && (
                <button className="submit-btn" style={{ marginTop: 8, background: '#d97706', fontSize: 13 }} onClick={() => onGoToStep(5)}>
                  인출 연습으로 돌아가기
                </button>
              )}
            </div>
          )}
        </div>
        <button className="submit-btn" style={{ background: '#64748b' }} onClick={onComplete}>
          다시 시도
        </button>
      </div>
    );
  }

  // Success state
  if (!completionResult) return null;

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>세션 정리</h2>

      <div style={{
        background: '#f0fdf4', border: '1px solid #bbf7d0',
        borderRadius: 8, padding: '16px 20px', marginBottom: 20,
      }}>
        <p style={{ fontWeight: 600, color: '#15803d', marginBottom: 8 }}>
          학습 세션을 완료했습니다!
        </p>
        <p style={{ fontSize: 14, color: '#166534' }}>
          {completionResult.completion_summary}
        </p>
        <p style={{ fontSize: 13, color: '#166534', marginTop: 4 }}>
          완료한 단계: {stepsCompleted.length}/{TOTAL_STEPS}
        </p>
      </div>

      {/* Mastery updates table */}
      {completionResult.mastery_updates.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h3 style={{ marginBottom: 10, fontSize: 15 }}>숙련도 변화</h3>
          <table className="table-simple">
            <thead>
              <tr>
                <th>표현</th>
                <th>이전</th>
                <th>이후</th>
                <th>정확도</th>
              </tr>
            </thead>
            <tbody>
              {completionResult.mastery_updates.map((mu) => (
                <tr key={mu.representation_type}>
                  <td>{REP_LABELS[mu.representation_type] ?? mu.representation_type}</td>
                  <td><span className="badge badge-overdue">{MASTERY_LABELS[mu.before] ?? mu.before}</span></td>
                  <td>
                    <span className={`badge ${mu.after === 'solid' ? 'badge-solid' : mu.after === 'partial' ? 'badge-partial' : 'badge-overdue'}`}>
                      {MASTERY_LABELS[mu.after] ?? mu.after}
                    </span>
                  </td>
                  <td>{Math.round(mu.accuracy_score * 100)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Session details */}
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 14, color: '#555' }}>
          다음 복습일: <strong>{completionResult.next_review_date}</strong>
        </p>
        <p style={{ fontSize: 14, color: '#555' }}>
          STUDY.md 업데이트: <strong>{completionResult.study_md_updated ? '완료' : '실패'}</strong>
        </p>
        {completionResult.study_patch_path && (
          <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 4 }}>
            패치 경로: {completionResult.study_patch_path}
          </p>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <Link className="submit-btn" to="/dashboard" style={{ textDecoration: 'none' }}>
          대시보드로 돌아가기
        </Link>
        <Link className="submit-btn" to="/" style={{ textDecoration: 'none', background: '#64748b' }}>
          다른 개념 공부하기
        </Link>
      </div>
    </div>
  );
}
