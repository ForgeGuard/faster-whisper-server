import { forwardRef, type InputHTMLAttributes } from 'react'
import { cn } from './cn'

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => {
  return (
    <input
      ref={ref}
      className={cn(
        'h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-fg',
        'placeholder:text-faint shadow-sm transition-colors duration-150',
        'hover:border-border-strong focus:border-accent focus:outline-none',
        'focus:ring-2 focus:ring-accent/40 disabled:opacity-60',
        className,
      )}
      {...props}
    />
  )
})
Input.displayName = 'Input'
