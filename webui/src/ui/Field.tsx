import { useId, type ReactNode } from 'react'
import { cn } from './cn'

/**
 * Wraps a control with an associated <label>, optional hint, and passes a
 * generated id down via a render prop so labels stay correctly linked.
 */
export function Field({
  label,
  hint,
  htmlFor,
  className,
  children,
}: {
  label: ReactNode
  hint?: ReactNode
  htmlFor?: string
  className?: string
  children: ReactNode | ((id: string) => ReactNode)
}) {
  const generatedId = useId()
  const id = htmlFor ?? generatedId
  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label
        htmlFor={id}
        className="text-xs font-medium text-muted flex items-center justify-between gap-2"
      >
        <span>{label}</span>
        {hint && <span className="font-normal text-faint">{hint}</span>}
      </label>
      {typeof children === 'function' ? children(id) : children}
    </div>
  )
}
