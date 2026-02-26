import { useState, useCallback, useRef, useEffect, type KeyboardEvent, type DragEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Send, ImagePlus, X } from 'lucide-react'
import { useDropzone } from 'react-dropzone'

interface ChatInputProps {
  readonly onSend: (message: string, imageData?: string) => void
  readonly disabled: boolean
}

interface ImagePreview {
  data: string
  name: string
}

const LINE_HEIGHT = 20
const MAX_LINES = 5
const MAX_HEIGHT = LINE_HEIGHT * MAX_LINES

// サポートする画像形式
const ACCEPTED_IMAGE_TYPES = {
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/gif': ['.gif'],
  'image/webp': ['.webp'],
}
const MAX_IMAGE_SIZE = 10 * 1024 * 1024 // 10MB

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('')
  const [imagePreview, setImagePreview] = useState<ImagePreview | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT)}px`
    }
  }, [input])

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if ((trimmed || imagePreview) && !disabled) {
      onSend(trimmed, imagePreview?.data)
      setInput('')
      setImagePreview(null)
      const textarea = textareaRef.current
      if (textarea) {
        textarea.style.height = 'auto'
      }
    }
  }, [input, disabled, onSend, imagePreview])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const processImage = useCallback((file: File) => {
    // ファイルサイズチェック
    if (file.size > MAX_IMAGE_SIZE) {
      alert('画像サイズが大きすぎます（最大10MB）')
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      const data = e.target?.result as string
      // Base64データ部分のみを抽出
      const base64Data = data.split(',')[1]
      setImagePreview({
        data: base64Data,
        name: file.name,
      })
    }
    reader.readAsDataURL(file)
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      processImage(file)
    }
    // 同じファイルを再度選択できるようにリセット
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [processImage])

  const handleRemoveImage = useCallback(() => {
    setImagePreview(null)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      const file = acceptedFiles[0]
      if (file) {
        processImage(file)
      }
      setIsDragOver(false)
    },
    onDragEnter: () => setIsDragOver(true),
    onDragLeave: () => setIsDragOver(false),
    accept: ACCEPTED_IMAGE_TYPES,
    maxSize: MAX_IMAGE_SIZE,
    noClick: true,
    noKeyboard: true,
  })

  return (
    <div 
      {...getRootProps()} 
      className={`flex flex-col gap-2 p-3 sm:p-4 border-t bg-card relative ${isDragActive || isDragOver ? 'ring-2 ring-primary ring-inset' : ''}`}
      role="form"
    >
      {/* ドラッグ&ドロップオーバーレイ */}
      {(isDragActive || isDragOver) && (
        <div className="absolute inset-0 bg-primary/10 flex items-center justify-center z-10 rounded">
          <div className="text-primary font-medium">
            画像をドロップしてください
          </div>
        </div>
      )}

      {/* 画像プレビュー */}
      {imagePreview && (
        <div className="relative inline-block">
          <div className="relative w-20 h-20 rounded overflow-hidden border">
            <img 
              src={`data:image/png;base64,${imagePreview.data}`} 
              alt="プレビュー" 
              className="w-full h-full object-cover"
            />
            <button
              onClick={handleRemoveImage}
              className="absolute -top-1 -right-1 w-5 h-5 bg-destructive text-destructive-foreground rounded-full flex items-center justify-center text-xs hover:bg-destructive/90"
              aria-label="画像を削除"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
          <div className="text-xs text-muted-foreground mt-1 truncate max-w-[80px]">
            {imagePreview.name}
          </div>
        </div>
      )}

      <div className="flex gap-2">
        {/* 画像添付ボタン */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
          onChange={handleFileSelect}
          className="hidden"
          aria-hidden="true"
        />
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled}
          aria-label="画像添付"
          className="min-w-[44px] min-h-[44px] shrink-0"
        >
          <ImagePlus className="h-5 w-5" />
        </Button>

        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="質問を入力してください..."
          disabled={disabled}
          rows={1}
          className="flex-1"
          aria-label="メッセージ入力"
        />
        <Button
          onClick={handleSend}
          disabled={disabled || (!input.trim() && !imagePreview)}
          size="icon"
          aria-label="送信"
          className="min-w-[44px] min-h-[44px] shrink-0"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      <input {...getInputProps()} />
    </div>
  )
}
