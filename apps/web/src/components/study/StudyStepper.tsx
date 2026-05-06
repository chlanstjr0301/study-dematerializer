interface StudyStepperProps {
  steps: string[];
  currentStep: number;
  completedSteps: number[];
}

export default function StudyStepper({ steps, currentStep, completedSteps }: StudyStepperProps) {
  return (
    <div style={{
      display: 'flex', gap: 4, marginBottom: 24,
      overflowX: 'auto', padding: '4px 0',
    }}>
      {steps.map((label, i) => {
        const isCompleted = completedSteps.includes(i);
        const isCurrent = i === currentStep;
        const bg = isCurrent ? '#1d4ed8' : isCompleted ? '#15803d' : '#e5e7eb';
        const color = isCurrent || isCompleted ? '#fff' : '#6b7280';
        return (
          <div
            key={i}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 20,
              background: bg, color,
              fontSize: 13, fontWeight: isCurrent ? 600 : 400,
              whiteSpace: 'nowrap',
            }}
          >
            <span style={{
              width: 20, height: 20, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: isCurrent || isCompleted ? 'rgba(255,255,255,0.25)' : '#d1d5db',
              fontSize: 11, fontWeight: 600,
            }}>
              {isCompleted ? '✓' : i + 1}
            </span>
            {label}
          </div>
        );
      })}
    </div>
  );
}
