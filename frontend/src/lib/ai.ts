// AI API client — all calls go through backend proxy (no direct browser API calls)

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface AIStatus {
  available: boolean
  model: string
  analysis_model: string
}

// Check AI availability via backend
export async function checkAIStatus(): Promise<AIStatus> {
  try {
    const response = await fetch('/api/ai/claude/status', {
      signal: AbortSignal.timeout(5000)
    })
    if (!response.ok) {
      return { available: false, model: '', analysis_model: '' }
    }
    return await response.json()
  } catch {
    return { available: false, model: '', analysis_model: '' }
  }
}

// Streaming chat via backend proxy
export async function* chatStream(
  messages: ChatMessage[],
  systemPrompt?: string
): AsyncGenerator<string, void, unknown> {
  const response = await fetch('/api/ai/claude/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      system: systemPrompt || undefined
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`AI error: ${response.status} - ${error}`)
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

// Non-streaming chat via backend proxy
export async function chat(
  messages: ChatMessage[],
  systemPrompt?: string
): Promise<string> {
  const response = await fetch('/api/ai/claude/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages: messages.map(m => ({ role: m.role, content: m.content })),
      system: systemPrompt || undefined
    })
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`AI error: ${response.status} - ${error}`)
  }

  const data = await response.json()
  return data.content?.[0]?.text || ''
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
