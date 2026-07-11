import { useCallback, useEffect, useState } from 'react'
import { AppShell } from './components/AppShell'
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
  Badge,
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

export default function App() {
  const toast = useToast()
  const [ready, setReady] = useState(false)
  const [serverStatus, setServerStatus] = useState<ServerStatus | 'connecting'>(
    'connecting',
  )
  const [version, setVersion] = useState('')
  const [model, setModel] = useState('')
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
  const [result, setResult] = useState<TranscriptionResult | null>(null)

  // Authorized data load: doubles as the model-chip source and the signal that
  // a valid key (or open API) is in effect — clears the auth-required state.
  const loadModel = useCallback(async () => {
    try {
      const id = await fetchModel()
      setAuthRequired(false)
      setModel(id)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return
      // Non-fatal: the console still works; the model chip just stays empty.
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
    api.init().then(() => {
      if (!alive) return
      setVersion(api.getVersion())
      setReady(true)
      void loadModel()
    })
    return () => {
      alive = false
    }
  }, [loadModel])

  // Track model warmup: poll /health until it reports healthy. Re-armed by
  // setting serverStatus back to 'warming' (e.g. on a model_warming 503).
  useEffect(() => {
    if (serverStatus === 'healthy' || serverStatus === 'failed') return
    let alive = true
    let timer: number | undefined
    const poll = async () => {
      const { status, error } = await fetchServerStatus()
      if (!alive) return
      if (status === 'healthy') {
        if (serverStatus === 'warming') {
          toast.success('Model ready', 'Warmup complete.')
        }
        setServerStatus('healthy')
        return
      }
      if (status === 'failed') {
        setServerStatus('failed')
        toast.error('Model failed to load', error ?? 'Check the server logs.')
        return
      }
      setServerStatus(status) // 'warming' | 'unreachable'
      timer = window.setTimeout(poll, 3000)
    }
    void poll()
    return () => {
      alive = false
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [serverStatus, toast])

  const warming = serverStatus === 'warming' || serverStatus === 'connecting'
  const canRun =
    ready && !transcribing && serverStatus === 'healthy' && Boolean(selection)

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
    setTranscribing(true)
    try {
      const res = await transcribe({
        file: selection.blob,
        filename: selection.filename,
        task,
        language: task === 'transcribe' ? language || undefined : undefined,
        responseFormat: format,
        wordTimestamps,
      })
      setResult(res)
      toast.success(
        task === 'translate' ? 'Translation complete' : 'Transcription complete',
      )
    } catch (err) {
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
        task === 'translate' ? 'Translation failed' : 'Transcription failed',
        err instanceof Error ? err.message : String(err),
      )
    } finally {
      setTranscribing(false)
    }
  }

  const verb = task === 'translate' ? 'Translate' : 'Transcribe'

  return (
    <AppShell
      title="ForgeGuard Faster Whisper"
      tagline="Speech-to-text console"
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
            Check the server logs — the container usually restarts on its own.
          </span>
        </div>
      )}
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
            <CardHeader
              title="Options"
              action={
                model ? (
                  <Badge variant="muted" title="Configured server model">
                    {model}
                  </Badge>
                ) : undefined
              }
            />
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
                className={cnWordRow(format, task)}
                aria-disabled={format !== 'verbose_json' || task === 'translate'}
              >
                <input
                  type="checkbox"
                  className="h-4 w-4 shrink-0 rounded border-border-strong text-accent accent-accent focus-visible:ring-2 focus-visible:ring-accent/60"
                  checked={
                    wordTimestamps &&
                    format === 'verbose_json' &&
                    task === 'transcribe'
                  }
                  disabled={format !== 'verbose_json' || task === 'translate'}
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

function cnWordRow(format: ResponseFormat, task: Task): string {
  const enabled = format === 'verbose_json' && task === 'transcribe'
  return [
    'flex items-start gap-3 rounded-lg border border-border bg-surface-2/40 p-3 transition-opacity',
    enabled ? 'cursor-pointer' : 'cursor-not-allowed opacity-60',
  ].join(' ')
}
