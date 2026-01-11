import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  RefreshCw,
  Shield,
  Users,
  Clipboard,
  Send,
  Loader2,
  FileText,
  HelpCircle,
  Sunrise,
  BookOpen,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { MarkdownMessage } from '@/components/MarkdownMessage'

const API_BASE = ''

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

function StandupMode() {
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
      // Update the standup data with new section content
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

function HelpDeskMode() {
  const [question, setQuestion] = useState('')
  const [response, setResponse] = useState<HelpDeskResponse | null>(null)
  const [showSources, setShowSources] = useState(false)

  const askMutation = useMutation({
    mutationFn: askHelpDesk,
    onSuccess: setResponse
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!question.trim() || askMutation.isPending) return
    askMutation.mutate(question)
  }

  const confidenceColors = {
    high: 'bg-green-500/10 text-green-600 border-green-500/20',
    medium: 'bg-amber-500/10 text-amber-600 border-amber-500/20',
    low: 'bg-red-500/10 text-red-600 border-red-500/20'
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about food safety, HR policies, procedures..."
              disabled={askMutation.isPending}
              className="flex-1"
            />
            <Button type="submit" disabled={askMutation.isPending || !question.trim()}>
              {askMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>

          <div className="mt-4 flex flex-wrap gap-2">
            <Badge
              variant="outline"
              className="cursor-pointer hover:bg-muted"
              onClick={() => setQuestion('What are the hand washing requirements?')}
            >
              Hand washing
            </Badge>
            <Badge
              variant="outline"
              className="cursor-pointer hover:bg-muted"
              onClick={() => setQuestion('How do I handle a food safety incident?')}
            >
              Food safety
            </Badge>
            <Badge
              variant="outline"
              className="cursor-pointer hover:bg-muted"
              onClick={() => setQuestion('What is the vacation policy?')}
            >
              Vacation policy
            </Badge>
            <Badge
              variant="outline"
              className="cursor-pointer hover:bg-muted"
              onClick={() => setQuestion('How do I store food properly?')}
            >
              Food storage
            </Badge>
          </div>
        </CardContent>
      </Card>

      {askMutation.isPending && (
        <Card>
          <CardContent className="py-8 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
            <p className="mt-2 text-sm text-muted-foreground">Searching training materials...</p>
          </CardContent>
        </Card>
      )}

      {response && !askMutation.isPending && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <BookOpen className="h-5 w-5 text-primary" />
                Answer
              </CardTitle>
              <Badge className={confidenceColors[response.confidence]}>
                {response.confidence} confidence
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <MarkdownMessage content={response.answer} />
            </div>

            {response.sources && response.sources.length > 0 && (
              <div className="mt-4 pt-3 border-t">
                <button
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                  onClick={() => setShowSources(!showSources)}
                >
                  <FileText className="h-3 w-3" />
                  {response.sources.length} source{response.sources.length > 1 ? 's' : ''}
                  {showSources ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                </button>

                {showSources && (
                  <div className="mt-2 space-y-2">
                    {response.source_snippets?.map((snippet, i) => (
                      <div key={i} className="p-2 bg-muted rounded text-xs">
                        <div className="flex items-center gap-1 font-medium mb-1">
                          <FileText className="h-3 w-3" />
                          {snippet.file}
                        </div>
                        <p className="text-muted-foreground">{snippet.text}...</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {!response && !askMutation.isPending && (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <HelpCircle className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
            <h3 className="font-semibold mb-2">Ask the Help Desk</h3>
            <p className="text-sm text-muted-foreground max-w-md mx-auto">
              Search our training materials for answers about food safety, HR policies,
              procedures, and more. Answers are sourced directly from official documents.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export function StandupPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-head flex items-center gap-2">
          <Sunrise className="h-6 w-6 text-primary" />
          Daily Standup
        </h1>
        <p className="text-muted-foreground">Morning briefing and knowledge help desk</p>
      </div>

      <Tabs defaultValue="standup" className="space-y-4">
        <TabsList className="grid w-full grid-cols-2 max-w-md">
          <TabsTrigger value="standup" className="gap-2">
            <Sunrise className="h-4 w-4" />
            Standup
          </TabsTrigger>
          <TabsTrigger value="helpdesk" className="gap-2">
            <HelpCircle className="h-4 w-4" />
            Help Desk
          </TabsTrigger>
        </TabsList>

        <TabsContent value="standup">
          <StandupMode />
        </TabsContent>

        <TabsContent value="helpdesk">
          <HelpDeskMode />
        </TabsContent>
      </Tabs>
    </div>
  )
}
