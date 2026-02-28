import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { logger } from '@/lib/logger'

interface ErrorBoundaryProps {
  readonly children: ReactNode
}

interface ErrorBoundaryState {
  readonly hasError: boolean
  readonly error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.error('ErrorBoundary', {
      message: 'React component error caught',
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
    })

    // In production, send to Sentry or similar
    // if (process.env.NODE_ENV === 'production') {
    //   Sentry.captureException(error, { contexts: { react: { componentStack: errorInfo.componentStack } } })
    // }
  }

  render() {
    if (this.state.hasError) {
      return (
        <Card className="m-4">
          <CardContent className="p-6 text-center">
            <h2 className="text-lg font-bold text-red-600 mb-2">
              予期しないエラーが発生しました
            </h2>
            <p className="text-sm text-muted-foreground mb-4">
              {this.state.error?.message ?? '不明なエラー'}
            </p>
            <Button
              onClick={() => this.setState({ hasError: false, error: null })}
              variant="outline"
            >
              再試行
            </Button>
          </CardContent>
        </Card>
      )
    }

    return this.props.children
  }
}
