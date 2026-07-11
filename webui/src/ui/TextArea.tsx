import { forwardRef, type TextareaHTMLAttributes } from 'react'
import { cn } from './cn'

export const TextArea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => {
  return (
    <textarea
      ref={ref}
      className={cn(
        'w-full resize-y rounded-xl border border-border bg-surface px-4 py-3 text-sm text-fg',
        'placeholder:text-faint shadow-sm transition-colors duration-150',
        'hover:border-border-strong focus:border-accent focus:outline-none',
        'focus:ring-2 focus:ring-accent/40 disabled:opacity-60',
        className,
      )}
      {...props}
    />
  )
})
TextArea.displayName = 'TextArea'
