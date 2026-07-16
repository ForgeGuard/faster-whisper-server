import { useCallback, useEffect, useRef, useState } from 'react'
import { AppShell } from './components/AppShell'
import { GpuMonitor } from './components/GpuMonitor'
import { ModelSelector } from './components/ModelSelector'
import {
  NotFound,
  consoleHome,
  isUnknownRoute,
} from './components/NotFound'
import { SettingsDialog } from './components/SettingsDialog'
import {
  AudioInput,
  type AudioSelection,
} from './components/stt/AudioInput'
import { TranscriptPanel } from './components/stt/TranscriptPanel'
import { api, ApiError } from './lib/apiClient'
import {
  fetchServerStatus,
  isWarmingError,
  type ServerStatus,
} from './lib/health'
import {
  fetchModel,
  LANGUAGES,
  transcribe,
  type ResponseFormat,
  type Task,
  type TranscriptionResult,
} from './lib/sttApi'
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  KeyIcon,
  MicIcon,
  Select,
  Spinner,
  cn,
  useToast,
} from './ui'

const FORMATS: { value: ResponseFormat; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'json', label: 'JSON' },
  { value: 'verbose_json', label: 'Verbose JSON (segments)' },
]

// Branding: the full product name is the app title; the section names the
// current view. The browser tab reads "<Section> · <App title>".
const APP_TITLE = 'ForgeGuard Faster Whisper Server'
const SECTION = 'Transcribe'

