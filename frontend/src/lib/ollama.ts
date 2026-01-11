// AI API client - supports Ollama (local) and Claude (API)

export type AIProvider = 'ollama' | 'claude'

export interface AIConfig {
  provider: AIProvider
  // Ollama settings
  ollamaUrl: string
  ollamaModel: string
  // Claude settings
  claudeApiKey: string
  claudeModel: string
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface OllamaResponse {
  model: string
  message: ChatMessage
  done: boolean
}

export interface OllamaModel {
  name: string
  size: number
  modified_at: string
}

// Standardized models - granite4:3b for LLM, nomic-embed-text for embeddings
export const STANDARD_MODEL = 'granite4:3b'
export const EMBED_MODEL = 'nomic-embed-text:v1.5'

const DEFAULT_CONFIG: AIConfig = {
  provider: 'ollama',
  // Use Vite proxy to avoid CORS issues (proxies to localhost:11434)
  ollamaUrl: '/ollama',
  ollamaModel: STANDARD_MODEL,
  claudeApiKey: '',
  claudeModel: 'claude-sonnet-4-20250514'
}

// Get config from localStorage
export function getAIConfig(): AIConfig {
  try {
    const stored = localStorage.getItem('ai_config')
    if (stored) {
      return { ...DEFAULT_CONFIG, ...JSON.parse(stored) }
    }
  } catch (e) {
    console.warn('Failed to load AI config:', e)
  }
  return DEFAULT_CONFIG
}

// Legacy support
export function getOllamaConfig() {
  const config = getAIConfig()
  return { baseUrl: config.ollamaUrl, model: config.ollamaModel }
}

// Save config to localStorage
export function saveAIConfig(config: Partial<AIConfig>): void {
  const current = getAIConfig()
  const updated = { ...current, ...config }
  localStorage.setItem('ai_config', JSON.stringify(updated))
}

// Legacy support
export function saveOllamaConfig(config: { baseUrl?: string; model?: string }): void {
  saveAIConfig({
    ollamaUrl: config.baseUrl,
    ollamaModel: config.model
  })
}

// Check if Ollama is available
export async function checkOllamaStatus(): Promise<{ available: boolean; models: OllamaModel[] }> {
  const config = getOllamaConfig()

  try {
    const response = await fetch(`${config.baseUrl}/api/tags`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    })

    if (!response.ok) {
      return { available: false, models: [] }
    }

    const data = await response.json()
    return { available: true, models: data.models || [] }
  } catch (e) {
    return { available: false, models: [] }
  }
}

// Chat with Ollama (streaming)
export async function* chatStream(
  messages: ChatMessage[],
  systemPrompt?: string
): AsyncGenerator<string, void, unknown> {
  const config = getOllamaConfig()

  const fullMessages: ChatMessage[] = systemPrompt
    ? [{ role: 'system', content: systemPrompt }, ...messages]
    : messages

  const response = await fetch(`${config.baseUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: config.model,
      messages: fullMessages,
      stream: true
    })
  })

  if (!response.ok) {
    throw new Error(`Ollama error: ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.trim()) continue
      try {
        const json = JSON.parse(line)
        if (json.message?.content) {
          yield json.message.content
        }
      } catch (e) {
        // Skip malformed JSON
      }
    }
  }
}

// Non-streaming chat
export async function chat(
  messages: ChatMessage[],
  systemPrompt?: string
): Promise<string> {
  const config = getOllamaConfig()

  const fullMessages: ChatMessage[] = systemPrompt
    ? [{ role: 'system', content: systemPrompt }, ...messages]
    : messages

  const response = await fetch(`${config.baseUrl}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: config.model,
      messages: fullMessages,
      stream: false
    })
  })

  if (!response.ok) {
    throw new Error(`Ollama error: ${response.status}`)
  }

  const data = await response.json()
  return data.message?.content || ''
}

// Generate embeddings (Ollama only)
export async function embed(text: string): Promise<number[]> {
  const config = getOllamaConfig()

  const response = await fetch(`${config.baseUrl}/api/embeddings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: config.model,
      prompt: text
    })
  })

  if (!response.ok) {
    throw new Error(`Ollama embedding error: ${response.status}`)
  }

  const data = await response.json()
  return data.embedding || []
}

