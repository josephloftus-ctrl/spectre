import { useState, useCallback, useEffect } from 'react'
import {
  createChatSession,
  getChatSessions,
  getChatMessages,
  addChatMessage,
  updateSessionTitle,
  deleteSession,
  getMemory,
  addMemory,
  ChatSession,
  ChatMessage as DbChatMessage
} from '@/lib/db'
import { chatStream, SYSTEM_PROMPTS } from '@/lib/ai'

// Operations-focused system prompt with memory injection
const buildSystemPrompt = (memories: string[]) => `${SYSTEM_PROMPTS.inventoryAnalyst}

${memories.length > 0 ? `\n## Remembered Context\n${memories.join('\n')}\n` : ''}

Always be concise and actionable. When you learn something important about the user's operations, sites, or preferences, mention it so they can save it to memory.`

export function useChat() {
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<DbChatMessage[]>([])
  const [memories, setMemories] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
    loadMemories()
  }, [])

  // Load messages when session changes
  useEffect(() => {
    if (currentSessionId) {
      loadMessages(currentSessionId)
    } else {
      setMessages([])
    }
  }, [currentSessionId])

  const loadSessions = async () => {
    const s = await getChatSessions()
    setSessions(s)
  }

  const loadMessages = async (sessionId: string) => {
    const m = await getChatMessages(sessionId)
    setMessages(m)
  }

  const loadMemories = async () => {
    const m = await getMemory(20)
    setMemories(m.map(i => `- ${i.content}`))
  }

  const startNewSession = useCallback(async () => {
    const session = await createChatSession()
    setSessions(prev => [session, ...prev])
    setCurrentSessionId(session.id)
    setMessages([])
    return session
  }, [])

  const selectSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return

    let sessionId = currentSessionId
    if (!sessionId) {
      const session = await startNewSession()
      sessionId = session.id
    }

    setIsLoading(true)
    setStreamingContent('')

    // Save user message
    const userMsg = await addChatMessage(sessionId, 'user', content)
    setMessages(prev => [...prev, userMsg])

    // Auto-title on first message
    const session = sessions.find(s => s.id === sessionId)
    if (session?.messageCount === 0) {
      const title = content.slice(0, 40) + (content.length > 40 ? '...' : '')
      await updateSessionTitle(sessionId, title)
      setSessions(prev => prev.map(s => s.id === sessionId ? { ...s, title } : s))
    }

    try {
      const chatMsgs = [...messages, userMsg].map(m => ({ role: m.role, content: m.content }))

      let fullResponse = ''
      for await (const chunk of chatStream(chatMsgs, buildSystemPrompt(memories))) {
        fullResponse += chunk
        setStreamingContent(fullResponse)
      }

      const assistantMsg = await addChatMessage(sessionId, 'assistant', fullResponse, 'claude')
      setMessages(prev => [...prev, assistantMsg])
      setStreamingContent('')
      await loadSessions()
    } catch (error) {
      const errMsg = await addChatMessage(sessionId, 'assistant', `Error: ${(error as Error).message}`)
      setMessages(prev => [...prev, errMsg])
    } finally {
      setIsLoading(false)
    }
  }, [currentSessionId, messages, memories, isLoading, sessions, startNewSession])

  const saveMemory = useCallback(async (content: string, category: 'fact' | 'preference' | 'procedure' | 'issue' = 'fact', importance?: number) => {
    await addMemory(content, category, importance)
    await loadMemories()
  }, [])

  const removeSession = useCallback(async (sessionId: string) => {
    await deleteSession(sessionId)
    if (currentSessionId === sessionId) {
      setCurrentSessionId(null)
      setMessages([])
    }
    await loadSessions()
  }, [currentSessionId])

  return {
    sessions,
    currentSessionId,
    messages,
    memories,
    isLoading,
    streamingContent,
    startNewSession,
    selectSession,
    sendMessage,
    saveMemory,
    removeSession
  }
}