export default function App() {
  const toast = useToast()
  const [ready, setReady] = useState(false)
  const [serverStatus, setServerStatus] = useState<ServerStatus | 'connecting'>(
    'connecting',
  )
  const [version, setVersion] = useState('')
  const [settingsOpen, setSettingsOpen] = useState(false)
  // True once the server has answered 401: auth is enabled and we lack a valid
  // key. Drives the inline "Enter API key" affordance.
  const [authRequired, setAuthRequired] = useState(false)

  const [selection, setSelection] = useState<AudioSelection | null>(null)
  const [task, setTask] = useState<Task>('transcribe')
  const [language, setLanguage] = useState('')
  const [format, setFormat] = useState<ResponseFormat>('verbose_json')
  const [wordTimestamps, setWordTimestamps] = useState(true)

  const [transcribing, setTranscribing] = useState(false)
  // Task captured when the in-flight request started (the selector can change
  // mid-request); drives the button label and completion/failure toasts.
  const [inFlightTask, setInFlightTask] = useState<Task | null>(null)
  const [result, setResult] = useState<TranscriptionResult | null>(null)
  // Server upload cap from /web/config (0 = disabled) for a client-side preflight.
  const [maxUploadBytes, setMaxUploadBytes] = useState(0)
  const abortRef = useRef<AbortController | null>(null)

  // Authorized probe: hitting /v1/models with the stored key is the signal that
  // a valid key (or open API) is in effect — clears the auth-required state.
  const loadModel = useCallback(async () => {
    try {
      await fetchModel()
      setAuthRequired(false)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return
      // Non-fatal: the console still works even if the probe fails.
    }
  }, [])

  // Reopen settings automatically on auth failure.
  useEffect(() => {
    return api.onUnauthorized(() => {
      setAuthRequired(true)
      setSettingsOpen(true)
      toast.error('Authentication required', 'Enter a valid API key to continue.')
    })
  }, [toast])

  useEffect(() => {
    let alive = true
    api.init().then(async () => {
      if (!alive) return
      setVersion(api.getVersion())
      setReady(true)
      void loadModel()
      // The shared apiClient bootstrap only stores root_path/version, so read
      // the upload cap from /web/config directly.
      try {
        const res = await fetch(`${api.getRootPath()}/web/config`, {
          headers: { Accept: 'application/json' },
        })
        if (res.ok) {
          const cfg = (await res.json()) as { max_upload_bytes?: number }
          if (alive && typeof cfg.max_upload_bytes === 'number') {
            setMaxUploadBytes(cfg.max_upload_bytes)
          }
        }
      } catch {
        /* no config endpoint — skip the preflight */
      }
    })
    return () => {
      alive = false
    }
  }, [loadModel])

  // Track model warmup: poll /health until it reports healthy. Re-armed by
  // setting serverStatus back to 'warming' (e.g. on a model_warming 503).
  // 'failed' is NOT terminal: keep polling (slower) so a restarted/recovered
  // server flips the UI back to healthy without a manual refresh.
  useEffect(() => {
    if (serverStatus === 'healthy') return
    let alive = true
    let timer: number | undefined
    const poll = async () => {
      const { status, error } = await fetchServerStatus()
      if (!alive) return
      if (status === 'healthy') {
        if (serverStatus === 'warming' || serverStatus === 'failed') {
          toast.success('Model ready', 'The server is healthy again.')
        }
        setServerStatus('healthy')
        return
      }
      if (status === 'failed' && serverStatus !== 'failed') {
        toast.error('Model failed to load', error ?? 'Check the server logs.')
      }
      setServerStatus(status) // 'warming' | 'unreachable' | 'failed'
      timer = window.setTimeout(poll, status === 'failed' ? 10000 : 3000)
    }
    void poll()
    return () => {
      alive = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [serverStatus, toast])

  const [notFound] = useState(isUnknownRoute)

  // Browser-tab title: "<Section> · <App title>".
  useEffect(() => {
    document.title = notFound
      ? `Not found · ${APP_TITLE}`
      : `${SECTION} · ${APP_TITLE}`
  }, [notFound])

  const warming = serverStatus === 'warming' || serverStatus === 'connecting'
  const canRun =
    ready && !transcribing && serverStatus === 'healthy' && Boolean(selection)

  // Switching the resident model takes the server through WARMING again; re-arm
  // the health poll so the console reflects it and re-enables when ready.
  const onModelSwitchStart = useCallback(() => {
    setServerStatus('warming')
  }, [])

  const selectAudio = (sel: AudioSelection) => {
    setSelection((prev) => {
      if (prev) URL.revokeObjectURL(prev.url)
      return sel
    })
    setResult(null)
  }

  const clearAudio = () => {
    setSelection((prev) => {
      if (prev) URL.revokeObjectURL(prev.url)
      return null
    })
    setResult(null)
  }

  const onRun = async () => {
    if (!canRun || !selection) return
    if (maxUploadBytes > 0 && selection.blob.size > maxUploadBytes) {
      toast.error(
        'File too large',
        `The server accepts up to ${(maxUploadBytes / (1024 * 1024)).toFixed(0)} MB per upload.`,
      )
      return
    }
    const requestTask = task // capture: the selector can change mid-request
    const controller = new AbortController()
    abortRef.current = controller
    setInFlightTask(requestTask)
    setTranscribing(true)
    try {
      const res = await transcribe(
        {
          file: selection.blob,
          filename: selection.filename,
          task: requestTask,
          language:
            requestTask === 'transcribe' ? language || undefined : undefined,
          responseFormat: format,
          wordTimestamps,
        },
        controller.signal,
      )
      setResult(res)
      toast.success(
        requestTask === 'translate'
          ? 'Translation complete'
          : 'Transcription complete',
      )
    } catch (err) {
      if (controller.signal.aborted) {
        toast.info('Cancelled')
        return
      }
      if (err instanceof ApiError && err.status === 401) return
      if (
        err instanceof ApiError &&
        err.status === 503 &&
        isWarmingError(err.detail)
      ) {
        // Model still warming — resume polling; the banner shows progress.
        setServerStatus('warming')
        toast.info('Model warming up', 'Hang tight — this unlocks when it finishes.')
        return
      }
      toast.error(
        requestTask === 'translate' ? 'Translation failed' : 'Transcription failed',
        err instanceof Error ? err.message : String(err),
      )
    } finally {
      abortRef.current = null
      setInFlightTask(null)
      setTranscribing(false)
    }
  }

  const onCancel = () => {
    abortRef.current?.abort()
  }

  const verb =
    (inFlightTask ?? task) === 'translate' ? 'Translate' : 'Transcribe'
  const wordsEnabled = format === 'verbose_json' && task === 'transcribe'

  if (notFound) {
    return <NotFound home={consoleHome()} />
  }

  return (
    <AppShell
      title={APP_TITLE}
      tagline={SECTION}
      mark={<MicIcon />}
      version={version}
      onOpenSettings={() => setSettingsOpen(true)}
    >
      {warming && ready && (
        <div
          role="status"
          className="mb-6 flex animate-fade-in items-center gap-3 rounded-xl border border-border bg-accent-soft px-4 py-3 text-sm text-fg"
        >
          <Spinner />
          <div>
            <span className="font-medium">The speech model is warming up.</span>{' '}
            <span className="text-muted">
              This can take a little while on a cold start — transcription
              unlocks automatically when it&apos;s ready.
            </span>
          </div>
        </div>
      )}
      {serverStatus === 'failed' && (
        <div
          role="alert"
          className="mb-6 rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-fg"
        >
          <span className="font-medium">The speech model failed to load.</span>{' '}
          <span className="text-muted">
            Check the server logs — this console keeps watching and recovers
            automatically once the server is healthy again.
          </span>
        </div>
      )}
      {/* Model mode + live GPU/activity monitor strip */}
      <div className="mb-6 flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-fg">Model</span>
            <span className="text-xs text-faint">
              Switch the resident Whisper size — larger is more accurate, smaller
              is faster and lighter on VRAM.
            </span>
          </div>
          <ModelSelector
            disabled={warming || transcribing}
            onSwitchStart={onModelSwitchStart}
          />
        </div>
        <GpuMonitor />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        {/* Main column */}
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader
              title="Audio input"
              description="Upload a file or record from your microphone."
            />
            <CardBody>
              <AudioInput
                selection={selection}
                onSelect={selectAudio}
                onClear={clearAudio}
                disabled={transcribing}
                onError={(m) => toast.error('Invalid input', m)}
              />
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <Button
                  size="lg"
                  onClick={onRun}
                  disabled={!canRun}
                  loading={transcribing}
                >
                  {transcribing ? `${verb.slice(0, -1)}ing…` : verb}
                </Button>
                {transcribing && (
                  <Button size="lg" variant="secondary" onClick={onCancel}>
                    Cancel
                  </Button>
                )}
                {authRequired && (
                  <Button
                    size="lg"
                    variant="secondary"
                    onClick={() => setSettingsOpen(true)}
                  >
                    <KeyIcon />
                    Enter API key
                  </Button>
                )}
                {!ready && (
                  <span className="flex items-center gap-2 text-sm text-muted">
                    <Spinner /> Connecting…
                  </span>
                )}
                {ready && !selection && (
                  <span className="text-sm text-faint">Add audio to begin</span>
                )}
              </div>
            </CardBody>
          </Card>

          {result && (
            <Card>
              <CardHeader
                title="Transcript"
                description="Copy, download, or inspect per-segment timing."
              />
              <CardBody>
                <TranscriptPanel result={result} />
              </CardBody>
            </Card>
          )}
        </div>

        {/* Options sidebar */}
        <div className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Options" />
            <CardBody className="space-y-5">
              <Field label="Mode">
                {() => (
                  <div className="inline-flex w-full overflow-hidden rounded-sm border border-border text-sm">
                    {(['transcribe', 'translate'] as Task[]).map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setTask(t)}
                        className={cn(
                          'flex-1 px-3 py-1.5 capitalize transition-colors',
                          task === t
                            ? 'bg-accent text-accent-fg'
                            : 'bg-surface text-muted hover:text-fg',
                        )}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                )}
              </Field>
              <Field
                label="Language"
                hint={task === 'translate' ? 'auto → English' : undefined}
              >
                {(id) => (
                  <Select
                    id={id}
                    value={task === 'translate' ? '' : language}
                    disabled={task === 'translate'}
                    onChange={(e) => setLanguage(e.target.value)}
                    options={LANGUAGES}
                  />
                )}
              </Field>
              <Field label="Response format">
                {(id) => (
                  <Select
                    id={id}
                    value={format}
                    onChange={(e) =>
                      setFormat(e.target.value as ResponseFormat)
                    }
                    options={FORMATS}
                  />
                )}
              </Field>
              <label
                className={cnWordRow(wordsEnabled)}
                aria-disabled={!wordsEnabled}
              >
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 rounded border-border-strong text-accent accent-accent focus-visible:ring-2 focus-visible:ring-accent/60"
                  checked={wordTimestamps && wordsEnabled}
                  disabled={!wordsEnabled}
                  onChange={(e) => setWordTimestamps(e.target.checked)}
                />
                <span>
                  <span className="block text-sm font-medium text-fg">
                    Word timestamps
                  </span>
                  <span className="block text-xs text-muted">
                    Transcribe + verbose JSON only
                  </span>
                </span>
              </label>
            </CardBody>
          </Card>
        </div>
      </div>

      <SettingsDialog
        open={settingsOpen}
        onClose={() => {
          setSettingsOpen(false)
          // Retry with the (possibly new) key so the console recovers without
          // a manual refresh.
          if (authRequired) void loadModel()
        }}
      />
    </AppShell>
  )
}

function cnWordRow(enabled: boolean): string {
  return [
    'flex items-start gap-3 rounded-lg border border-border bg-surface-2/40 p-3 transition-opacity',
    enabled ? 'cursor-pointer' : 'cursor-not-allowed opacity-60',
  ].join(' ')
}
