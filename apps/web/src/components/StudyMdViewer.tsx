export default function StudyMdViewer({ content }: { content: string }) {
  if (!content) return <p className="empty-state">STUDY.md not found.</p>;
  return <pre className="pre-block">{content}</pre>;
}
