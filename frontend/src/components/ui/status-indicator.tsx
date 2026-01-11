import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { CheckCircle2, AlertTriangle, AlertCircle, Circle } from "lucide-react"

const statusIndicatorVariants = cva(
  "inline-flex items-center justify-center rounded-full transition-colors",
  {
    variants: {
      status: {
        critical: "text-red-500",
        warning: "text-amber-500",
        healthy: "text-green-500",
        clean: "text-emerald-500",
      },
      size: {
        sm: "h-4 w-4",
        md: "h-5 w-5",
        lg: "h-6 w-6",
      },
    },
    defaultVariants: {
      status: "clean",
      size: "md",
    },
  }
)

const statusDotVariants = cva(
  "rounded-full animate-pulse",
  {
    variants: {
      status: {
        critical: "bg-red-500",
        warning: "bg-amber-500",
        healthy: "bg-green-500",
        clean: "bg-emerald-500",
      },
      size: {
        sm: "h-2 w-2",
        md: "h-2.5 w-2.5",
        lg: "h-3 w-3",
      },
    },
    defaultVariants: {
      status: "clean",
      size: "md",
    },
  }
)

export type StatusType = "critical" | "warning" | "healthy" | "clean"
export type TrendType = "up" | "down" | "stable" | null

export interface StatusIndicatorProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof statusIndicatorVariants> {
  status: StatusType
  showIcon?: boolean
  showDot?: boolean
}

function StatusIndicator({
  className,
  status,
  size,
  showIcon = false,
  showDot = true,
  ...props
}: StatusIndicatorProps) {
  const Icon = getStatusIcon(status)

  if (showIcon) {
    return (
      <div
        className={cn(statusIndicatorVariants({ status, size }), className)}
        {...props}
      >
        <Icon className="h-full w-full" />
      </div>
    )
  }

  if (showDot) {
    return (
      <div
        className={cn(
          "inline-flex items-center justify-center",
          size === "sm" ? "h-4 w-4" : size === "lg" ? "h-6 w-6" : "h-5 w-5",
          className
        )}
        {...props}
      >
        <span className={cn(statusDotVariants({ status, size }))} />
      </div>
    )
  }

  return null
}

function getStatusIcon(status: StatusType) {
  switch (status) {
    case "critical":
      return AlertCircle
    case "warning":
      return AlertTriangle
    case "healthy":
      return Circle
    case "clean":
      return CheckCircle2
  }
}

function getStatusLabel(status: StatusType): string {
  switch (status) {
    case "critical":
      return "Critical"
    case "warning":
      return "Warning"
    case "healthy":
      return "Healthy"
    case "clean":
      return "Clean"
  }
}

function getStatusColor(status: StatusType): string {
  switch (status) {
    case "critical":
      return "text-red-500"
    case "warning":
      return "text-amber-500"
    case "healthy":
      return "text-green-500"
    case "clean":
      return "text-emerald-500"
  }
}

function getTrendIcon(trend: TrendType): string {
  switch (trend) {
    case "up":
      return "↑" // Got worse
    case "down":
      return "↓" // Improved
    case "stable":
      return "→" // No change
    default:
      return ""
  }
}

function getTrendLabel(trend: TrendType): string {
  switch (trend) {
    case "up":
      return "Worsened"
    case "down":
      return "Improved"
    case "stable":
      return "Stable"
    default:
      return ""
  }
}

function getTrendColor(trend: TrendType): string {
  switch (trend) {
    case "up":
      return "text-red-500" // Worse = bad
    case "down":
      return "text-emerald-500" // Better = good
    case "stable":
      return "text-muted-foreground"
    default:
      return ""
  }
}

export {
  StatusIndicator,
  statusIndicatorVariants,
  getStatusIcon,
  getStatusLabel,
  getStatusColor,
  getTrendIcon,
  getTrendLabel,
  getTrendColor,
}
