import { jsx as _jsx } from "react/jsx-runtime";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
export function Markdown({ content }) {
    // Handle empty or undefined content
    const safeContent = content?.trim() || "";
    if (!safeContent) {
        return _jsx("div", { className: "markdown text-muted-foreground italic", children: "No content" });
    }
    return (_jsx("div", { className: "markdown", children: _jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: safeContent }) }));
}
