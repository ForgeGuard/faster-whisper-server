import { forwardRef, type InputHTMLAttributes } from 'react'
import { cn } from './cn'

/**
 * Range slider with a themed track fill driven by the current value.
 * Pass value/min/max as numbers so the fill percentage can be computed.
 */
export interface SliderProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  value: number
  min?: number
  max?: number
}

export const Slider = forwardRef<HTMLInputElement, SliderProps>(
  ({ className, value, min = 0, max = 100, style, ...props }, ref) => {
    const pct = Math.min(
      100,
      Math.max(0, ((value - min) / (max - min || 1)) * 100),
    )
    return (
      <input
        ref={ref}
        type="range"
        min={min}
        max={max}
        value={value}
        className={cn('ui-slider w-full', className)}
        style={
          {
            '--pct': `${pct}%`,
            ...style,
          } as React.CSSProperties
        }
        {...props}
      />
    )
  },
)
Slider.displayName = 'Slider'
