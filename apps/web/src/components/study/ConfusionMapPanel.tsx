import type { ConfusionMapData } from '../../api/types';

interface ConfusionMapPanelProps {
  confusionMap: ConfusionMapData | null;
  loading: boolean;
}

const MASTERY_INDICATOR: Record<string, { icon: string; color: string }> = {
  solid: { icon: '\u25CF', color: '#16a34a' },   // ● green
  partial: { icon: '\u25D0', color: '#ca8a04' },  // ◐ yellow
  unknown: { icon: '\u25CB', color: '#9ca3af' },  // ○ gray
};

export default function ConfusionMapPanel({ confusionMap, loading }: ConfusionMapPanelProps) {
  if (loading) {
    return (
      <div className="cmap-panel">
        <h3 className="cmap-title">혼동 지도</h3>
        <div className="cmap-skeleton">
          <div className="cmap-skeleton-bar" style={{ width: '80%' }} />
          <div className="cmap-skeleton-bar" style={{ width: '60%' }} />
          <div className="cmap-skeleton-bar" style={{ width: '70%' }} />
        </div>
      </div>
    );
  }

  if (!confusionMap) {
    return (
      <div className="cmap-panel">
        <h3 className="cmap-title">혼동 지도</h3>
        <p className="cmap-empty">진단을 시작하면 혼동 지도가 생성됩니다.</p>
      </div>
    );
  }

  const {
    prerequisite_nodes,
    mapping_edges,
    misconception_tags,
    next_recall_triggers,
    evidence_snippets,
    last_updated_step,
  } = confusionMap;

  return (
    <div className="cmap-panel">
      <h3 className="cmap-title">혼동 지도</h3>
      <div className="cmap-updated">마지막 갱신: {last_updated_step}</div>

      {/* Prerequisite Nodes */}
      {prerequisite_nodes.length > 0 && (
        <div className="cmap-section">
          <h4 className="cmap-section-label">선행 개념</h4>
          {prerequisite_nodes.map((node) => {
            const indicator = MASTERY_INDICATOR[node.mastery] ?? MASTERY_INDICATOR.unknown;
            return (
              <div key={node.concept_id} className="cmap-prereq-row">
                <span style={{ color: indicator.color }}>{indicator.icon}</span>
                <span className="cmap-prereq-id">{node.concept_id}</span>
                <span className="cmap-prereq-mastery">{node.mastery}</span>
                {node.self_reported && (
                  <span className="cmap-prereq-self">({node.self_reported})</span>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Mapping Edges */}
      {mapping_edges.length > 0 && (
        <div className="cmap-section">
          <h4 className="cmap-section-label">매핑 연결</h4>
          {mapping_edges.map((edge) => {
            const icon = edge.passed ? '\u2713' : '\u2717'; // ✓ or ✗
            const color = edge.passed ? '#16a34a' : '#dc2626';
            return (
              <div key={edge.task_type} className="cmap-edge-row">
                <span style={{ color, fontWeight: 700 }}>{icon}</span>
                <span>{edge.from_rep} → {edge.to_rep}</span>
                <span className="cmap-edge-score">({edge.score.toFixed(1)})</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Misconception Tags */}
      {misconception_tags.length > 0 && (
        <div className="cmap-section">
          <h4 className="cmap-section-label">활성 오개념</h4>
          {misconception_tags.map((tag) => (
            <div key={tag} className="cmap-misconception-tag">
              <span className="cmap-misconception-dot">&bull;</span> {tag}
            </div>
          ))}
        </div>
      )}

      {/* Recall Triggers */}
      {next_recall_triggers.length > 0 && (
        <div className="cmap-section">
          <h4 className="cmap-section-label">인출 과제</h4>
          {next_recall_triggers.map((trigger, i) => (
            <div key={i} className="cmap-trigger-row">
              <span className="cmap-trigger-arrow">&rarr;</span>
              <span className="cmap-trigger-text">{trigger}</span>
            </div>
          ))}
        </div>
      )}

      {/* Evidence Snippets */}
      {evidence_snippets.length > 0 && (
        <div className="cmap-section">
          <h4 className="cmap-section-label">증거</h4>
          {evidence_snippets.map((snippet, i) => (
            <div key={i} className="cmap-evidence-item">
              <div className="cmap-evidence-step">[{snippet.step}]</div>
              <div className="cmap-evidence-text">&ldquo;{snippet.learner_text}&rdquo;</div>
              <div className="cmap-evidence-issue">&rarr; {snippet.issue}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
