import { useMemo } from 'react'
import { cn } from '@/lib/utils'

interface DataPoint {
  label: string
  value: number
}

interface TrendChartProps {
  data: DataPoint[]
  height?: number
  className?: string
  color?: 'blue' | 'green' | 'amber' | 'red'
  showLabels?: boolean
  formatValue?: (value: number) => string
}

const COLORS = {
  blue: {
    line: 'stroke-blue-500',
    fill: 'fill-blue-500/10',
    dot: 'fill-blue-500',
    gradient: ['#3b82f6', '#3b82f620']
  },
  green: {
    line: 'stroke-emerald-500',
    fill: 'fill-emerald-500/10',
    dot: 'fill-emerald-500',
    gradient: ['#10b981', '#10b98120']
  },
  amber: {
    line: 'stroke-amber-500',
    fill: 'fill-amber-500/10',
    dot: 'fill-amber-500',
    gradient: ['#f59e0b', '#f59e0b20']
  },
  red: {
    line: 'stroke-red-500',
    fill: 'fill-red-500/10',
    dot: 'fill-red-500',
    gradient: ['#ef4444', '#ef444420']
  }
}

export function TrendChart({
  data,
  height = 120,
  className,
  color = 'blue',
  showLabels = true,
  formatValue: _formatValue = (v) => v.toLocaleString()
}: TrendChartProps) {
  // formatValue available for future tooltip implementation
  void _formatValue
  const chartData = useMemo(() => {
    if (data.length === 0) return null

    const values = data.map(d => d.value)
    const min = Math.min(...values)
    const max = Math.max(...values)
    const range = max - min || 1

    // Padding
    const paddingX = 10
    const paddingY = 20
    const chartWidth = 100 - paddingX * 2
    const chartHeight = height - paddingY * 2

    // Calculate points
    const points = data.map((d, i) => {
      const x = paddingX + (i / (data.length - 1 || 1)) * chartWidth
      const y = paddingY + chartHeight - ((d.value - min) / range) * chartHeight
      return { x, y, ...d }
    })

    // Create SVG path for line
    const linePath = points
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
      .join(' ')

    // Create SVG path for area fill
    const areaPath = `${linePath} L ${points[points.length - 1].x} ${paddingY + chartHeight} L ${points[0].x} ${paddingY + chartHeight} Z`

    return {
      points,
      linePath,
      areaPath,
      min,
      max,
      latest: data[data.length - 1],
      previous: data.length > 1 ? data[data.length - 2] : null
    }
  }, [data, height])

  if (!chartData || data.length < 2) {
    return (
      <div className={cn("flex items-center justify-center text-muted-foreground text-sm", className)} style={{ height }}>
        Not enough data
      </div>
    )
  }

  const colorScheme = COLORS[color]
  const change = chartData.previous
    ? chartData.latest.value - chartData.previous.value
    : 0
  const changePercent = chartData.previous && chartData.previous.value > 0
    ? ((change / chartData.previous.value) * 100).toFixed(1)
    : '0'

  return (
    <div className={cn("relative", className)}>
      <svg
        viewBox={`0 0 100 ${height}`}
        className="w-full"
        style={{ height }}
        preserveAspectRatio="none"
      >
        {/* Gradient definition */}
        <defs>
          <linearGradient id={`gradient-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colorScheme.gradient[0]} stopOpacity="0.3" />
            <stop offset="100%" stopColor={colorScheme.gradient[1]} stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Area fill */}
        <path
          d={chartData.areaPath}
          fill={`url(#gradient-${color})`}
        />

        {/* Line */}
        <path
          d={chartData.linePath}
          fill="none"
          className={colorScheme.line}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />

        {/* Dots for first and last points */}
        <circle
          cx={chartData.points[0].x}
          cy={chartData.points[0].y}
          r="3"
          className={colorScheme.dot}
          vectorEffect="non-scaling-stroke"
        />
        <circle
          cx={chartData.points[chartData.points.length - 1].x}
          cy={chartData.points[chartData.points.length - 1].y}
          r="4"
          className={colorScheme.dot}
          vectorEffect="non-scaling-stroke"
        />
      </svg>

      {/* Labels */}
      {showLabels && (
        <div className="flex justify-between text-xs text-muted-foreground mt-1">
          <span>{data[0].label}</span>
          <span className={cn(
            "font-medium",
            change > 0 ? "text-emerald-500" : change < 0 ? "text-red-500" : "text-muted-foreground"
          )}>
            {change >= 0 ? '+' : ''}{changePercent}%
          </span>
          <span>{data[data.length - 1].label}</span>
        </div>
      )}
    </div>
  )
}

// Compact sparkline version
interface SparklineProps {
  values: number[]
  color?: 'blue' | 'green' | 'amber' | 'red'
  width?: number
  height?: number
}

export function Sparkline({ values, color = 'blue', width = 60, height = 20 }: SparklineProps) {
  const path = useMemo(() => {
    if (values.length < 2) return ''

    const min = Math.min(...values)
    const max = Math.max(...values)
    const range = max - min || 1

    const points = values.map((v, i) => {
      const x = (i / (values.length - 1)) * width
      const y = height - ((v - min) / range) * height
      return `${i === 0 ? 'M' : 'L'} ${x} ${y}`
    })

    return points.join(' ')
  }, [values, width, height])

  if (values.length < 2) {
    return <div style={{ width, height }} />
  }

  const colorScheme = COLORS[color]

  return (
    <svg width={width} height={height} className="inline-block">
      <path
        d={path}
        fill="none"
        className={colorScheme.line}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
