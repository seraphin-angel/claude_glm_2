export const TOOL_LABELS: Record<string, string> = {
  search_knowledge: 'ナレッジ検索',
  check_relevance: '関連性チェック',
  generate_answer: '回答生成',
}

export function getToolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] ?? toolName
}
