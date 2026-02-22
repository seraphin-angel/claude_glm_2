import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { HITLRequest } from '@/types/message'
import { ClarificationButtons } from './ClarificationButtons'
import { ClarificationInput } from './ClarificationInput'

interface HITLWidgetProps {
  readonly request: HITLRequest
  readonly onRespond: (response: string) => void
  readonly disabled: boolean
}

export function HITLWidget({ request, onRespond, disabled }: HITLWidgetProps) {
  return (
    <div className="flex w-full justify-start mb-4">
      <Card className="max-w-[85%] border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Badge variant="outline" className="text-amber-700 border-amber-300 dark:text-amber-300 dark:border-amber-700">
              確認
            </Badge>
          </div>
          <p className="text-sm text-foreground mb-3">{request.question}</p>

          {request.input_type === 'buttons' && request.options ? (
            <ClarificationButtons
              options={request.options}
              onSelect={onRespond}
              disabled={disabled}
            />
          ) : (
            <ClarificationInput
              onSubmit={onRespond}
              disabled={disabled}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
