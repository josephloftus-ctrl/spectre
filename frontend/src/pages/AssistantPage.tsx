import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
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
  X,
  RefreshCw,
  Shield,
  Users,
  Clipboard,
  FileText,
  Sunrise,
  BookOpen
} from 'lucide-react'
import { useChat, useNotes } from '@/hooks'
import { fetchSummary } from '@/lib/api'
import { checkAIStatus, STANDARD_MODEL } from '@/lib/ollama'
import { cn } from '@/lib/utils'
import { getMemory, deleteMemory, type MemoryItem } from '@/lib/db'
import { MarkdownMessage } from '@/components/MarkdownMessage'
import { TypingIndicator } from '@/components/TypingIndicator'

const API_BASE = ''

// ============ Types ============

interface StandupContent {
  date: string
  from_cache: boolean
  safety_moment: {
    content: string
    sources: string[]
    topic: string
  }
  dei_moment: {
    content: string
    observances: string[]
    date: string
  }
  manager_prompt: {
    content: string
    sources: string[]
    day: string
  }
  generated_at: string
}

interface HelpDeskResponse {
  answer: string
  confidence: 'high' | 'medium' | 'low'
  sources: string[]
  source_snippets?: { file: string; text: string }[]
}

// ============ API Functions ============

async function fetchStandup(date?: string): Promise<StandupContent> {
  const url = date
    ? `${API_BASE}/api/standup?date=${date}`
    : `${API_BASE}/api/standup`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch standup')
  return res.json()
}

async function rerollSection(section: string, topic?: string) {
  const formData = new FormData()
  if (topic) formData.append('topic', topic)

  const res = await fetch(`${API_BASE}/api/standup/reroll/${section}`, {
    method: 'POST',
    body: formData
  })
  if (!res.ok) throw new Error('Failed to reroll')
  return res.json()
}

async function askHelpDesk(question: string): Promise<HelpDeskResponse> {
  const formData = new FormData()
  formData.append('question', question)
  formData.append('include_sources', 'true')

  const res = await fetch(`${API_BASE}/api/helpdesk/ask`, {
    method: 'POST',
    body: formData
  })
  if (!res.ok) throw new Error('Failed to get answer')
  return res.json()
}

// ============ Standup Section Component ============

function StandupSection({
  title,
  icon: Icon,
  content,
  sources,
  section,
  onReroll,
  isRerolling
}: {
  title: string
  icon: React.ElementType
  content: string
  sources?: string[]
  section: string
  onReroll: (section: string) => void
  isRerolling: boolean
}) {
  const [expanded, setExpanded] = useState(true)

  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Icon className="h-5 w-5 text-primary" />
            {title}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onReroll(section)}
              disabled={isRerolling}
            >
              <RefreshCw className={cn("h-4 w-4", isRerolling && "animate-spin")} />
              <span className="ml-1 text-xs">Reroll</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExpanded(!expanded)}
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-2">
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <MarkdownMessage content={content || 'No content available'} />
          </div>
          {sources && sources.length > 0 && (
            <div className="mt-4 pt-3 border-t">
              <p className="text-xs text-muted-foreground mb-1">Sources:</p>
              <div className="flex flex-wrap gap-1">
                {sources.map((source, i) => (
                  <Badge key={i} variant="secondary" className="text-xs">
                    <FileText className="h-3 w-3 mr-1" />
                    {source}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  )
}

// ============ Standup Tab ============

function StandupTab() {
  const queryClient = useQueryClient()
  const [rerollingSection, setRerollingSection] = useState<string | null>(null)

  const { data: standup, isLoading, error } = useQuery({
    queryKey: ['standup'],
    queryFn: () => fetchStandup()
  })

  const rerollMutation = useMutation({
    mutationFn: ({ section }: { section: string }) => rerollSection(section),
    onMutate: ({ section }) => setRerollingSection(section),
    onSuccess: (data, { section }) => {
      queryClient.setQueryData(['standup'], (old: StandupContent | undefined) => {
        if (!old) return old
        const sectionKey = section === 'safety' ? 'safety_moment'
          : section === 'dei' ? 'dei_moment'
          : 'manager_prompt'
        return {
          ...old,
          [sectionKey]: data.content
        }
      })
      setRerollingSection(null)
    },
    onError: () => setRerollingSection(null)
  })

  const handleReroll = (section: string) => {
    rerollMutation.mutate({ section })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-2">Loading standup content...</span>
      </div>
    )
  }

  if (error || !standup) {
    return (
      <Card className="border-destructive">
        <CardContent className="py-8 text-center">
          <p className="text-destructive">Failed to load standup content</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['standup'] })}
          >
            Try Again
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            {standup.from_cache ? 'Pre-baked' : 'Generated'} for {standup.date}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => queryClient.invalidateQueries({ queryKey: ['standup'] })}
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh All
        </Button>
      </div>

      <StandupSection
        title="Safety Moment"
        icon={Shield}
        content={standup.safety_moment?.content}
        sources={standup.safety_moment?.sources}
        section="safety"
        onReroll={handleReroll}
        isRerolling={rerollingSection === 'safety'}
      />

      <StandupSection
        title="DEI Moment"
        icon={Users}
        content={standup.dei_moment?.content}
        sources={standup.dei_moment?.observances}
        section="dei"
        onReroll={handleReroll}
        isRerolling={rerollingSection === 'dei'}
      />

      <StandupSection
        title="Manager Prompt"
        icon={Clipboard}
        content={standup.manager_prompt?.content}
        sources={standup.manager_prompt?.sources}
        section="manager"
        onReroll={handleReroll}
        isRerolling={rerollingSection === 'manager'}
      />
    </div>
  )
}

