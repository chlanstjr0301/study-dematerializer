import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  createStudySession,
  getStudySession,
  submitStudyDiagnosis,
  advanceStudySessionStep,
} from '../api/client';
import type {
  CreateStudySessionResponse,
  DiagnoseResponse,
} from '../api/types';
import StudyStepper from '../components/study/StudyStepper';
import DiagnosisStep from '../components/study/DiagnosisStep';
import PrerequisiteStep from '../components/study/PrerequisiteStep';
import RepresentationStep from '../components/study/RepresentationStep';
import MisconceptionStep from '../components/study/MisconceptionStep';
import WhiteRecallStep from '../components/study/WhiteRecallStep';
import SessionSummaryStep from '../components/study/SessionSummaryStep';

const STEP_LABELS = ['진단', '선행 확인', '표현 학습', '오개념 체크', '인출 연습', '세션 정리'];
const STEPS = ['diagnose', 'prerequisites', 'representations', 'misconceptions', 'recall', 'summary'];

function storageKey(conceptId: string) {
  return `study_session_${conceptId}`;
}

export default function StudySession() {
  const { conceptId } = useParams<{ conceptId: string }>();
  const concept = conceptId ?? 'unknown';

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<CreateStudySessionResponse | null>(null);
  const [currentStep, setCurrentStep] = useState(1); // 1-indexed (backend)
  const [stepsCompleted, setStepsCompleted] = useState<string[]>([]);
  const [diagnosisResult, setDiagnosisResult] = useState<DiagnoseResponse | null>(null);
  const [advancing, setAdvancing] = useState(false);
  const [stepError, setStepError] = useState<string | null>(null);
  const [viewingStep, setViewingStep] = useState(1);

  // Diagnosis input state (for re-display on back nav)
  const [priorKnowledge, setPriorKnowledge] = useState('');
  const [gap, setGap] = useState('');

  useEffect(() => {
    initSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conceptId]);

  async function initSession() {
    setLoading(true);
    setError(null);

    const key = storageKey(concept);
    const stored = sessionStorage.getItem(key);

    if (stored) {
      try {
        const { sessionId: sid, createResponse } = JSON.parse(stored);
        const state = await getStudySession(sid);
        // Restore from backend state
        setSessionId(sid);
        setSessionData(createResponse);
        setCurrentStep(state.current_step);
        setStepsCompleted(state.steps_completed);
        setViewingStep(state.current_step);
        if (state.diagnosis) {
          setPriorKnowledge(state.diagnosis.prior_knowledge);
          setGap(state.diagnosis.gap_description);
          setDiagnosisResult({
            initial_mastery_estimate: state.diagnosis.initial_mastery_estimate,
            identified_gaps: state.diagnosis.identified_gaps,
            recommendation: state.diagnosis.recommendation,
          });
        }
        setLoading(false);
        return;
      } catch {
        // Session not found or parse error — clear and create new
        sessionStorage.removeItem(key);
      }
    }

    // Create new session
    await createNewSession();
  }

  async function createNewSession() {
    try {
      const resp = await createStudySession({ concept_id: concept });
      setSessionId(resp.session_id);
      setSessionData(resp);
      setCurrentStep(resp.current_step);
      setStepsCompleted([]);
      setViewingStep(resp.current_step);
      sessionStorage.setItem(storageKey(concept), JSON.stringify({
        sessionId: resp.session_id,
        createResponse: resp,
      }));
      setLoading(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes('422') && msg.includes('소스 파일')) {
        setError('소스 파일을 먼저 업로드하세요.');
      } else if (msg.includes('422')) {
        setError('지원하지 않는 개념입니다.');
      } else {
        setError('세션 생성에 실패했습니다. 다시 시도해 주세요.');
      }
      setLoading(false);
    }
  }

  // --- Diagnosis ---
  // NOTE: advance("diagnose") 절대 호출 금지!
  // diagnose 단계는 submitStudyDiagnosis 성공 시 backend에서 자동 current_step=2.
  async function handleDiagnoseSubmit(prior: string, gapDesc: string) {
    if (!sessionId) return;
    setAdvancing(true);
    setStepError(null);
    try {
      const result = await submitStudyDiagnosis(sessionId, {
        prior_knowledge: prior,
        gap_description: gapDesc,
      });
      setPriorKnowledge(prior);
      setGap(gapDesc);
      setDiagnosisResult(result);
      setStepsCompleted(prev => [...prev, 'diagnose']);
      setCurrentStep(2);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setStepError(`진단 제출 실패: ${msg}`);
    } finally {
      setAdvancing(false);
    }
  }

  function handleDiagnoseConfirm() {
    setViewingStep(2);
  }

  // --- Advance (steps 2-5) ---
  async function handleAdvance(stepName: string) {
    if (!sessionId) return;
    setAdvancing(true);
    setStepError(null);
    try {
      const resp = await advanceStudySessionStep(sessionId, { completed_step: stepName });
      setCurrentStep(resp.current_step);
      setStepsCompleted(resp.steps_completed);
      setViewingStep(resp.current_step);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setStepError(`단계 진행 실패: ${msg}`);
    } finally {
      setAdvancing(false);
    }
  }

  // --- Navigation ---
  function goBack() {
    if (viewingStep > 1) {
      setViewingStep(viewingStep - 1);
    }
  }

  function goToCurrent() {
    setViewingStep(currentStep);
  }

  // --- Render ---
  if (loading) {
    return (
      <div>
        <h1 style={{ marginBottom: 8 }}>학습 세션: {concept}</h1>
        <div className="section">
          <div className="card">
            <p style={{ color: '#64748b' }}>학습 세션을 준비하고 있습니다...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1 style={{ marginBottom: 8 }}>학습 세션: {concept}</h1>
        <div className="section">
          <div className="card" style={{ borderColor: '#ef4444' }}>
            <p style={{ color: '#dc2626', marginBottom: 12 }}>{error}</p>
            {error.includes('소스 파일') && (
              <Link to="/sources" className="submit-btn" style={{ textDecoration: 'none', marginRight: 8 }}>
                소스 업로드
              </Link>
            )}
            <button className="submit-btn" style={{ background: '#64748b' }} onClick={() => { setError(null); setLoading(true); createNewSession(); }}>
              다시 시도
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!sessionData) return null;

  const displayStep = viewingStep - 1; // 0-indexed for StudyStepper
  const completedIndices = stepsCompleted.map(s => STEPS.indexOf(s));
  const readOnly = viewingStep < currentStep;

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>학습 세션: {sessionData.canonical_name_ko}</h1>

      <StudyStepper
        steps={STEP_LABELS}
        currentStep={displayStep}
        completedSteps={completedIndices}
      />

      <div className="section">
        <div className="card">
          {stepError && (
            <p style={{ color: '#dc2626', fontSize: 13, marginBottom: 12 }}>{stepError}</p>
          )}

          {displayStep === 0 && (
            <DiagnosisStep
              initialKnowledge={priorKnowledge}
              initialGap={gap}
              onSubmit={handleDiagnoseSubmit}
              submitting={advancing}
              result={diagnosisResult}
              onConfirm={handleDiagnoseConfirm}
              readOnly={readOnly}
            />
          )}
          {displayStep === 1 && (
            <PrerequisiteStep
              prerequisites={sessionData.prerequisites}
              onNext={() => handleAdvance('prerequisites')}
              advancing={advancing}
              readOnly={readOnly}
            />
          )}
          {displayStep === 2 && (
            <RepresentationStep
              representations={sessionData.representations}
              onNext={() => handleAdvance('representations')}
              advancing={advancing}
              readOnly={readOnly}
            />
          )}
          {displayStep === 3 && (
            <MisconceptionStep
              misconceptions={sessionData.misconceptions}
              onNext={() => handleAdvance('misconceptions')}
              advancing={advancing}
              readOnly={readOnly}
            />
          )}
          {displayStep === 4 && (
            <WhiteRecallStep
              conceptId={concept}
              onNext={() => handleAdvance('recall')}
              advancing={advancing}
              readOnly={readOnly}
            />
          )}
          {displayStep === 5 && (
            <SessionSummaryStep
              conceptId={concept}
              canonicalNameKo={sessionData.canonical_name_ko}
              stepsCompleted={stepsCompleted}
            />
          )}
        </div>
      </div>

      {/* Navigation */}
      {viewingStep > 1 && displayStep < 5 && (
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button
            className="submit-btn"
            style={{ background: '#64748b', fontSize: 13 }}
            onClick={goBack}
          >
            &larr; 이전 단계
          </button>
          {readOnly && (
            <button
              className="submit-btn"
              style={{ fontSize: 13 }}
              onClick={goToCurrent}
            >
              현재 단계로 &rarr;
            </button>
          )}
        </div>
      )}
    </div>
  );
}
