import { useState } from 'react';

interface DiagnosisStepProps {
  initialKnowledge?: string;
  initialGap?: string;
  onNext: (priorKnowledge: string, gap: string) => void;
}

export default function DiagnosisStep({ initialKnowledge = '', initialGap = '', onNext }: DiagnosisStepProps) {
  const [knowledge, setKnowledge] = useState(initialKnowledge);
  const [gap, setGap] = useState(initialGap);

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
        />
      </div>

      <button
        className="submit-btn"
        onClick={() => onNext(knowledge, gap)}
      >
        다음 단계 →
      </button>
    </div>
  );
}
