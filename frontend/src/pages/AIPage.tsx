import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Send,
  Cpu,
  Loader2,
  Trash2,
  Sparkles,
  AlertTriangle,
  TrendingUp,
  StickyNote,
  Settings,
  Plus,
  MessageSquare,
  Brain,
  ChevronDown,
  ChevronUp,
  Bookmark,
  X
} from 'lucide-react'
import { useChat, useNotes } from '@/hooks'
import { fetchSummary } from '@/lib/api'
import { checkAIStatus, getAIConfig, saveAIConfig, checkOllamaStatus } from '@/lib/ollama'
import { cn } from '@/lib/utils'
import { getMemory, deleteMemory, type MemoryItem } from '@/lib/db'
import { MarkdownMessage } from '@/components/MarkdownMessage'
import { TypingIndicator } from '@/components/TypingIndicator'

const CLAUDE_MODELS = [
  { id: 'claude-sonnet-4-20250514', name: 'Sonnet 4' },
  { id: 'claude-3-5-sonnet-20241022', name: 'Sonnet 3.5' },
  { id: 'claude-3-haiku-20240307', name: 'Haiku' },
]

export function AIPage() {
  const navigate = useNavigate()
  const [input, setInput] = useState('')
  const [showSessions, setShowSessions] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [showMemories, setShowMemories] = useState(false)
  const [allMemories, setAllMemories] = useState<MemoryItem[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    sessions,
    currentSessionId,
    messages,
    memories,
    isLoading,
    streamingContent,
    startNewSession,
    selectSession,
    sendMessage: chatSendMessage,
    saveMemory,
    removeSession
  } = useChat()

  // Load all memories when panel opens
  useEffect(() => {
    if (showMemories) {
      getMemory(50).then(setAllMemories)
    }
  }, [showMemories, memories])

  const { data: aiStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['ai-status'],
    queryFn: checkAIStatus
  })

  const { data: ollamaModels } = useQuery({
    queryKey: ['ollama-models'],
    queryFn: async () => {
      const status = await checkOllamaStatus()
      return status.models
    }
  })

  const config = getAIConfig()
  const isAvailable = aiStatus?.available

  const switchProvider = (provider: 'ollama' | 'claude') => {
    saveAIConfig({ provider })
    refetchStatus()
  }

  const switchModel = (model: string) => {
    if (config.provider === 'claude') {
      saveAIConfig({ claudeModel: model })
    } else {
      saveAIConfig({ ollamaModel: model })
    }
    refetchStatus()
  }

  const { notes } = useNotes()
  const { data: inventoryData } = useQuery({
    queryKey: ['summary'],
    queryFn: fetchSummary,
    refetchInterval: 30000
  })

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    chatSendMessage(input)
    setInput('')
  }

  const handleQuickAction = (prompt: string) => {
    chatSendMessage(prompt)
  }

  const handleDeleteMemory = async (id: string) => {
    await deleteMemory(id)
    setAllMemories(prev => prev.filter(m => m.id !== id))
  }

  const handleSaveAsMemory = async (content: string) => {
    // Extract first 200 chars as memory
    const memoryContent = content.length > 200 ? content.slice(0, 200) + '...' : content
    await saveMemory(memoryContent, 'fact')
  }

  // Build context for AI
  const buildContextPrompt = (action: string): string => {
    let context = action + '\n\nCurrent Data Context:\n'

    if (inventoryData) {
      context += `\nInventory Summary:
- Total Value: $${inventoryData.global_value.toLocaleString()}
- Active Sites: ${inventoryData.active_sites}
- Total Issues: ${inventoryData.total_issues}

Sites:\n`
      inventoryData.sites.forEach(site => {
        context += `- ${site.site}: $${site.latest_total.toLocaleString()} (${site.delta_pct > 0 ? '+' : ''}${site.delta_pct.toFixed(1)}% change, ${site.issue_count} issues)\n`
      })
    }

    if (notes.length > 0) {
      context += `\nRecent Notes (${notes.length} total):\n`
      notes.slice(0, 5).forEach((note, i) => {
        context += `${i + 1}. ${note.content.substring(0, 100)}${note.content.length > 100 ? '...' : ''}\n`
      })
    }

    return context
  }

  if (!isAvailable) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold font-head">AI Assistant</h1>
          <p className="text-muted-foreground">Chat with AI about your inventory data</p>
        </div>

        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Cpu className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <h2 className="text-lg font-semibold mb-2">AI Not Connected</h2>
            <p className="text-muted-foreground mb-4 max-w-md mx-auto">
              Configure an AI provider in Settings to enable AI features.
              You can use <strong>Ollama</strong> (local, free) or <strong>Claude API</strong> (cloud).
            </p>
            <div className="space-y-2">
              <Button onClick={() => navigate('/settings')}>
                <Settings className="h-4 w-4 mr-2" />
                Go to Settings
              </Button>
              <p className="text-xs text-muted-foreground">
                For Ollama: click Reset next to URL field, then Refresh
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold font-head flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            AI Assistant
          </h1>
          <div className="flex items-center gap-2 mt-1">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Badge variant="secondary" className="text-xs cursor-pointer hover:bg-muted/80 gap-1">
                  {aiStatus?.provider === 'claude' ? 'Claude' : 'Ollama'}
                  <span className="text-muted-foreground">|</span>
                  <span className="font-mono">
                    {config.provider === 'claude'
                      ? CLAUDE_MODELS.find(m => m.id === config.claudeModel)?.name || config.claudeModel.split('-')[1]
                      : config.ollamaModel?.split(':')[0].split('/').pop() || 'default'}
                  </span>
                  <ChevronDown className="h-3 w-3 ml-0.5" />
                </Badge>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-48">
                <DropdownMenuLabel>Provider</DropdownMenuLabel>
                <DropdownMenuItem
                  onClick={() => switchProvider('ollama')}
                  className={config.provider === 'ollama' ? 'bg-accent' : ''}
                >
                  Ollama (Local)
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => switchProvider('claude')}
                  className={config.provider === 'claude' ? 'bg-accent' : ''}
                >
                  Claude (API)
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuLabel>Model</DropdownMenuLabel>
                {config.provider === 'ollama' ? (
                  ollamaModels?.map(m => (
                    <DropdownMenuItem
                      key={m.name}
                      onClick={() => switchModel(m.name)}
                      className={config.ollamaModel === m.name ? 'bg-accent' : ''}
                    >
                      {m.name.split(':')[0].split('/').pop()}
                    </DropdownMenuItem>
                  ))
                ) : (
                  CLAUDE_MODELS.map(m => (
                    <DropdownMenuItem
                      key={m.id}
                      onClick={() => switchModel(m.id)}
                      className={config.claudeModel === m.id ? 'bg-accent' : ''}
                    >
                      {m.name}
                    </DropdownMenuItem>
                  ))
                )}
              </DropdownMenuContent>
            </DropdownMenu>
            <Badge
              variant="outline"
              className="text-xs cursor-pointer hover:bg-muted"
              onClick={() => setShowMemories(!showMemories)}
            >
              <Brain className="h-3 w-3 mr-1" />
              {memories.length} memories
            </Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowSessions(!showSessions)}>
            <MessageSquare className="h-4 w-4 mr-2" />
            {sessions.length} chats
          </Button>
          <Button variant="default" size="sm" onClick={startNewSession}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Session List */}
      {showSessions && sessions.length > 0 && (
        <div className="mb-4 p-2 bg-muted rounded-lg max-h-32 overflow-y-auto">
          {sessions.map(s => (
            <div
              key={s.id}
              className={cn(
                "flex justify-between items-center p-2 rounded cursor-pointer hover:bg-background",
                currentSessionId === s.id && "bg-background"
              )}
              onClick={() => { selectSession(s.id); setShowSessions(false) }}
            >
              <span className="text-sm truncate flex-1">{s.title}</span>
              <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); removeSession(s.id) }}>
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          ))}
        </div>
      )}

      {/* Memory Panel */}
      {showMemories && (
        <div className="mb-4 p-3 bg-muted/50 rounded-lg border">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Brain className="h-4 w-4" />
              Saved Memories
            </h3>
            <Button variant="ghost" size="sm" onClick={() => setShowMemories(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
          {allMemories.length === 0 ? (
            <p className="text-xs text-muted-foreground">No memories saved yet. Click the bookmark icon on AI responses to save them.</p>
          ) : (
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {allMemories.map(mem => (
                <div key={mem.id} className="flex items-start gap-2 p-2 bg-background rounded text-xs">
                  <span className="flex-1">{mem.content}</span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                    onClick={() => handleDeleteMemory(mem.id)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Advanced Settings (discrete) */}
      <div className="mb-4">
        <button
          className="text-xs text-muted-foreground flex items-center gap-1 hover:text-foreground"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          {showAdvanced ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          Advanced
        </button>
        {showAdvanced && (
          <div className="mt-2 p-3 bg-muted/50 rounded-lg space-y-3">
            {/* Provider Toggle */}
            <div className="flex gap-2">
              <Button
                variant={config.provider === 'ollama' ? 'default' : 'outline'}
                size="sm"
                onClick={() => switchProvider('ollama')}
              >
                Ollama
              </Button>
              <Button
                variant={config.provider === 'claude' ? 'default' : 'outline'}
                size="sm"
                onClick={() => switchProvider('claude')}
              >
                Claude
              </Button>
            </div>

            {/* Model Selection */}
            <div className="flex flex-wrap gap-1">
              {config.provider === 'ollama' ? (
                ollamaModels?.map(m => (
                  <Button
                    key={m.name}
                    variant={config.ollamaModel === m.name ? 'secondary' : 'ghost'}
                    size="sm"
                    className="text-xs h-7"
                    onClick={() => switchModel(m.name)}
                  >
                    {m.name.split(':')[0].split('/').pop()}
                  </Button>
                ))
              ) : (
                CLAUDE_MODELS.map(m => (
                  <Button
                    key={m.id}
                    variant={config.claudeModel === m.id ? 'secondary' : 'ghost'}
                    size="sm"
                    className="text-xs h-7"
                    onClick={() => switchModel(m.id)}
                  >
                    {m.name}
                  </Button>
                ))
              )}
            </div>

            {/* Current Model Display */}
            <p className="text-xs text-muted-foreground font-mono">
              {config.provider === 'claude' ? config.claudeModel : config.ollamaModel}
            </p>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      {messages.length === 0 && (
        <div className="grid gap-3 md:grid-cols-3 mb-6">
          <Card
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => handleQuickAction(buildContextPrompt('Analyze the current inventory status. What are the key insights and any concerns?'))}
          >
            <CardContent className="p-4">
              <TrendingUp className="h-8 w-8 text-primary mb-2" />
              <h3 className="font-semibold">Analyze Inventory</h3>
              <p className="text-sm text-muted-foreground">
                Get insights on current status and trends
              </p>
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => handleQuickAction(buildContextPrompt('Review all sites and flag any that need attention. Explain why.'))}
          >
            <CardContent className="p-4">
              <AlertTriangle className="h-8 w-8 text-amber-500 mb-2" />
              <h3 className="font-semibold">Find Issues</h3>
              <p className="text-sm text-muted-foreground">
                Identify sites needing attention
              </p>
            </CardContent>
          </Card>

          <Card
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => handleQuickAction(buildContextPrompt('Summarize my recent notes. Extract any action items or important points.'))}
          >
            <CardContent className="p-4">
              <StickyNote className="h-8 w-8 text-blue-500 mb-2" />
              <h3 className="font-semibold">Summarize Notes</h3>
              <p className="text-sm text-muted-foreground">
                Get a summary of your recent notes
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex group",
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            <div
              className={cn(
                "max-w-[80%] rounded-lg px-4 py-3 relative",
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted'
              )}
            >
              {msg.role === 'assistant' ? (
                <MarkdownMessage content={msg.content} className="text-sm" />
              ) : (
                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
              )}
              {msg.role === 'assistant' && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute -right-8 top-1 opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0"
                  onClick={() => handleSaveAsMemory(msg.content)}
                  title="Save to memory"
                >
                  <Bookmark className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>
        ))}

        {/* Streaming response */}
        {streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg px-4 py-3 bg-muted">
              <MarkdownMessage content={streamingContent} className="text-sm" />
              <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
            </div>
          </div>
        )}

        {/* Typing indicator */}
        {isLoading && !streamingContent && (
          <div className="flex justify-start">
            <div className="rounded-lg px-4 py-3 bg-muted">
              <TypingIndicator />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your inventory, sites, or notes..."
          disabled={isLoading}
          className="flex-1"
        />
        <Button type="submit" disabled={isLoading || !input.trim()}>
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </form>
    </div>
  )
}
