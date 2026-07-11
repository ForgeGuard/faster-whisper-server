import { forwardRef, type ButtonHTMLAttributes } from 'react'
import { cn } from './cn'

export interface IconButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'ghost' | 'accent'
  size?: 'sm' | 'md' | 'lg'
}

const sizes = {
  sm: 'h-8 w-8 text-[1rem]',
  md: 'h-10 w-10 text-[1.15rem]',
  lg: 'h-12 w-12 text-[1.3rem]',
}

const variants = {
  default:
    'text-muted bg-surface border border-border hover:bg-surface-2 hover:text-fg hover:border-border-strong',
  ghost: 'text-muted bg-transparent hover:bg-surface-2 hover:text-fg',
  accent: 'text-accent-fg bg-accent hover:bg-accent-hover',
}

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, variant = 'default', size = 'md', children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        type="button"
        className={cn(
          'inline-flex items-center justify-center rounded-lg transition-colors duration-150 ' +
            'active:scale-95 disabled:pointer-events-none disabled:opacity-50 ' +
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 ' +
            'focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          sizes[size],
          variants[variant],
          className,
        )}
        {...props}
      >
        {children}
      </button>
    )
  },
)
IconButton.displayName = 'IconButton'
