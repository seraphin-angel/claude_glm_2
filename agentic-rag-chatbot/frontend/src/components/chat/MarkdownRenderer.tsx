import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownRendererProps {
  readonly content: string
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="prose prose-sm dark:prose-invert max-w-none
      prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5
      prose-headings:my-2 prose-pre:my-2 prose-code:text-xs
      prose-a:text-blue-600 dark:prose-a:text-blue-400
      break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
