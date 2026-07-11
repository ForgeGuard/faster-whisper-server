import { api } from './apiClient'

/**
 * Server health polling (app-specific, not part of the shared design system).
 *
 * The server answers /health immediately after boot while the model warms in
 * a background task: {"status":"warming"} -> {"status":"healthy"}. A failed
 * warmup reports 503 {"status":"failed"} briefly before the process exits.
 */

export type ServerStatus = 'warming' | 'healthy' | 'failed' | 'unreachable'

interface HealthResponse {
  status?: string
  model_loaded?: boolean
  error?: string
}

export async function fetchServerStatus(): Promise<{
  status: ServerStatus
  error?: string
}> {
  try {
    const url = await api.apiUrl('/health')
    const res = await fetch(url, { headers: { Accept: 'application/json' } })
    const body = (await res.json()) as HealthResponse
    if (body.status === 'healthy') return { status: 'healthy' }
    if (body.status === 'warming') return { status: 'warming' }
    return { status: 'failed', error: body.error }
  } catch {
    return { status: 'unreachable' }
  }
}

/** True when an ApiError detail is the server's "model still warming" 503. */
export function isWarmingError(detail: unknown): boolean {
  if (!detail || typeof detail !== 'object') return false
  const d = (detail as { detail?: { error?: string } }).detail
  return d?.error === 'model_warming'
}
