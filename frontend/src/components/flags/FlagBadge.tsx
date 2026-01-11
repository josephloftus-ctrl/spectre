import * as React from "react"
import { cn } from "@/lib/utils"
import { Package, DollarSign } from "lucide-react"

export type FlagType = "uom_error" | "big_dollar"

interface FlagBadgeProps {
  type: FlagType
  className?: string
  showLabel?: boolean
}

const flagConfig: Record<FlagType, {
  label: string
  shortLabel: string
  color: string
  bgColor: string
  borderColor: string
  Icon: React.ComponentType<{ className?: string }>
}> = {
  uom_error: {
    label: "UOM Error",
    shortLabel: "UOM",
    color: "text-red-600",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/30",
    Icon: Package,
  },
  big_dollar: {
    label: "Big Dollar",
    shortLabel: "$$$",
    color: "text-amber-600",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
    Icon: DollarSign,
  },
}

export function FlagBadge({ type, className, showLabel = true }: FlagBadgeProps) {
  const config = flagConfig[type]
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

export function FlagBadgeList({ flags, className }: { flags: FlagType[], className?: string }) {
  if (!flags || flags.length === 0) return null

  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      {flags.map((flag, i) => (
        <FlagBadge key={`${flag}-${i}`} type={flag} />
      ))}
    </div>
  )
}

export function getFlagLabel(type: FlagType): string {
  return flagConfig[type]?.label || type
}

export function getFlagDescription(type: FlagType): string {
  switch (type) {
    case "uom_error":
      return "High case count (10+) suggests units entered as cases"
    case "big_dollar":
      return "Line total exceeds $250"
    default:
      return ""
  }
}
