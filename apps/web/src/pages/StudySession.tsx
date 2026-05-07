import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  createStudySession,
  getStudySession,
  submitStudyDiagnosis,
  advanceStudySessionStep,
  submitSelfExplanation,
  submitRecall,
  completeStudySession,
  getMappingTasks,
  submitMapping,
  getConfusionMap,
} from '../api/client';
import type {
  CreateStudySessionResponse,
  DiagnoseResponse,
  SelfExplainResponse,
  RecallSubmitResponse,
  CompleteStudySessionResponse,
  MappingTaskItem,
  MappingSubmitResult,
  ConfusionMapData,
} from '../api/types';
import StudyStepper from '../components/study/StudyStepper';
import DiagnosisStep from '../components/study/DiagnosisStep';
import PrerequisiteStep from '../components/study/PrerequisiteStep';
import RepresentationStep from '../components/study/RepresentationStep';
import MappingCheckStep from '../components/study/MappingCheckStep';
import MisconceptionStep from '../components/study/MisconceptionStep';
import WhiteRecallStep from '../components/study/WhiteRecallStep';
import SessionSummaryStep from '../components/study/SessionSummaryStep';
import ConfusionMapPanel from '../components/study/ConfusionMapPanel';

const STEP_LABELS = ['진단', '선행 확인', '표현 학습', '매핑 과제', '오개념 체크', '인출 연습', '세션 정리'];
const STEPS = ['diagnose', 'prerequisites', 'representations', 'mapping', 'misconceptions', 'recall', 'summary'];

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

  // MVP5-4B: Completion loop state
  // NOTE: selfExplanationResults, recallResult, completionResult are NOT restored from
  // sessionStorage on refresh. This is a known limitation — the user would need to re-submit
  // self-explanations and recall after a page refresh. The backend state tracks what was submitted,
  // so re-calling complete will still work if conditions are met.
  const [selfExplanationResults, setSelfExplanationResults] = useState<Record<string, SelfExplainResponse>>({});
  const [recallResult, setRecallResult] = useState<RecallSubmitResponse | null>(null);
  const [completionResult, setCompletionResult] = useState<CompleteStudySessionResponse | null>(null);
  const [completing, setCompleting] = useState(false);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [selfExplainSubmitting, setSelfExplainSubmitting] = useState(false);
  const [recallSubmitting, setRecallSubmitting] = useState(false);

  // MVP6: Mapping + Confusion Map state
  const [confusionMap, setConfusionMap] = useState<ConfusionMapData | null>(null);
  const [confusionMapLoading, setConfusionMapLoading] = useState(false);
  const [mappingTasks, setMappingTasks] = useState<MappingTaskItem[]>([]);
  const [mappingResults, setMappingResults] = useState<MappingSubmitResult[]>([]);

  useEffect(() => {
    initSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conceptId]);

  // MVP6: Load confusion map (best-effort, never blocks)
  async function loadConfusionMap(sid: string) {
    setConfusionMapLoading(true);
    try {
      const cmap = await getConfusionMap(sid);
      setConfusionMap(cmap);
    } catch {
      // best-effort — confusion map may not exist yet
    } finally {
      setConfusionMapLoading(false);
    }
  }

  // MVP6: Load mapping tasks (best-effort)
  async function loadMappingTasks(sid: string) {
    try {
      const resp = await getMappingTasks(sid);
      setMappingTasks(resp.tasks);
    } catch {
      // tasks may not exist yet
    }
  }

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
        // MVP6: restore confusion map + mapping tasks
        loadConfusionMap(sid);
        loadMappingTasks(sid);
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
      // MVP6: load confusion map after creation
      loadConfusionMap(resp.session_id);
      setLoading(false);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes('422') && msg.includes('소스 파일')) {
        setError('소스 파일을 먼저 업로드하세요.');
      } else if (msg.includes('422') && msg.includes('선행개념 독립 세션 미지원')) {
        setError('__unsupported_prerequisite__');
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
      // MVP6: refresh confusion map after diagnosis
      if (sessionId) loadConfusionMap(sessionId);
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
      // MVP6: refresh confusion map after advance
      loadConfusionMap(sessionId);
      // MVP6: load mapping tasks when entering mapping step
      const newStepName = STEPS[resp.current_step - 1];
      if (newStepName === 'mapping') {
        loadMappingTasks(sessionId);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setStepError(`단계 진행 실패: ${msg}`);
    } finally {
      setAdvancing(false);
    }
  }

  // --- MVP5-4B: Self-Explanation ---
  async function handleSubmitSelfExplanation(representationType: string, learnerExplanation: string): Promise<SelfExplainResponse> {
    if (!sessionId) throw new Error('No session');
    setSelfExplainSubmitting(true);
    setStepError(null);
    try {
      const result = await submitSelfExplanation(sessionId, {
        representation_type: representationType,
        learner_explanation: learnerExplanation,
      });
      setSelfExplanationResults(prev => ({ ...prev, [representationType]: result }));
      // MVP6: refresh confusion map after self-explanation
      loadConfusionMap(sessionId);
      return result;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setStepError(`자기 설명 제출 실패: ${msg}`);
      throw e;
    } finally {
      setSelfExplainSubmitting(false);
    }
  }

  // --- MVP5-4B: Recall ---
  async function handleSubmitRecall(learnerResponse: string): Promise<RecallSubmitResponse> {
    if (!sessionId) throw new Error('No session');
    setRecallSubmitting(true);
    setStepError(null);
    try {
      const result = await submitRecall(sessionId, {
        learner_response: learnerResponse,
      });
      setRecallResult(result);
      // MVP6: refresh confusion map after recall
      loadConfusionMap(sessionId);
      return result;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setStepError(`인출 제출 실패: ${msg}`);
      throw e;
    } finally {
      setRecallSubmitting(false);
    }
  }

  // --- MVP5-4B: Complete Session ---
  async function handleCompleteSession() {
    if (!sessionId || completing || completionResult) return;
    setCompleting(true);
    setCompletionError(null);
    try {
      const result = await completeStudySession(sessionId);
      setCompletionResult(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      // Extract detail from API error (format: "500 Internal Server Error: {json}")
      let detail = msg;
      try {
        const jsonStart = msg.indexOf('{');
        if (jsonStart !== -1) {
          const parsed = JSON.parse(msg.slice(jsonStart));
          detail = parsed.detail || msg;
        }
      } catch {
        // use raw message
      }
      setCompletionError(detail);
    } finally {
      setCompleting(false);
    }
  }

  // --- MVP6: Mapping Submit ---
  async function handleMappingSubmit(taskId: string, response: string): Promise<MappingSubmitResult> {
    if (!sessionId) throw new Error('No session');
    const result = await submitMapping(sessionId, taskId, response);
    setMappingResults(prev => [...prev, result]);
    setConfusionMap(result.confusion_map);
    return result;
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

  if (error === '__unsupported_prerequisite__') {
    return (
      <div>
        <h1 style={{ marginBottom: 8 }}>학습 세션: {concept}</h1>
        <div className="section">
          <div className="card" style={{ borderColor: '#f59e0b' }}>
            <p style={{ color: '#92400e', marginBottom: 12, fontWeight: 500 }}>
              이 선행개념은 아직 독립 학습 세션으로 제공되지 않습니다.
            </p>
            <p style={{ color: '#78716c', fontSize: 14, marginBottom: 16 }}>
              현재는 옹골성 세션 안에서 선행개념으로만 확인할 수 있습니다.
            </p>
            <Link to="/study/compactness" className="submit-btn" style={{ textDecoration: 'none', marginRight: 8 }}>
              옹골성 세션으로 돌아가기
            </Link>
            <Link to="/" className="submit-btn" style={{ textDecoration: 'none', background: '#64748b' }}>
              홈으로
            </Link>
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

  // MVP6: Steps 3-5 (mapping, misconceptions, recall) use split layout with confusion panel
  const showSplitLayout = displayStep >= 3 && displayStep <= 5;

  function renderStepContent() {
    if (!sessionData) return null;
    return (
      <>
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
            onSubmitSelfExplanation={handleSubmitSelfExplanation}
            selfExplanationResults={selfExplanationResults}
            selfExplainSubmitting={selfExplainSubmitting}
            advancing={advancing}
            readOnly={readOnly}
          />
        )}
        {displayStep === 3 && (
          <MappingCheckStep
            sessionId={sessionId!}
            tasks={mappingTasks}
            results={mappingResults}
            confusionMap={confusionMap}
            readOnly={readOnly}
            onTaskSubmit={handleMappingSubmit}
            onAllComplete={() => handleAdvance('mapping')}
          />
        )}
        {displayStep === 4 && (
          <MisconceptionStep
            misconceptions={sessionData.misconceptions}
            onNext={() => handleAdvance('misconceptions')}
            advancing={advancing}
            readOnly={readOnly}
          />
        )}
        {displayStep === 5 && (
          <WhiteRecallStep
            conceptId={concept}
            onSubmitRecall={handleSubmitRecall}
            onNext={() => handleAdvance('recall')}
            recallResult={recallResult}
            recallSubmitting={recallSubmitting}
            advancing={advancing}
            readOnly={readOnly}
          />
        )}
        {displayStep === 6 && (
          <SessionSummaryStep
            conceptId={concept}
            canonicalNameKo={sessionData.canonical_name_ko}
            stepsCompleted={stepsCompleted}
            confusionMap={confusionMap}
            onComplete={handleCompleteSession}
            completing={completing}
            completionResult={completionResult}
            completionError={completionError}
            onGoToStep={(step) => setViewingStep(step)}
          />
        )}
      </>
    );
  }

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>학습 세션: {sessionData.canonical_name_ko}</h1>

      <StudyStepper
        steps={STEP_LABELS}
        currentStep={displayStep}
        completedSteps={completedIndices}
      />

      <div className="section">
        {showSplitLayout ? (
          <div className="study-session-split">
            <div className="study-session-split__main">
              <div className="card">{renderStepContent()}</div>
            </div>
            <div className="study-session-split__panel">
              <ConfusionMapPanel confusionMap={confusionMap} loading={confusionMapLoading} />
            </div>
          </div>
        ) : (
          <div className="card">{renderStepContent()}</div>
        )}
      </div>

      {/* Navigation */}
      {viewingStep > 1 && displayStep < 6 && (
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
