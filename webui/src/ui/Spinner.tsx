import { cn } from './cn'

type SpinnerProps = {
  className?: string
  label?: string
}

export function Spinner({ className, label = 'Loading' }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label}
      className={cn(
        'inline-block h-4 w-4 shrink-0 animate-[spin-slow_0.7s_linear_infinite] rounded-full border-2 border-current border-t-transparent',
        className,
      )}
    />
  )
}
