import type { ReactNode } from 'react'
import { GearIcon, IconButton, ThemeToggle } from '../ui'

/**
 * Page chrome shared in spirit across both consoles: a sticky header with the
 * product mark, a version badge, theme toggle and settings button, plus a
 * centered, responsive content column.
 */
export function AppShell({
  title,
  tagline,
  mark,
  version,
  onOpenSettings,
  children,
}: {
  title: string
  tagline: string
  mark: ReactNode
  version?: string
  onOpenSettings: () => void
  children: ReactNode
}) {
  return (
    <div className="relative min-h-screen">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-grid opacity-60" />
      <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-[1.35rem] text-accent-fg shadow-sm">
              {mark}
            </span>
            <div className="leading-tight">
              <div className="flex items-center gap-2">
                <h1 className="text-base font-semibold tracking-tight text-fg">
                  {title}
                </h1>
                {version && (
                  <span className="rounded-sm border border-border bg-surface-2 px-2 py-0.5 text-[0.65rem] font-medium text-muted">
                    v{version}
                  </span>
                )}
              </div>
              <p className="hidden text-xs text-muted sm:block">{tagline}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <IconButton
              aria-label="Open settings"
              title="Settings"
              onClick={onOpenSettings}
            >
              <GearIcon className="text-[1.15rem]" />
            </IconButton>
          </div>
        </div>
      </header>
      <main className="relative mx-auto max-w-5xl px-4 pb-16 pt-6 sm:px-6">
        {children}
      </main>
    </div>
  )
}
