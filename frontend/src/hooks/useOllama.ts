import { useState, useCallback, useEffect, useRef } from 'react'
import {
  ChatMessage,
  OllamaModel,
  AIProvider,
  checkAIStatus,
  unifiedChatStream,
  unifiedChat,
  getAIConfig,
  saveAIConfig,
  SYSTEM_PROMPTS
} from '@/lib/ollama'

export interface UseOllamaOptions {
  systemPrompt?: string
  onError?: (error: Error) => void
  /** Polling interval in ms when connected (default: 30000) */
  pollInterval?: number
  /** Retry interval in ms when disconnected (default: 5000) */
  retryInterval?: number
  /** Maximum retry interval in ms (default: 30000) */
  maxRetryInterval?: number
}

export type ConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected'

export function useOllama(options: UseOllamaOptions = {}) {
  const {
    pollInterval = 30000,     // Check every 30s when connected
    retryInterval = 5000,     // Retry every 5s when disconnected
    maxRetryInterval = 30000  // Max retry interval (exponential backoff cap)
  } = options

  const [isAvailable, setIsAvailable] = useState<boolean | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting')
  const [models, setModels] = useState<OllamaModel[]>([])
  const [provider, setProvider] = useState<AIProvider>(getAIConfig().provider)
  const [currentModel, setCurrentModel] = useState(
    getAIConfig().provider === 'claude' ? getAIConfig().claudeModel : getAIConfig().ollamaModel
  )
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [streamingContent, setStreamingContent] = useState('')
  const abortRef = useRef<AbortController | null>(null)
  const abortedRef = useRef(false)
  const retryCountRef = useRef(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const isAvailableRef = useRef<boolean | null>(null)
  const checkStatusRef = useRef<() => Promise<void>>()

  // Keep ref in sync with state
  useEffect(() => {
    isAvailableRef.current = isAvailable
  }, [isAvailable])

  // Clear any existing timer
  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  // Check status implementation
  const checkStatusImpl = useCallback(async () => {
    const wasAvailable = isAvailableRef.current
    const status = await checkAIStatus()

    setIsAvailable(status.available)
    setModels(status.models)
    setProvider(status.provider)

    // Update connection state
    if (status.available) {
      setConnectionState('connected')
    } else if (wasAvailable === true) {
      // Was connected, now disconnected - reconnecting
      setConnectionState('reconnecting')
    } else if (wasAvailable === null) {
      // Initial connection attempt failed
      setConnectionState('disconnected')
    } else {
      // Still disconnected, keep reconnecting state
      setConnectionState('reconnecting')
    }

    // Update current model display
    const config = getAIConfig()
    setCurrentModel(config.provider === 'claude' ? config.claudeModel : config.ollamaModel)

    // Schedule next status check using ref to avoid stale closure
    clearTimer()
    if (status.available) {
      // Connected: poll at normal interval
      retryCountRef.current = 0
      timerRef.current = setTimeout(() => checkStatusRef.current?.(), pollInterval)
    } else {
      // Disconnected: use exponential backoff
      const backoffDelay = Math.min(
        retryInterval * Math.pow(2, retryCountRef.current),
        maxRetryInterval
      )
      retryCountRef.current++
      timerRef.current = setTimeout(() => checkStatusRef.current?.(), backoffDelay)
    }
  }, [pollInterval, retryInterval, maxRetryInterval, clearTimer])

  // Keep checkStatus ref updated
  useEffect(() => {
    checkStatusRef.current = checkStatusImpl
  }, [checkStatusImpl])

  // Public checkStatus function
  const checkStatus = useCallback(async () => {
    await checkStatusImpl()
  }, [checkStatusImpl])

  // Check status on mount and set up periodic polling
  useEffect(() => {
    checkStatusImpl()

    // Cleanup on unmount
    return () => clearTimer()
  }, [checkStatusImpl, clearTimer])

  const selectModel = useCallback((model: string) => {
    const config = getAIConfig()
    setCurrentModel(model)
    if (config.provider === 'claude') {
      saveAIConfig({ claudeModel: model })
    } else {
      saveAIConfig({ ollamaModel: model })
    }
  }, [])

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
        for await (const chunk of unifiedChatStream(newMessages, options.systemPrompt)) {
          // Check if aborted before processing each chunk
          if (abortedRef.current) {
            break
          }
          fullResponse += chunk
          setStreamingContent(fullResponse)
        }

        // Only save the response if not aborted
        if (!abortedRef.current) {
          setMessages(prev => [...prev, { role: 'assistant', content: fullResponse }])
        }
        setStreamingContent('')
      } else {
        const response = await unifiedChat(newMessages, options.systemPrompt)
        if (!abortedRef.current) {
          setMessages(prev => [...prev, { role: 'assistant', content: response }])
        }
      }
    } catch (error) {
      if (abortedRef.current) {
        // Don't show error for aborted requests
        return
      }
      console.error('Chat error:', error)
      options.onError?.(error as Error)
      // Keep the user message but add an error response
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${(error as Error).message || 'Failed to get response. Check console for details.'}`
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
    abortRef.current?.abort()
    setIsLoading(false)
    setStreamingContent('')
  }, [])

  return {
    isAvailable,
    connectionState,
    isLoading,
    models,
    provider,
    currentModel,
    messages,
    streamingContent,
    checkStatus,
    selectModel,
    sendMessage,
    clearMessages,
    abort
  }
}

// Specialized hook for inventory analysis
export function useInventoryAnalysis() {
  return useOllama({
    systemPrompt: SYSTEM_PROMPTS.inventoryAnalyst
  })
}

// Specialized hook for note summarization
export function useNoteSummarizer() {
  const ollama = useOllama({
    systemPrompt: SYSTEM_PROMPTS.noteSummarizer
  })

  const summarizeNotes = useCallback(async (notes: string[]): Promise<string> => {
    if (!ollama.isAvailable) {
      throw new Error('AI not available')
    }

    const prompt = `Please summarize these notes:\n\n${notes.map((n, i) => `${i + 1}. ${n}`).join('\n\n')}`

    return await unifiedChat([{ role: 'user', content: prompt }], SYSTEM_PROMPTS.noteSummarizer)
  }, [ollama.isAvailable])

  return {
    ...ollama,
    summarizeNotes
  }
}

// Specialized hook for anomaly detection
export function useAnomalyDetection() {
  return useOllama({
    systemPrompt: SYSTEM_PROMPTS.anomalyDetector
  })
}
