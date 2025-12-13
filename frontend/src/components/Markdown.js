import { jsx as _jsx } from "react/jsx-runtime";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
export function Markdown({ content }) {
    return _jsx(ReactMarkdown, { remarkPlugins: [remarkGfm], children: content });
}
