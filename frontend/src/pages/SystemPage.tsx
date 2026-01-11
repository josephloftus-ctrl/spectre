import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { fetchStats, fetchWorkerStatus, fetchEmbeddingStats, fetchAnomalies, fetchJobs } from '@/lib/api'
import { checkAIStatus } from '@/lib/ollama'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Activity,
  Cpu,
  Database,
  FileSpreadsheet,
  Cog,
  Clock,
  Sparkles,
  AlertTriangle,
  TrendingUp,
  RefreshCw,
  Server,
  Zap
} from 'lucide-react'
import { cn } from '@/lib/utils'

export function SystemPage() {
  const navigate = useNavigate()

  const { data: aiStatus, refetch: refetchAI } = useQuery({
    queryKey: ['ai-status'],
    queryFn: checkAIStatus,
    refetchInterval: 30000
  })

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['system-stats'],
    queryFn: fetchStats,
    refetchInterval: 5000
  })

  const { data: workerStatus, refetch: refetchWorker } = useQuery({
    queryKey: ['worker-status'],
    queryFn: fetchWorkerStatus,
    refetchInterval: 10000
  })

  const { data: embeddingStats, refetch: refetchEmbeddings } = useQuery({
    queryKey: ['embedding-stats'],
    queryFn: fetchEmbeddingStats,
    refetchInterval: 30000
  })

  const { data: anomaliesData } = useQuery({
    queryKey: ['anomalies'],
    queryFn: () => fetchAnomalies(10),
    refetchInterval: 30000
  })

  const { data: jobsData } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => fetchJobs({ limit: 20 }),
    refetchInterval: 5000
  })

  const handleRefreshAll = () => {
    refetchAI()
    refetchStats()
    refetchWorker()
    refetchEmbeddings()
  }

  const recentJobs = jobsData?.jobs?.slice(0, 10) || []
  const runningJobs = recentJobs.filter((j) => j.status === 'running')
  const queuedJobs = recentJobs.filter((j) => j.status === 'queued')

  return (
    <div className="space-y-6 animate-page-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-head flex items-center gap-2">
            <Server className="h-6 w-6 text-primary" />
            System
          </h1>
          <p className="text-muted-foreground text-sm">
            Backend services, jobs, and AI status
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefreshAll}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Service Status Grid */}
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Worker Status */}
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-3">
              <div className={cn(
                "h-10 w-10 rounded-lg flex items-center justify-center",
                workerStatus?.running ? "bg-emerald-500/10" : "bg-red-500/10"
              )}>
                <Activity className={cn(
                  "h-5 w-5",
                  workerStatus?.running ? "text-emerald-500" : "text-red-500"
                )} />
              </div>
              <div>
                <p className="text-sm font-medium">Background Worker</p>
                <p className={cn(
                  "text-xs",
                  workerStatus?.running ? "text-emerald-500" : "text-red-500"
                )}>
                  {workerStatus?.running ? 'Running' : 'Stopped'}
                </p>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              {workerStatus?.jobs?.length || 0} scheduled jobs
            </div>
          </CardContent>
        </Card>

        {/* AI Status */}
        <Card
          className="cursor-pointer hover:bg-muted/50 transition-colors"
          onClick={() => navigate('/ai')}
        >
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-3">
              <div className={cn(
                "h-10 w-10 rounded-lg flex items-center justify-center",
                aiStatus?.available ? "bg-emerald-500/10" : "bg-yellow-500/10"
              )}>
                <Cpu className={cn(
                  "h-5 w-5",
                  aiStatus?.available ? "text-emerald-500" : "text-yellow-500"
                )} />
              </div>
              <div>
                <p className="text-sm font-medium">AI Service</p>
                <p className={cn(
                  "text-xs",
                  aiStatus?.available ? "text-emerald-500" : "text-yellow-500"
                )}>
                  {aiStatus?.available
                    ? (aiStatus.provider === 'claude' ? 'Claude API' : 'Ollama')
                    : 'Not Connected'}
                </p>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              Click to open AI Assistant
            </div>
          </CardContent>
        </Card>

        {/* Embeddings Status */}
        <Card
          className="cursor-pointer hover:bg-muted/50 transition-colors"
          onClick={() => navigate('/search')}
        >
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-3">
              <div className={cn(
                "h-10 w-10 rounded-lg flex items-center justify-center",
                embeddingStats?.available ? "bg-emerald-500/10" : "bg-yellow-500/10"
              )}>
                <Sparkles className={cn(
                  "h-5 w-5",
                  embeddingStats?.available ? "text-emerald-500" : "text-yellow-500"
                )} />
              </div>
              <div>
                <p className="text-sm font-medium">Vector Search</p>
                <p className={cn(
                  "text-xs",
                  embeddingStats?.available ? "text-emerald-500" : "text-yellow-500"
                )}>
                  {embeddingStats?.available ? 'Ready' : 'Unavailable'}
                </p>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              {stats?.embeddings || 0} indexed chunks
            </div>
          </CardContent>
        </Card>

        {/* Database Status */}
        <Card>
          <CardContent className="pt-4 pb-3">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <Database className="h-5 w-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-sm font-medium">Database</p>
                <p className="text-xs text-emerald-500">Connected</p>
              </div>
            </div>
            <div className="mt-3 text-xs text-muted-foreground">
              SQLite + ChromaDB
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Processing Stats */}
      <section className="grid gap-4 md:grid-cols-2">
        {/* Files Stats */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4" />
              File Processing
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats ? (
              <div className="space-y-3">
                <div className="grid grid-cols-4 gap-2">
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <p className="text-xl font-bold text-emerald-500">{stats.files.completed || 0}</p>
                    <p className="text-xs text-muted-foreground">Completed</p>
                  </div>
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <p className="text-xl font-bold text-blue-500">{stats.files.processing || 0}</p>
                    <p className="text-xs text-muted-foreground">Processing</p>
                  </div>
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <p className="text-xl font-bold text-yellow-500">{stats.files.pending || 0}</p>
                    <p className="text-xs text-muted-foreground">Pending</p>
                  </div>
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <p className="text-xl font-bold text-red-500">{stats.files.failed || 0}</p>
                    <p className="text-xs text-muted-foreground">Failed</p>
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => navigate('/documents')}
                >
                  View All Documents
                </Button>
              </div>
            ) : (
              <div className="h-24 skeleton rounded" />
            )}
          </CardContent>
        </Card>

        {/* Jobs Stats */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Cog className="h-4 w-4" />
              Job Queue
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats ? (
              <div className="space-y-3">
                <div className="grid grid-cols-4 gap-2">
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <p className="text-xl font-bold text-emerald-500">{stats.jobs.completed || 0}</p>
                    <p className="text-xs text-muted-foreground">Done</p>
                  </div>
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <p className="text-xl font-bold text-blue-500">{stats.jobs.running || 0}</p>
                    <p className="text-xs text-muted-foreground">Running</p>
                  </div>
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <p className="text-xl font-bold text-yellow-500">{stats.jobs.queued || 0}</p>
                    <p className="text-xs text-muted-foreground">Queued</p>
                  </div>
                  <div className="text-center p-2 bg-muted/50 rounded">
                    <p className="text-xl font-bold text-red-500">{stats.jobs.failed || 0}</p>
                    <p className="text-xs text-muted-foreground">Failed</p>
                  </div>
                </div>
                <div className="text-xs text-muted-foreground text-center">
                  {(stats.jobs.running || 0) + (stats.jobs.queued || 0) > 0
                    ? `${(stats.jobs.running || 0) + (stats.jobs.queued || 0)} jobs in progress`
                    : 'Queue is empty'}
                </div>
              </div>
            ) : (
              <div className="h-24 skeleton rounded" />
            )}
          </CardContent>
        </Card>
      </section>

      {/* Active Jobs */}
      {(runningJobs.length > 0 || queuedJobs.length > 0) && (
        <section>
          <h2 className="text-lg font-semibold font-head mb-3 flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            Active Jobs
          </h2>
          <div className="space-y-2">
            {runningJobs.map((job) => (
              <Card key={job.id} className="border-blue-500/30">
                <CardContent className="py-3 flex items-center gap-3">
                  <Cog className="h-4 w-4 text-blue-500 animate-spin" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{job.job_type}</p>
                    <p className="text-xs text-muted-foreground">Started {new Date(job.created_at).toLocaleTimeString()}</p>
                  </div>
                  <Badge variant="secondary" className="bg-blue-500/10 text-blue-500">
                    Running
                  </Badge>
                </CardContent>
              </Card>
            ))}
            {queuedJobs.map((job) => (
              <Card key={job.id} className="border-yellow-500/30">
                <CardContent className="py-3 flex items-center gap-3">
                  <Clock className="h-4 w-4 text-yellow-500" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{job.job_type}</p>
                    <p className="text-xs text-muted-foreground">Queued {new Date(job.created_at).toLocaleTimeString()}</p>
                  </div>
                  <Badge variant="secondary" className="bg-yellow-500/10 text-yellow-500">
                    Queued
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* AI Insights Section */}
      {anomaliesData && anomaliesData.anomalies.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold font-head mb-3 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-primary" />
            AI Insights
          </h2>
          <div className="space-y-3">
            {anomaliesData.anomalies.map((anomaly, idx) => (
              <Card
                key={idx}
                className={cn(
                  "cursor-pointer hover:bg-muted/50 transition-colors",
                  anomaly.risk_score > 70 && "border-red-500/50",
                  anomaly.risk_score > 40 && anomaly.risk_score <= 70 && "border-yellow-500/50"
                )}
                onClick={() => navigate('/documents')}
              >
                <CardContent className="py-3">
                  <div className="flex items-start gap-3">
                    <div className={cn(
                      "h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0",
                      anomaly.risk_score > 70 ? "bg-red-500/10" :
                      anomaly.risk_score > 40 ? "bg-yellow-500/10" : "bg-blue-500/10"
                    )}>
                      <AlertTriangle className={cn(
                        "h-4 w-4",
                        anomaly.risk_score > 70 ? "text-red-500" :
                        anomaly.risk_score > 40 ? "text-yellow-500" : "text-blue-500"
                      )} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <p className="text-sm font-medium truncate">
                          {anomaly.summary || 'Document Analysis'}
                        </p>
                        <Badge
                          variant="secondary"
                          className={cn(
                            anomaly.risk_score > 70 ? "bg-red-500/10 text-red-500" :
                            anomaly.risk_score > 40 ? "bg-yellow-500/10 text-yellow-500" :
                            "bg-blue-500/10 text-blue-500"
                          )}
                        >
                          Risk: {anomaly.risk_score}
                        </Badge>
                      </div>
                      {anomaly.anomalies.length > 0 && (
                        <ul className="text-xs text-muted-foreground space-y-0.5">
                          {anomaly.anomalies.slice(0, 3).map((a, i) => (
                            <li key={i} className="truncate">• {a}</li>
                          ))}
                          {anomaly.anomalies.length > 3 && (
                            <li className="text-primary">+{anomaly.anomalies.length - 3} more</li>
                          )}
                        </ul>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Scheduled Jobs List */}
      {workerStatus?.jobs && workerStatus.jobs.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold font-head mb-3">Scheduled Tasks</h2>
          <Card>
            <CardContent className="py-3">
              <div className="space-y-2">
                {workerStatus.jobs.map((job, idx) => (
                  <div key={idx} className="flex items-center justify-between text-sm py-2 border-b last:border-0">
                    <span className="text-muted-foreground">{job.name}</span>
                    {job.next_run && (
                      <span className="text-xs text-muted-foreground">
                        Next: {new Date(job.next_run).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      )}
    </div>
  )
}
