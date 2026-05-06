import { useState } from 'react';

interface WhiteRecallStepProps {
  onNext: () => void;
}

export default function WhiteRecallStep({ onNext }: WhiteRecallStepProps) {
  const [recall, setRecall] = useState('');

  return (
    <div>
      <h2 style={{ marginBottom: 16 }}>인출 연습</h2>

      <div style={{
        background: '#eff6ff', border: '1px solid #bfdbfe',
        borderRadius: 6, padding: '12px 16px', marginBottom: 20,
        fontSize: 14, color: '#1e40af',
      }}>
        교재를 덮고, 처음부터 설명해 보세요.
      </div>

      <textarea
        className="recall-textarea"
        value={recall}
        onChange={(e) => setRecall(e.target.value)}
        placeholder="이 개념을 처음부터 설명해 보세요. 정의, 핵심 아이디어, 예시, 증명 구조 등을 자유롭게 작성하세요..."
        style={{ minHeight: 200 }}
      />

      <button
        className="submit-btn"
        onClick={onNext}
        disabled={!recall.trim()}
        style={{ marginTop: 16 }}
      >
        제출
      </button>

      {!recall.trim() && (
        <p style={{ fontSize: 13, color: '#94a3b8', marginTop: 8 }}>
          내용을 작성하면 제출할 수 있습니다.
        </p>
      )}
    </div>
  );
}