// ============ Chat Tab ============

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'helpdesk'
  content: string
  helpdesk?: HelpDeskResponse
}

function ChatTab() {
  const [input, setInput] = useState('')
  const [showSessions, setShowSessions] = useState(false)
  const [showMemories, setShowMemories] = useState(false)
  const [allMemories, setAllMemories] = useState<MemoryItem[]>([])
  const [helpdeskLoading, setHelpdeskLoading] = useState(false)
  const [helpdeskMessages, setHelpdeskMessages] = useState<ChatMessage[]>([])
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

  useEffect(() => {
    if (showMemories) {
      getMemory(50).then(setAllMemories)
    }
  }, [showMemories, memories])

  const { notes } = useNotes()
  const { data: inventoryData } = useQuery({
    queryKey: ['summary'],
    queryFn: fetchSummary,
    refetchInterval: 30000
  })

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
    const memoryContent = content.length > 200 ? content.slice(0, 200) + '...' : content
    await saveMemory(memoryContent, 'fact')
  }

  const handleHelpDeskQuery = async (question: string) => {
    if (!question.trim() || helpdeskLoading) return

    // Add user message
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: question
    }
    setHelpdeskMessages(prev => [...prev, userMsg])
    setHelpdeskLoading(true)

    try {
      const response = await askHelpDesk(question)
      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'helpdesk',
        content: response.answer,
        helpdesk: response
      }
      setHelpdeskMessages(prev => [...prev, assistantMsg])
    } catch {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'helpdesk',
        content: 'Sorry, I could not search the training materials. Please try again.'
      }
      setHelpdeskMessages(prev => [...prev, errorMsg])
    } finally {
      setHelpdeskLoading(false)
    }
  }

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

  return (
    <div className="flex flex-col h-[calc(100vh-220px)]">
      {/* Session & Memory Controls */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="text-xs cursor-pointer hover:bg-muted"
            onClick={() => setShowMemories(!showMemories)}
          >
            <Brain className="h-3 w-3 mr-1" />
            {memories.length} memories
          </Badge>
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

      {/* Quick Actions */}
      {messages.length === 0 && helpdeskMessages.length === 0 && (
        <div className="grid gap-3 grid-cols-2 md:grid-cols-4 mb-6">
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

          <Card
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => handleHelpDeskQuery('What are the key food safety requirements I should know?')}
          >
            <CardContent className="p-4">
              <BookOpen className="h-8 w-8 text-green-500 mb-2" />
              <h3 className="font-semibold">Search Training</h3>
              <p className="text-sm text-muted-foreground">
                Find answers in training materials
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {/* Regular chat messages */}
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

        {/* Help desk messages */}
        {helpdeskMessages.map((msg) => (
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
                  : 'bg-green-500/10 border border-green-500/20'
              )}
            >
              {msg.role === 'helpdesk' && msg.helpdesk && (
                <div className="flex items-center gap-2 mb-2">
                  <BookOpen className="h-4 w-4 text-green-600" />
                  <span className="text-xs font-medium text-green-600">Training Materials</span>
                  <Badge className={cn(
                    "text-xs",
                    msg.helpdesk.confidence === 'high' && 'bg-green-500/10 text-green-600 border-green-500/20',
                    msg.helpdesk.confidence === 'medium' && 'bg-amber-500/10 text-amber-600 border-amber-500/20',
                    msg.helpdesk.confidence === 'low' && 'bg-red-500/10 text-red-600 border-red-500/20'
                  )}>
                    {msg.helpdesk.confidence}
                  </Badge>
                </div>
              )}
              {msg.role === 'helpdesk' ? (
                <>
                  <MarkdownMessage content={msg.content} className="text-sm" />
                  {msg.helpdesk?.sources && msg.helpdesk.sources.length > 0 && (
                    <div className="mt-3 pt-2 border-t border-green-500/20">
                      <p className="text-xs text-muted-foreground mb-1">Sources:</p>
                      <div className="flex flex-wrap gap-1">
                        {msg.helpdesk.sources.slice(0, 3).map((source, i) => (
                          <Badge key={i} variant="secondary" className="text-xs">
                            <FileText className="h-3 w-3 mr-1" />
                            {source}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
              )}
            </div>
          </div>
        ))}

        {streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg px-4 py-3 bg-muted">
              <MarkdownMessage content={streamingContent} className="text-sm" />
              <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />
            </div>
          </div>
        )}

        {isLoading && !streamingContent && (
          <div className="flex justify-start">
            <div className="rounded-lg px-4 py-3 bg-muted">
              <TypingIndicator />
            </div>
          </div>
        )}

        {helpdeskLoading && (
          <div className="flex justify-start">
            <div className="rounded-lg px-4 py-3 bg-green-500/10 border border-green-500/20">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-green-600" />
                <span className="text-sm text-green-600">Searching training materials...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="space-y-2">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about inventory, sites, notes, or training materials..."
            disabled={isLoading || helpdeskLoading}
            className="flex-1"
          />
          <Button type="submit" disabled={isLoading || helpdeskLoading || !input.trim()}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>

        {/* Help desk quick queries */}
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-muted-foreground self-center">Training:</span>
          <Badge
            variant="outline"
            className="cursor-pointer hover:bg-green-500/10 hover:border-green-500/30 text-xs"
            onClick={() => handleHelpDeskQuery('What are the hand washing requirements?')}
          >
            Hand washing
          </Badge>
          <Badge
            variant="outline"
            className="cursor-pointer hover:bg-green-500/10 hover:border-green-500/30 text-xs"
            onClick={() => handleHelpDeskQuery('How do I handle a food safety incident?')}
          >
            Food safety
          </Badge>
          <Badge
            variant="outline"
            className="cursor-pointer hover:bg-green-500/10 hover:border-green-500/30 text-xs"
            onClick={() => handleHelpDeskQuery('How do I store food properly?')}
          >
            Food storage
          </Badge>
          <Badge
            variant="outline"
            className="cursor-pointer hover:bg-green-500/10 hover:border-green-500/30 text-xs"
            onClick={() => handleHelpDeskQuery('What is the vacation policy?')}
          >
            HR policies
          </Badge>
        </div>
      </div>
    </div>
  )
}

// ============ Main Assistant Page ============

export function AssistantPage() {
  const navigate = useNavigate()
  const { data: aiStatus } = useQuery({
    queryKey: ['ai-status'],
    queryFn: checkAIStatus
  })

  const isAvailable = aiStatus?.available

  if (!isAvailable) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold font-head flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            Assistant
          </h1>
          <p className="text-muted-foreground">AI-powered help for inventory and operations</p>
        </div>

        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <Cpu className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <h2 className="text-lg font-semibold mb-2">AI Not Connected</h2>
            <p className="text-muted-foreground mb-4 max-w-md mx-auto">
              The AI service (Ollama with {STANDARD_MODEL}) is not available.
              Make sure Ollama is running.
            </p>
            <Button onClick={() => navigate('/settings')}>
              <Settings className="h-4 w-4 mr-2" />
              Go to Settings
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold font-head flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          Assistant
        </h1>
        <p className="text-muted-foreground text-sm">
          Powered by {STANDARD_MODEL}
        </p>
      </div>

      <Tabs defaultValue="chat" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 max-w-xs">
          <TabsTrigger value="chat" className="gap-2">
            <MessageSquare className="h-4 w-4" />
            Chat
          </TabsTrigger>
          <TabsTrigger value="standup" className="gap-2">
            <Sunrise className="h-4 w-4" />
            Standup
          </TabsTrigger>
        </TabsList>

        <TabsContent value="chat">
          <ChatTab />
        </TabsContent>

        <TabsContent value="standup">
          <StandupTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
