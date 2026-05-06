import { useState } from 'react';
import { useParams } from 'react-router-dom';
import StudyStepper from '../components/study/StudyStepper';
import DiagnosisStep from '../components/study/DiagnosisStep';
import PrerequisiteStep from '../components/study/PrerequisiteStep';
import RepresentationStep from '../components/study/RepresentationStep';
import MisconceptionStep from '../components/study/MisconceptionStep';
import WhiteRecallStep from '../components/study/WhiteRecallStep';
import SessionSummaryStep from '../components/study/SessionSummaryStep';

const STEP_LABELS = ['진단', '선행 확인', '표현 학습', '오개념 체크', '인출 연습', '세션 정리'];

export default function StudySession() {
  const { conceptId } = useParams<{ conceptId: string }>();
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);

  // Step input state
  const [priorKnowledge, setPriorKnowledge] = useState('');
  const [gap, setGap] = useState('');

  function completeStep(step: number) {
    if (!completedSteps.includes(step)) {
      setCompletedSteps(prev => [...prev, step]);
    }
    if (step < STEP_LABELS.length - 1) {
      setCurrentStep(step + 1);
    }
  }

  function goBack() {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  }

  const concept = conceptId ?? 'unknown';

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>학습 세션: {concept}</h1>

      <StudyStepper
        steps={STEP_LABELS}
        currentStep={currentStep}
        completedSteps={completedSteps}
      />

      <div className="section">
        <div className="card">
          {currentStep === 0 && (
            <DiagnosisStep
              initialKnowledge={priorKnowledge}
              initialGap={gap}
              onNext={(k, g) => {
                setPriorKnowledge(k);
                setGap(g);
                completeStep(0);
              }}
            />
          )}
          {currentStep === 1 && (
            <PrerequisiteStep
              conceptId={concept}
              onNext={() => completeStep(1)}
            />
          )}
          {currentStep === 2 && (
            <RepresentationStep
              onNext={() => completeStep(2)}
            />
          )}
          {currentStep === 3 && (
            <MisconceptionStep
              conceptId={concept}
              onNext={() => completeStep(3)}
            />
          )}
          {currentStep === 4 && (
            <WhiteRecallStep
              onNext={() => completeStep(4)}
            />
          )}
          {currentStep === 5 && (
            <SessionSummaryStep conceptId={concept} />
          )}
        </div>
      </div>

      {/* Navigation */}
      {currentStep > 0 && currentStep < 5 && (
        <div style={{ marginTop: 12 }}>
          <button
            className="submit-btn"
            style={{ background: '#64748b', fontSize: 13 }}
            onClick={goBack}
          >
            ← 이전 단계
          </button>
        </div>
      )}
    </div>
  );
}
