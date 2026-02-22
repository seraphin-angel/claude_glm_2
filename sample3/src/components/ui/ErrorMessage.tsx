interface ErrorMessageProps {
  message: string
  'data-testid'?: string
}

export function ErrorMessage({ message, 'data-testid': testId }: ErrorMessageProps) {
  return (
    <p
      role="alert"
      className="text-sm text-red-600"
      data-testid={testId}
    >
      {message}
    </p>
  )
}
