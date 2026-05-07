import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

interface RichMathTextProps {
  children: string;
  className?: string;
  inline?: boolean;
}

/**
 * Renders markdown with LaTeX math support.
 * - Inline math: $...$
 * - Block math: $$...$$
 * - Standard markdown: bold, italic, lists, code, etc.
 * - Tolerates raw text without crashing.
 */
export default function RichMathText({ children, className, inline }: RichMathTextProps) {
  if (!children) return null;

  if (inline) {
    return (
      <span className={className}>
        <ReactMarkdown
          remarkPlugins={[remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={{
            p: ({ children: c }) => <>{c}</>,
          }}
        >
          {children}
        </ReactMarkdown>
      </span>
    );
  }

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
