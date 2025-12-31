import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownProps {
  content: string;
}

export function Markdown({ content }: MarkdownProps) {
  // Handle empty or undefined content
  const safeContent = content?.trim() || "";

  if (!safeContent) {
    return <div className="markdown text-muted-foreground italic">No content</div>;
  }

  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{safeContent}</ReactMarkdown>
    </div>
  );
}