// Check Claude API status
export async function checkClaudeStatus(): Promise<boolean> {
  const config = getAIConfig()
  if (!config.claudeApiKey) return false

  try {
    // Simple validation - check if key looks valid (format: sk-ant-api03-...)
    return config.claudeApiKey.startsWith('sk-ant-api03-')
  } catch {
    return false
  }
}

// Check overall AI status
export async function checkAIStatus(): Promise<{
  provider: AIProvider
  available: boolean
  models: OllamaModel[]
  claudeConfigured: boolean
}> {
  const config = getAIConfig()
  const ollamaStatus = await checkOllamaStatus()
  const claudeConfigured = await checkClaudeStatus()

  return {
    provider: config.provider,
    available: config.provider === 'ollama' ? ollamaStatus.available : claudeConfigured,
    models: ollamaStatus.models,
    claudeConfigured
  }
}

// Claude API chat (streaming)
export async function* claudeChatStream(
  messages: ChatMessage[],
  systemPrompt?: string
): AsyncGenerator<string, void, unknown> {
  const config = getAIConfig()

  if (!config.claudeApiKey) {
    throw new Error('Claude API key not configured')
  }

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': config.claudeApiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify({
      model: config.claudeModel,
      max_tokens: 4096,
      system: systemPrompt || '',
      messages: messages.filter(m => m.role !== 'system').map(m => ({
        role: m.role,
        content: m.content
      })),
      stream: true
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Claude error: ${response.status} - ${error}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data = line.slice(6)
      if (data === '[DONE]') continue

      try {
        const json = JSON.parse(data)
        if (json.type === 'content_block_delta' && json.delta?.text) {
          yield json.delta.text
        }
      } catch {
        // Skip malformed JSON
      }
    }
  }
}

// Claude API chat (non-streaming)
export async function claudeChat(
  messages: ChatMessage[],
  systemPrompt?: string
): Promise<string> {
  const config = getAIConfig()

  if (!config.claudeApiKey) {
    throw new Error('Claude API key not configured')
  }

  const response = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': config.claudeApiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify({
      model: config.claudeModel,
      max_tokens: 4096,
      system: systemPrompt || '',
      messages: messages.filter(m => m.role !== 'system').map(m => ({
        role: m.role,
        content: m.content
      }))
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Claude error: ${response.status} - ${error}`)
  }

  const data = await response.json()
  return data.content?.[0]?.text || ''
}

// Unified chat function - uses configured provider
export async function* unifiedChatStream(
  messages: ChatMessage[],
  systemPrompt?: string
): AsyncGenerator<string, void, unknown> {
  const config = getAIConfig()

  if (config.provider === 'claude') {
    yield* claudeChatStream(messages, systemPrompt)
  } else {
    yield* chatStream(messages, systemPrompt)
  }
}

export async function unifiedChat(
  messages: ChatMessage[],
  systemPrompt?: string
): Promise<string> {
  const config = getAIConfig()

  if (config.provider === 'claude') {
    return claudeChat(messages, systemPrompt)
  } else {
    return chat(messages, systemPrompt)
  }
}

// System prompts for different use cases
export const SYSTEM_PROMPTS = {
  inventoryAnalyst: `You are an inventory operations analyst assistant. You help analyze inventory data, identify trends, explain variances, and suggest actions.

When analyzing inventory:
- Focus on significant changes (>5% variance)
- Identify patterns across sites
- Flag potential issues proactively
- Suggest concrete actions
- Be concise and actionable

Format numbers clearly and use bullet points for lists.`,

  noteSummarizer: `You are a note summarization assistant. Given a collection of notes, extract key themes, action items, and important information.

When summarizing:
- Identify main topics
- Extract action items (things that need to be done)
- Note any deadlines or time-sensitive items
- Group related notes together
- Be concise but don't miss important details`,

  anomalyDetector: `You are an anomaly detection assistant for inventory management. Analyze data to identify unusual patterns, outliers, and potential issues.

When detecting anomalies:
- Compare against historical patterns
- Flag unexpected changes
- Consider seasonality and known factors
- Prioritize by impact
- Provide confidence levels when possible`
}
