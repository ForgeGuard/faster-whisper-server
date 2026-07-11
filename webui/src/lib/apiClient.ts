/**
 * Shared API client — BYTE-FOR-BYTE IDENTICAL between the kokoro (web/) and
 * faster-whisper (webui/) consoles.
 *
 * Responsibilities:
 *  - Bootstrap the base/root path from GET /web/config so the console works
 *    behind an arbitrary reverse-proxy prefix (UVICORN_ROOT_PATH). The config
 *    payload may include { root_path?, version? }; both are optional.
 *  - Read the API key from localStorage key 'apiKey' and inject it as
 *    `Authorization: Bearer <key>` on every request.
 *  - On a 401 response, clear the stored key and notify subscribers so the app
 *    can reopen the settings dialog.
 */

const API_KEY_STORAGE = 'apiKey'

export interface WebConfig {
  root_path?: string
  version?: string
}

export class ApiError extends Error {
  status: number
  detail?: unknown
  constructor(message: string, status: number, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

type UnauthorizedListener = () => void

class ApiClient {
  private rootPath = ''
  private version = ''
  private initialized = false
  private initPromise: Promise<void> | null = null
  private unauthorizedListeners = new Set<UnauthorizedListener>()

  /** Detect the root path from the current URL by stripping a trailing /web. */
  private detectRootPath(): void {
    const currentPath = window.location.pathname
    let root = ''
    if (currentPath.includes('/web/') || currentPath.endsWith('/web')) {
      const webIndex = currentPath.indexOf('/web')
      root = currentPath.substring(0, webIndex)
    }
    this.rootPath = root.replace(/\/$/, '')
  }

  private async bootstrap(): Promise<void> {
    this.detectRootPath()
    try {
      const res = await fetch(`${this.rootPath}/web/config`, {
        headers: { Accept: 'application/json' },
      })
      if (res.ok) {
        const cfg = (await res.json()) as WebConfig
        if (typeof cfg.root_path === 'string') {
          this.rootPath = cfg.root_path.replace(/\/$/, '')
        }
        if (typeof cfg.version === 'string') {
          this.version = cfg.version
        }
      }
    } catch {
      /* offline / no config endpoint — fall back to the detected root path */
    }
    this.initialized = true
  }

  init(): Promise<void> {
    if (!this.initPromise) this.initPromise = this.bootstrap()
    return this.initPromise
  }

  private async ensureReady(): Promise<void> {
    if (!this.initialized) await this.init()
  }

  getVersion(): string {
    return this.version
  }

  getRootPath(): string {
    return this.rootPath
  }

  async apiUrl(endpoint: string): Promise<string> {
    await this.ensureReady()
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
    return `${this.rootPath}${path}`
  }

  // ---- API key management -------------------------------------------------

  getApiKey(): string {
    try {
      return localStorage.getItem(API_KEY_STORAGE) ?? ''
    } catch {
      return ''
    }
  }

  setApiKey(key: string): void {
    try {
      const trimmed = key.trim()
      if (trimmed) localStorage.setItem(API_KEY_STORAGE, trimmed)
      else localStorage.removeItem(API_KEY_STORAGE)
    } catch {
      /* storage unavailable */
    }
  }

  clearApiKey(): void {
    try {
      localStorage.removeItem(API_KEY_STORAGE)
    } catch {
      /* storage unavailable */
    }
  }

  hasApiKey(): boolean {
    return this.getApiKey().length > 0
  }

  onUnauthorized(listener: UnauthorizedListener): () => void {
    this.unauthorizedListeners.add(listener)
    return () => this.unauthorizedListeners.delete(listener)
  }

  private handleUnauthorized(): void {
    this.clearApiKey()
    this.unauthorizedListeners.forEach((l) => l())
  }

  private authHeaders(existing?: HeadersInit): Headers {
    const headers = new Headers(existing)
    const key = this.getApiKey()
    if (key && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${key}`)
    }
    return headers
  }

  // ---- Core request -------------------------------------------------------

  /** Low-level fetch with auth injection and 401 handling. Returns the raw Response. */
  async request(endpoint: string, init: RequestInit = {}): Promise<Response> {
    const url = await this.apiUrl(endpoint)
    const headers = this.authHeaders(init.headers)
    const res = await fetch(url, { ...init, headers })
    if (res.status === 401) {
      this.handleUnauthorized()
      throw new ApiError('Unauthorized — check your API key.', 401)
    }
    return res
  }

  private async parseError(res: Response): Promise<ApiError> {
    let detail: unknown
    let message = `Request failed (${res.status})`
    try {
      const data = await res.json()
      detail = data
      const d = (data as { detail?: unknown })?.detail
      if (typeof d === 'string') message = d
      else if (d && typeof d === 'object' && 'message' in d) {
        message = String((d as { message: unknown }).message)
      } else if (typeof (data as { message?: unknown })?.message === 'string') {
        message = String((data as { message: unknown }).message)
      }
    } catch {
      try {
        const text = await res.text()
        if (text) message = text
      } catch {
        /* ignore */
      }
    }
    return new ApiError(message, res.status, detail)
  }

  async getJson<T>(endpoint: string): Promise<T> {
    const res = await this.request(endpoint, {
      headers: { Accept: 'application/json' },
    })
    if (!res.ok) throw await this.parseError(res)
    return (await res.json()) as T
  }

  async postJson<T>(endpoint: string, body: unknown): Promise<T> {
    const res = await this.request(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw await this.parseError(res)
    return (await res.json()) as T
  }

  /** POST a JSON body and return the response as a Blob (e.g. audio bytes). */
  async postForBlob(endpoint: string, body: unknown): Promise<Blob> {
    const res = await this.request(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw await this.parseError(res)
    return await res.blob()
  }

  /** POST multipart form data and return parsed JSON. */
  async postForm<T>(endpoint: string, form: FormData): Promise<T> {
    const res = await this.request(endpoint, { method: 'POST', body: form })
    if (!res.ok) throw await this.parseError(res)
    return (await res.json()) as T
  }

  /** POST multipart form data and return the raw text body. */
  async postFormText(endpoint: string, form: FormData): Promise<string> {
    const res = await this.request(endpoint, { method: 'POST', body: form })
    if (!res.ok) throw await this.parseError(res)
    return await res.text()
  }
}

/** Singleton — import and use across the app. */
export const api = new ApiClient()
export default api
