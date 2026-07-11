import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { createPortal } from 'react-dom'
import { cn } from './cn'
import { AlertIcon, CheckIcon, CloseIcon, InfoIcon } from './icons'
import { IconButton } from './IconButton'

export type ToastVariant = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  variant: ToastVariant
  title: string
  message?: string
}

interface ToastContextValue {
  toast: (t: Omit<ToastItem, 'id'>) => void
  success: (title: string, message?: string) => void
  error: (title: string, message?: string) => void
  info: (title: string, message?: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const variantStyles: Record<
  ToastVariant,
  { icon: ReactNode; accent: string }
> = {
  success: {
    icon: <CheckIcon />,
    accent: 'text-success',
  },
  error: {
    icon: <AlertIcon />,
    accent: 'text-danger',
  },
  info: {
    icon: <InfoIcon />,
    accent: 'text-accent',
  },
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const idRef = useRef(0)

  const dismiss = useCallback((id: number) => {
    setItems((cur) => cur.filter((t) => t.id !== id))
  }, [])

  const toast = useCallback(
    (t: Omit<ToastItem, 'id'>) => {
      const id = ++idRef.current
      setItems((cur) => [...cur, { ...t, id }])
      window.setTimeout(() => dismiss(id), 5000)
    },
    [dismiss],
  )

  const value = useMemo<ToastContextValue>(
    () => ({
      toast,
      success: (title, message) => toast({ variant: 'success', title, message }),
      error: (title, message) => toast({ variant: 'error', title, message }),
      info: (title, message) => toast({ variant: 'info', title, message }),
    }),
    [toast],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      {createPortal(
        <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-full max-w-sm flex-col gap-2">
          {items.map((t) => {
            const v = variantStyles[t.variant]
            return (
              <div
                key={t.id}
                role="status"
                className="pointer-events-auto flex animate-slide-in items-start gap-3 rounded-xl border border-border bg-elevated p-3.5 shadow-elevated"
              >
                <span className={cn('mt-0.5 text-[1.2rem]', v.accent)}>
                  {v.icon}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-fg">{t.title}</p>
                  {t.message && (
                    <p className="mt-0.5 break-words text-xs text-muted">
                      {t.message}
                    </p>
                  )}
                </div>
                <IconButton
                  variant="ghost"
                  size="sm"
                  aria-label="Dismiss notification"
                  onClick={() => dismiss(t.id)}
                >
                  <CloseIcon />
                </IconButton>
              </div>
            )
          })}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within a ToastProvider')
  return ctx
}
