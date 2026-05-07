import { useEffect, useState } from 'react';
import { getBank } from '../../api/client';
import type { QuestionItem, RecallSubmitResponse } from '../../api/types';
import RichMathText from '../common/RichMathText';
import GraderProvenance from '../common/GraderProvenance';

interface WhiteRecallStepProps {
  conceptId: string;
  onSubmitRecall: (learnerResponse: string) => Promise<RecallSubmitResponse>;
  onNext: () => void;
  recallResult: RecallSubmitResponse | null;
  recallSubmitting: boolean;
  advancing?: boolean;
  readOnly?: boolean;
}

const QUESTION_TYPE_LABELS: Record<string, string> = {
  define: '정의',
  explain: '설명',
  prove: '증명',
  example: '예시',
  counterexample: '반례',
  visualize: '시각화',
};

export default function WhiteRecallStep({
  conceptId,
  onSubmitRecall,
  onNext,
  recallResult,
  recallSubmitting,
  advancing = false,
  readOnly = false,
}: WhiteRecallStepProps) {
  const [recall, setRecall] = useState('');
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [loadingQuestions, setLoadingQuestions] = useState(true);

  useEffect(() => {
    // Fetch bank questions (read-only display).
    // If fetch fails, silently degrade to textarea-only.
    getBank(conceptId)
      .then(setQuestions)
      .catch(() => {})
      .finally(() => setLoadingQuestions(false));
  }, [conceptId]);

  async function handleSubmit() {
    if (!recall.trim()) return;
    await onSubmitRecall(recall);
  }

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>인출 연습</h2>

      <div style={{
        background: '#eff6ff', border: '1px solid #bfdbfe',
        borderRadius: 6, padding: '12px 16px', marginBottom: 20,
        fontSize: 14, color: '#1e40af',
      }}>
        교재를 덮고, 아래 질문들에 대해 처음부터 설명해 보세요.
      </div>

      {/* Read-only bank questions */}
      {!loadingQuestions && questions.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10, color: '#374151' }}>
            인출 질문 ({questions.length}개)
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {questions.map((q, i) => (
              <div key={q.id} style={{
                padding: '10px 14px', borderRadius: 6,
                background: '#f8fafc', border: '1px solid #e2e8f0',
              }}>
                <span style={{ fontSize: 12, color: '#64748b', marginRight: 8 }}>
                  [{QUESTION_TYPE_LABELS[q.question_type] ?? q.question_type}]
                </span>
                <span style={{ fontSize: 14, color: '#1e293b' }}>
                  {i + 1}. <RichMathText className="rich-math-text" inline>{q.question}</RichMathText>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <textarea
        className="recall-textarea"
        value={recall}
        onChange={(e) => setRecall(e.target.value)}
        placeholder="이 개념을 처음부터 설명해 보세요. 정의, 핵심 아이디어, 예시, 증명 구조 등을 자유롭게 작성하세요..."
        style={{ minHeight: 200 }}
        disabled={readOnly || !!recallResult}
      />

      {/* Submit button — only before recall is evaluated */}
      {!readOnly && !recallResult && (
        <button
          className="submit-btn"
          onClick={handleSubmit}
          disabled={!recall.trim() || recallSubmitting}
          style={{ marginTop: 16 }}
        >
          {recallSubmitting ? '평가 중...' : '제출'}
        </button>
      )}

      {!readOnly && !recallResult && !recall.trim() && (
        <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 8 }}>
          내용을 작성하면 제출할 수 있습니다.
        </p>
      )}

      {/* Recall evaluation result */}
      {recallResult && (
        <div style={{
          background: '#f0fdf4', border: '1px solid #bbf7d0',
          borderRadius: 8, padding: '16px 20px', marginTop: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#15803d' }}>
              인출 평가 결과
            </span>
            <span style={{
              fontSize: 12, padding: '2px 8px', borderRadius: 4,
              background: recallResult.accuracy_score >= 0.85 ? '#bbf7d0' :
                recallResult.accuracy_score >= 0.5 ? '#fef3c7' : '#fecaca',
              color: recallResult.accuracy_score >= 0.85 ? '#15803d' :
                recallResult.accuracy_score >= 0.5 ? '#92400e' : '#b91c1c',
            }}>
              정확도: {Math.round(recallResult.accuracy_score * 100)}%
            </span>
          </div>
          {recallResult.feedback && (
            <div style={{ fontSize: 13, color: '#374151', marginBottom: 8 }}>
              <RichMathText className="rich-math-text">{recallResult.feedback}</RichMathText>
            </div>
          )}
          {recallResult.missing_elements.length > 0 && (
            <div style={{ fontSize: 12, color: '#92400e', marginTop: 4 }}>
              <span style={{ fontWeight: 500 }}>누락된 내용:</span>
              <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                {recallResult.missing_elements.map((el, i) => (
                  <li key={i}><RichMathText className="rich-math-text" inline>{el}</RichMathText></li>
                ))}
              </ul>
            </div>
          )}
          {recallResult.errors.length > 0 && (
            <div style={{ fontSize: 12, color: '#b91c1c', marginTop: 4 }}>
              <span style={{ fontWeight: 500 }}>오류:</span>
              <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                {recallResult.errors.map((el, i) => (
                  <li key={i}><RichMathText className="rich-math-text" inline>{el}</RichMathText></li>
                ))}
              </ul>
            </div>
          )}
          <GraderProvenance graderSource={recallResult.grader_source} />
        </div>
      )}

      {/* Advance button — only after recall is evaluated */}
      {!readOnly && recallResult && (
        <button
          className="submit-btn"
          onClick={onNext}
          disabled={advancing}
          style={{ marginTop: 16 }}
        >
          {advancing ? '처리 중...' : '다음 단계로 →'}
        </button>
      )}
    </div>
  );
}
