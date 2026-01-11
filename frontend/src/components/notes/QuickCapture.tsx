import { useState, useCallback, useEffect } from 'react'
import { Plus, Mic, MicOff, Send, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useVoice } from '@/hooks'
import { cn } from '@/lib/utils'

interface QuickCaptureProps {
  onSubmit: (content: string, isVoiceNote?: boolean) => void
}

export function QuickCapture({ onSubmit }: QuickCaptureProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [content, setContent] = useState('')
  const [isVoiceMode, setIsVoiceMode] = useState(false)
  const { isListening, transcript, start, stop, clear, isSupported } = useVoice()

  // Append transcript to content
  useEffect(() => {
    if (transcript) {
      setContent(prev => prev + (prev ? ' ' : '') + transcript)
      clear()
    }
  }, [transcript, clear])

  const handleSubmit = useCallback(() => {
    if (!content.trim()) return

    onSubmit(content.trim(), isVoiceMode)
    setContent('')
    setIsOpen(false)
    setIsVoiceMode(false)
    if (isListening) stop()
  }, [content, isVoiceMode, isListening, onSubmit, stop])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }, [handleSubmit])

  const handleVoiceToggle = useCallback(() => {
    if (isListening) {
      stop()
    } else {
      setIsVoiceMode(true)
      start()
    }
  }, [isListening, start, stop])

  const handleClose = useCallback(() => {
    setIsOpen(false)
    setContent('')
    setIsVoiceMode(false)
    if (isListening) stop()
  }, [isListening, stop])

  if (!isOpen) {
    return (
      <Button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg z-50"
        size="icon"
      >
        <Plus className="h-6 w-6" />
      </Button>
    )
  }

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm">
      <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4 pb-safe">
        <div className="max-w-2xl mx-auto space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Quick Capture</h3>
            <Button variant="ghost" size="icon" onClick={handleClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Input area */}
          <div className="relative">
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={isListening ? "Listening..." : "Type or speak..."}
              className={cn(
                "w-full min-h-[100px] p-4 rounded-lg border bg-muted/50 resize-none",
                "focus:outline-none focus:ring-2 focus:ring-primary",
                isListening && "border-red-500"
              )}
              autoFocus
            />

            {isListening && (
              <div className="absolute top-2 right-2 flex items-center gap-2 text-red-500 text-sm">
                <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                Recording
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {isSupported && (
                <Button
                  variant={isListening ? "destructive" : "outline"}
                  size="icon"
                  onClick={handleVoiceToggle}
                  className={cn(isListening && "animate-pulse")}
                >
                  {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                </Button>
              )}
              {isVoiceMode && !isListening && content && (
                <span className="text-xs text-muted-foreground">Voice note</span>
              )}
            </div>

            <Button
              onClick={handleSubmit}
              disabled={!content.trim()}
            >
              <Send className="h-4 w-4 mr-2" />
              Save Note
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
