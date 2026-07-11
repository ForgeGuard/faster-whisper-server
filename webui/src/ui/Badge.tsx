import type { HTMLAttributes } from 'react'
import { cn } from './cn'

export type BadgeVariant = 'default' | 'accent' | 'success' | 'muted'

const variants: Record<BadgeVariant, string> = {
  default: 'bg-surface-2 text-muted border-border',
  accent: 'bg-accent-soft text-accent border-transparent',
  success: 'bg-success/10 text-success border-transparent',
  muted: 'bg-transparent text-faint border-border',
}

export function Badge({
  className,
  variant = 'default',
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs font-medium',
        variants[variant],
        className,
      )}
      {...props}
    />
  )
}
