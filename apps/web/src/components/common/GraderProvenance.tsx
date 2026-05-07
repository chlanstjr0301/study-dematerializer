interface GraderProvenanceProps {
  graderSource?: string;
}

/**
 * Renders grader source/hash metadata inside a collapsible <details> element.
 * Only renders if graderSource is a non-empty string.
 */
export default function GraderProvenance({ graderSource }: GraderProvenanceProps) {
  if (!graderSource) return null;

  return (
    <details className="grader-provenance">
      <summary>출처 정보 보기</summary>
      <pre className="grader-provenance__content">{graderSource}</pre>
    </details>
  );
}
