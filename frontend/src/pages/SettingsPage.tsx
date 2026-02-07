import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import {
  Mail, Database, Bell, HardDrive, Cpu, RefreshCw, Check, X,
  Sparkles, Server, FileSpreadsheet, Cog, AlertTriangle
} from 'lucide-react'
import { checkAIStatus } from '@/lib/ai'
import { fetchStats, fetchWorkerStatus, fetchJobs, fetchAnomalies, retryFailedJobs } from '@/lib/api'
import { cn } from '@/lib/utils'

export function SettingsPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  // Debug menu state
  const [debugTapCount, setDebugTapCount] = useState(0)
  const [showDebug, setShowDebug] = useState(searchParams.get('debug') === '1')
  const [retrying, setRetrying] = useState(false)

  // System status queries
  const { data: aiStatus, refetch: refetchAI } = useQuery({
    queryKey: ['ai-status'],
    queryFn: checkAIStatus,
    refetchInterval: 30000
  })

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['system-stats'],
    queryFn: fetchStats,
    refetchInterval: 10000
  })

  const { data: workerStatus } = useQuery({
    queryKey: ['worker-status'],
    queryFn: fetchWorkerStatus,
    refetchInterval: 10000
  })

  // Debug-only queries
  const { data: jobsData } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => fetchJobs({ limit: 20 }),
    refetchInterval: 5000,
    enabled: showDebug
  })

  const { data: anomaliesData } = useQuery({
    queryKey: ['anomalies'],
    queryFn: () => fetchAnomalies(10),
    refetchInterval: 30000,
    enabled: showDebug
  })

  // Handle version tap to reveal debug menu
  const handleVersionTap = () => {
    const newCount = debugTapCount + 1
    setDebugTapCount(newCount)
    if (newCount >= 5) {
      setShowDebug(true)
      setDebugTapCount(0)
    }
    setTimeout(() => setDebugTapCount(0), 2000)
  }

  const handleRetryFailed = async () => {
    setRetrying(true)
    try {
      await retryFailedJobs()
      refetchStats()
    } finally {
      setRetrying(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-head">Settings</h1>
        <p className="text-muted-foreground">Configure your preferences</p>
      </div>

      {/* AI Configuration */}
      <Card className={aiStatus?.available ? 'border-primary/30' : ''}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-primary" />
            AI Assistant
          </CardTitle>
          <CardDescription>
            Powered by Claude via backend proxy
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Connection Status */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {aiStatus === undefined ? (
                <span className="text-sm text-muted-foreground">Checking...</span>
              ) : aiStatus?.available ? (
                <>
                  <Check className="h-4 w-4 text-emerald-500" />
                  <span className="text-sm text-emerald-500">Connected</span>
                </>
              ) : (
                <>
                  <X className="h-4 w-4 text-destructive" />
                  <span className="text-sm text-destructive">Not Configured</span>
                </>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetchAI()}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>

          {/* Model Info */}
          {aiStatus?.available && (
            <div className="p-3 rounded-lg bg-muted/50 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Chat Model</span>
                <code className="bg-background px-2 py-0.5 rounded">{aiStatus.model}</code>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Analysis Model</span>
                <code className="bg-background px-2 py-0.5 rounded">{aiStatus.analysis_model}</code>
              </div>
            </div>
          )}

          {/* Setup instructions if not connected */}
          {!aiStatus?.available && (
            <div className="p-4 rounded-lg bg-muted/50 text-sm space-y-2">
              <p className="font-medium">To configure Claude:</p>
              <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                <li>Set <span className="font-mono">CLAUDE_API_KEY</span> in your backend environment</li>
                <li>Restart the backend server</li>
                <li>Click Refresh above</li>
              </ol>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Microsoft Account */}
      <Card className="opacity-75">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Microsoft Account
            <Badge variant="secondary" className="ml-2">Coming Soon</Badge>
          </CardTitle>
          <CardDescription>
            Connect your Microsoft 365 account to automatically sync emails and documents
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground">
              OAuth integration not yet configured
            </div>
            <Button disabled>Connect Account</Button>
          </div>
        </CardContent>
      </Card>

      {/* Local Storage */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HardDrive className="h-5 w-5" />
            Local Storage
          </CardTitle>
          <CardDescription>
            Manage offline data stored in your browser
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Documents</div>
              <div className="text-sm text-muted-foreground">0 files cached</div>
            </div>
            <Button variant="outline" size="sm">Clear</Button>
          </div>
          <Separator />
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Notes</div>
              <div className="text-sm text-muted-foreground">0 notes stored</div>
            </div>
            <Button variant="outline" size="sm">Export</Button>
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Notifications
          </CardTitle>
          <CardDescription>
            Configure when and how you receive alerts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            Notification settings coming soon
          </div>
        </CardContent>
      </Card>

      {/* System Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            System Status
          </CardTitle>
          <CardDescription>
            Backend services and processing status
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Service Status Indicators */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-2">
              <div className={cn(
                "h-2 w-2 rounded-full",
                workerStatus?.running ? "bg-emerald-500" : "bg-red-500"
              )} />
              <span className="text-sm">Worker: {workerStatus?.running ? 'Running' : 'Stopped'}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className={cn(
                "h-2 w-2 rounded-full",
                aiStatus?.available ? "bg-emerald-500" : "bg-yellow-500"
              )} />
              <span className="text-sm">AI: {aiStatus?.available ? 'Claude' : 'Offline'}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="text-sm">Database: Connected</span>
            </div>
          </div>

          <Separator />

          {/* File Processing Summary */}
          {stats && (
            <div className="space-y-2">
              <p className="text-sm font-medium">File Processing</p>
              <div className="flex gap-4 text-sm">
                <span className="text-emerald-500">{stats.files.completed || 0} completed</span>
                <span className="text-yellow-500">{stats.files.pending || 0} pending</span>
                <span className="text-red-500">{stats.files.failed || 0} failed</span>
              </div>
              {(stats.files.failed || 0) > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRetryFailed}
                  disabled={retrying}
                >
                  <RefreshCw className={cn("h-4 w-4 mr-2", retrying && "animate-spin")} />
                  Retry Failed Files
                </Button>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Debug Menu (Hidden until tapped 5x on version) */}
      {showDebug && (
        <Card className="border-amber-500/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cog className="h-5 w-5 text-amber-500" />
              Debug Menu
              <Badge variant="secondary" className="ml-auto">Developer</Badge>
            </CardTitle>
            <CardDescription>
              Advanced system controls and diagnostics
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Job Queue */}
            {stats && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Job Queue</p>
                <div className="grid grid-cols-4 gap-2 text-center text-xs">
                  <div className="p-2 bg-muted rounded">
                    <p className="text-lg font-bold text-emerald-500">{stats.jobs.completed || 0}</p>
                    <p className="text-muted-foreground">Done</p>
                  </div>
                  <div className="p-2 bg-muted rounded">
                    <p className="text-lg font-bold text-blue-500">{stats.jobs.running || 0}</p>
                    <p className="text-muted-foreground">Running</p>
                  </div>
                  <div className="p-2 bg-muted rounded">
                    <p className="text-lg font-bold text-yellow-500">{stats.jobs.queued || 0}</p>
                    <p className="text-muted-foreground">Queued</p>
                  </div>
                  <div className="p-2 bg-muted rounded">
                    <p className="text-lg font-bold text-red-500">{stats.jobs.failed || 0}</p>
                    <p className="text-muted-foreground">Failed</p>
                  </div>
                </div>
              </div>
            )}

            {/* Recent Jobs List */}
            {jobsData?.jobs && jobsData.jobs.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Recent Jobs</p>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {jobsData.jobs.slice(0, 10).map((job) => (
                    <div key={job.id} className="flex items-center gap-2 text-xs p-2 bg-muted/50 rounded">
                      <div className={cn(
                        "h-2 w-2 rounded-full",
                        job.status === 'completed' && "bg-emerald-500",
                        job.status === 'running' && "bg-blue-500",
                        job.status === 'queued' && "bg-yellow-500",
                        job.status === 'failed' && "bg-red-500"
                      )} />
                      <span className="flex-1 truncate">{job.job_type}</span>
                      <span className="text-muted-foreground">{job.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Anomalies */}
            {anomaliesData && anomaliesData.anomalies.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Recent Anomalies ({anomaliesData.count})</p>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {anomaliesData.anomalies.slice(0, 5).map((anomaly, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs p-2 bg-muted/50 rounded">
                      <AlertTriangle className={cn(
                        "h-3 w-3 flex-shrink-0",
                        anomaly.risk_score > 70 ? "text-red-500" :
                        anomaly.risk_score > 40 ? "text-yellow-500" : "text-blue-500"
                      )} />
                      <span className="flex-1 truncate">{anomaly.summary || 'Analysis'}</span>
                      <Badge variant="secondary" className="text-[10px]">Risk: {anomaly.risk_score}</Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Separator />

            {/* Quick Actions */}
            <div className="flex gap-2 flex-wrap">
              <Button variant="outline" size="sm" onClick={() => navigate('/documents')}>
                <FileSpreadsheet className="h-4 w-4 mr-1" />
                Documents
              </Button>
              <Button variant="outline" size="sm" onClick={() => navigate('/search')}>
                <Sparkles className="h-4 w-4 mr-1" />
                Search
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="text-red-500 hover:text-red-600"
                onClick={() => setShowDebug(false)}
              >
                <X className="h-4 w-4 mr-1" />
                Hide Debug
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Backend Connection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Backend Connection
          </CardTitle>
          <CardDescription>
            API endpoint configuration
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-mono text-sm">/api</div>
              <div className="text-sm text-muted-foreground">Proxied to localhost:8000</div>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-sm text-emerald-500">Connected</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Version Footer - tap 5x to reveal debug menu */}
      <div
        className="text-center py-4 cursor-default select-none"
        onClick={handleVersionTap}
      >
        <p className="text-xs text-muted-foreground">
          Spectre v1.0.0 {debugTapCount > 0 && debugTapCount < 5 && `(${5 - debugTapCount} more...)`}
        </p>
      </div>
    </div>
  )
}
