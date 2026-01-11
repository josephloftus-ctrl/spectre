import * as React from "react"
import { cn } from "@/lib/utils"
import { ArrowRightLeft, AlertCircle } from "lucide-react"
import { MatchFlagType } from "@/lib/api"

interface MatchBadgeProps {
  type: MatchFlagType
  className?: string
  showLabel?: boolean
}

const matchFlagConfig: Record<MatchFlagType, {
  label: string
  shortLabel: string
  color: string
  bgColor: string
  borderColor: string
  Icon: React.ComponentType<{ className?: string }>
}> = {
  sku_mismatch: {
    label: "SKU Mismatch",
    shortLabel: "Mismatch",
    color: "text-amber-600",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
    Icon: ArrowRightLeft,
  },
  orphan: {
    label: "Orphan",
    shortLabel: "Orphan",
    color: "text-red-600",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/30",
    Icon: AlertCircle,
  },
}

export function MatchBadge({ type, className, showLabel = true }: MatchBadgeProps) {
  const config = matchFlagConfig[type]
  if (!config) return null

  const { Icon, shortLabel, color, bgColor, borderColor } = config

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium",
        bgColor,
        borderColor,
        color,
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {showLabel && <span>{shortLabel}</span>}
    </span>
  )
}

export function MatchBadgeList({ flags, className }: { flags: MatchFlagType[], className?: string }) {
  if (!flags || flags.length === 0) return null

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {flags.map((flag, i) => (
        <MatchBadge key={`${flag}-${i}`} type={flag} />
      ))}
    </div>
  )
}

export function getMatchFlagLabel(type: MatchFlagType): string {
  return matchFlagConfig[type]?.label || type
}

export function getMatchFlagDescription(type: MatchFlagType): string {
  switch (type) {
    case "sku_mismatch":
      return "SKU not found, but price and vendor match suggests a correction"
    case "orphan":
      return "No matching purchase record found - needs investigation"
    default:
      return ""
  }
}
