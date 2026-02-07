import { useState, useCallback, useEffect, useRef } from 'react'
import {
  ChatMessage,
  checkAIStatus,
  chatStream,
  chat,
  SYSTEM_PROMPTS
} from '@/lib/ai'

export interface UseAIOptions {
  systemPrompt?: string
  onError?: (error: Error) => void
  /** Polling interval in ms when connected (default: 60000) */
  pollInterval?: number
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected'

export function useAI(options: UseAIOptions = {}) {
  const { pollInterval = 60000 } = options

  const [isAvailable, setIsAvailable] = useState<boolean | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting')
  const [currentModel, setCurrentModel] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const abortedRef = useRef(false)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  const checkStatus = useCallback(async () => {
    const status = await checkAIStatus()
    setIsAvailable(status.available)
    setConnectionState(status.available ? 'connected' : 'disconnected')
    setCurrentModel(status.model || '')
  }, [])

  // Check status on mount and poll periodically
  useEffect(() => {
    checkStatus()
    timerRef.current = setInterval(checkStatus, pollInterval)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [checkStatus, pollInterval])

  const sendMessage = useCallback(async (content: string, streaming = true) => {
    if (!content.trim() || isLoading) return

    const userMessage: ChatMessage = { role: 'user', content }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setIsLoading(true)
    setStreamingContent('')
    abortedRef.current = false

    try {
      if (streaming) {
        let fullResponse = ''
        for await (const chunk of chatStream(newMessages, options.systemPrompt)) {
          if (abortedRef.current) break
          fullResponse += chunk
          setStreamingContent(fullResponse)
        }

        if (!abortedRef.current) {
          setMessages(prev => [...prev, { role: 'assistant', content: fullResponse }])
        }
        setStreamingContent('')
      } else {
        const response = await chat(newMessages, options.systemPrompt)
        if (!abortedRef.current) {
          setMessages(prev => [...prev, { role: 'assistant', content: response }])
        }
      }
    } catch (error) {
      if (abortedRef.current) return
      console.error('Chat error:', error)
      options.onError?.(error as Error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${(error as Error).message || 'Failed to get response.'}`
      }])
    } finally {
      setIsLoading(false)
    }
  }, [messages, isLoading, options])

  const clearMessages = useCallback(() => {
    setMessages([])
    setStreamingContent('')
  }, [])

  const abort = useCallback(() => {
    abortedRef.current = true
    setIsLoading(false)
    setStreamingContent('')
  }, [])

  return {
    isAvailable,
    connectionState,
    isLoading,
    currentModel,
    messages,
    streamingContent,
    checkStatus,
    sendMessage,
    clearMessages,
    abort
  }
}

// Specialized hook for inventory analysis
export function useInventoryAnalysis() {
  return useAI({
    systemPrompt: SYSTEM_PROMPTS.inventoryAnalyst
  })
}

// Specialized hook for note summarization
export function useNoteSummarizer() {
  const ai = useAI({
    systemPrompt: SYSTEM_PROMPTS.noteSummarizer
  })

  const summarizeNotes = useCallback(async (notes: string[]): Promise<string> => {
    if (!ai.isAvailable) {
      throw new Error('AI not available')
    }

    const prompt = `Please summarize these notes:\n\n${notes.map((n, i) => `${i + 1}. ${n}`).join('\n\n')}`

    return await chat([{ role: 'user', content: prompt }], SYSTEM_PROMPTS.noteSummarizer)
  }, [ai.isAvailable])

  return {
    ...ai,
    summarizeNotes
  }
}

// Specialized hook for anomaly detection
export function useAnomalyDetection() {
  return useAI({
    systemPrompt: SYSTEM_PROMPTS.anomalyDetector
  })
}
