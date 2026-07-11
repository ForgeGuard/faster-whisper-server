import { forwardRef, type SelectHTMLAttributes } from 'react'
import { cn } from './cn'
import { ChevronDownIcon } from './icons'

export interface SelectOption {
  value: string
  label: string
}

export interface SelectProps
  extends SelectHTMLAttributes<HTMLSelectElement> {
  options?: SelectOption[]
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, options, children, ...props }, ref) => {
    return (
      <div className="relative">
        <select
          ref={ref}
          className={cn(
            'h-10 w-full appearance-none rounded-lg border border-border bg-surface pl-3 pr-9 text-sm text-fg',
            'shadow-sm transition-colors duration-150 hover:border-border-strong',
            'focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/40',
            'disabled:opacity-60',
            className,
          )}
          {...props}
        >
          {options
            ? options.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))
            : children}
        </select>
        <ChevronDownIcon className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[1.1rem] text-faint" />
      </div>
    )
  },
)
Select.displayName = 'Select'
