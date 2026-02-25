import type { SourceDocument, QualityScore } from '@/types/message'

interface SourceCitationsProps {
  readonly sources: readonly SourceDocument[]
  readonly qualityScore?: QualityScore
}

interface SourceCardProps {
  readonly source: SourceDocument
}

function SourceCard({ source }: SourceCardProps) {
  const scorePercent = Math.round(source.score * 100)
  const scoreColor =
    scorePercent >= 80
      ? 'text-green-600'
      : scorePercent >= 50
        ? 'text-yellow-600'
        : 'text-red-600'

  return (
    <div className="rounded-md border border-gray-200 bg-gray-50 p-3 text-sm">
      <div className="mb-1 flex items-start justify-between">
        <div className="font-medium text-gray-900">{source.title || '不明'}</div>
        <span className={`ml-2 shrink-0 font-mono text-xs ${scoreColor}`}>
          {scorePercent}%
        </span>
      </div>
      {source.section && (
        <div className="mb-1 text-xs text-gray-500">セクション: {source.section}</div>
      )}
      <p className="line-clamp-2 text-gray-600">{source.snippet}</p>
    </div>
  )
}

export function SourceCitations({ sources, qualityScore }: SourceCitationsProps) {
  if (sources.length === 0) {
    return null
  }

  const confidencePercent = qualityScore
    ? Math.round(qualityScore.confidence * 100)
    : null
  const confidenceColor =
    confidencePercent !== null
      ? confidencePercent >= 80
        ? 'text-green-600'
        : confidencePercent >= 50
          ? 'text-yellow-600'
          : 'text-red-600'
      : ''

  return (
    <details className="mt-3 rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
      <summary className="flex cursor-pointer items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
        <span className="shrink-0">📚</span>
        <span>
          参照元 ({sources.length}件)
          {confidencePercent !== null && (
            <span className={`ml-2 ${confidenceColor}`}>
              信頼度: {confidencePercent}%
            </span>
          )}
        </span>
      </summary>
      <div className="mt-3 space-y-2">
        {sources.map((source) => (
          <SourceCard key={source.id} source={source} />
        ))}
        {qualityScore?.reasoning && (
          <div className="mt-3 border-t border-gray-200 pt-3">
            <div className="text-xs font-medium text-gray-500">評価理由:</div>
            <p className="mt-1 text-xs text-gray-600">{qualityScore.reasoning}</p>
          </div>
        )}
      </div>
    </details>
  )
}
