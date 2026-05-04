export default function MermaidPreview({ text, label }: { text: string; label: string }) {
  return (
    <div>
      <h4 style={{ marginBottom: 8 }}>{label}</h4>
      <pre className="pre-block">{text}</pre>
    </div>
  );
}
