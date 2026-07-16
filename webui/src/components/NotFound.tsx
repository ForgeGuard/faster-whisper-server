import { Button } from '../ui'

/**
 * Not-found view for an unknown client route under the console base. The server
 * SPA-fallbacks extensionless paths to index.html, so a deep link like
 * `/web/nope` lands here rather than showing a blank app.
 */
export function NotFound({ home }: { home: string }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-5 px-6 text-center">
      <p className="text-6xl font-semibold tracking-tight text-faint">404</p>
      <div className="space-y-1">
        <h1 className="text-lg font-semibold text-fg">Page not found</h1>
        <p className="max-w-sm text-sm text-muted">
          This console has a single view. The address you opened doesn’t match
          anything here.
        </p>
      </div>
      <Button onClick={() => (window.location.href = home)}>
        Back to the console
      </Button>
    </div>
  )
}

/** True when the current path points below the console base (an unknown route). */
export function isUnknownRoute(): boolean {
  const path = window.location.pathname.replace(/\/+$/, '')
  const idx = path.lastIndexOf('/web')
  if (idx === -1) return false
  // Exactly ".../web" is home; a further segment (".../web/foo") is unknown.
  return path.slice(idx + 4).length > 0
}

/** The console home URL (".../web/") for the current deployment prefix. */
export function consoleHome(): string {
  const path = window.location.pathname
  const idx = path.lastIndexOf('/web')
  const base = idx === -1 ? '' : path.slice(0, idx)
  return `${base}/web/`
}
