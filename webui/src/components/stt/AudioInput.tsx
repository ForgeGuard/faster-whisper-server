import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Button,
  FileAudioIcon,
  IconButton,
  MicIcon,
  StopIcon,
  TrashIcon,
  UploadIcon,
  cn,
} from '../../ui'

export interface AudioSelection {
  blob: Blob
  filename: string
  /** Object URL for local preview; revoked when the selection changes. */
  url: string
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

export function AudioInput({
  selection,
  onSelect,
  onClear,
  disabled,
  onError,
}: {
  selection: AudioSelection | null
  onSelect: (sel: AudioSelection) => void
  onClear: () => void
  disabled?: boolean
  onError?: (message: string) => void
}) {
  const [dragging, setDragging] = useState(false)
  const [recording, setRecording] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  // getUserMedia is only available in a secure context (HTTPS or http://localhost).
  const recordingSupported =
    typeof window !== 'undefined' &&
    window.isSecureContext &&
    !!navigator.mediaDevices?.getUserMedia
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)

  const select = useCallback(
    (blob: Blob, filename: string) => {
      const url = URL.createObjectURL(blob)
      onSelect({ blob, filename, url })
    },
    [onSelect],
  )

  const handleFiles = useCallback(
    (files: FileList | null) => {
      const file = files?.[0]
      if (!file) return
      if (!file.type.startsWith('audio/') && !/\.(wav|mp3|m4a|flac|ogg|opus|webm|aac)$/i.test(file.name)) {
        onError?.('Please choose an audio file.')
        return
      }
      select(file, file.name)
    },
    [select, onError],
  )

  const startRecording = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      // navigator.mediaDevices is only exposed in a secure context (HTTPS or
      // http://localhost), so an insecure LAN origin fails here in every browser.
      onError?.(
        window.isSecureContext
          ? 'Recording is not supported in this browser.'
          : 'Microphone recording needs a secure context — open the console over HTTPS or http://localhost. File upload works on any origin.',
      )
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = () => {
        const type = recorder.mimeType || 'audio/webm'
        const blob = new Blob(chunksRef.current, { type })
        const ext = type.includes('ogg') ? 'ogg' : 'webm'
        select(blob, `recording-${Date.now()}.${ext}`)
        stream.getTracks().forEach((t) => t.stop())
      }
      recorder.start()
      recorderRef.current = recorder
      setRecording(true)
      setElapsed(0)
      timerRef.current = window.setInterval(
        () => setElapsed((e) => e + 1),
        1000,
      )
    } catch {
      onError?.('Microphone access was denied.')
    }
  }, [select, onError])

  const stopRecording = useCallback(() => {
    recorderRef.current?.stop()
    recorderRef.current = null
    setRecording(false)
    if (timerRef.current) {
      window.clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current)
      recorderRef.current?.stream?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  // Selected state — show a preview card.
  if (selection) {
    return (
      <div className="flex items-center gap-4 rounded-xl border border-border bg-surface-2/60 p-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-[1.4rem] text-accent">
          <FileAudioIcon />
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-fg">
            {selection.filename}
          </p>
          <p className="text-xs text-muted">
            {formatBytes(selection.blob.size)}
            {selection.blob.type ? ` · ${selection.blob.type}` : ''}
          </p>
          <audio
            controls
            src={selection.url}
            className="mt-2 h-9 w-full max-w-xs"
          />
        </div>
        <IconButton
          variant="ghost"
          aria-label="Remove audio"
          onClick={onClear}
          disabled={disabled}
        >
          <TrashIcon className="text-[1.15rem]" />
        </IconButton>
      </div>
    )
  }

  // Empty state — drop zone + recording.
  return (
    <div className="space-y-3">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload audio file"
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click()
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors',
          dragging
            ? 'border-accent bg-accent-soft'
            : 'border-border-strong bg-surface-2/40 hover:border-accent hover:bg-accent-soft/50',
          disabled && 'pointer-events-none opacity-50',
        )}
      >
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-surface text-[1.5rem] text-accent shadow-sm">
          <UploadIcon />
        </span>
        <div>
          <p className="text-sm font-medium text-fg">
            Drop an audio file, or{' '}
            <span className="text-accent">browse</span>
          </p>
          <p className="mt-1 text-xs text-muted">
            WAV, MP3, M4A, FLAC, OGG, WebM
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*,.wav,.mp3,.m4a,.flac,.ogg,.opus,.webm,.aac"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div className="flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-xs font-medium uppercase tracking-wide text-faint">
          or
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      {recording ? (
        <div className="flex items-center justify-between rounded-xl border border-danger/40 bg-danger/5 px-4 py-3">
          <span className="flex items-center gap-2 text-sm font-medium text-danger">
            <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-danger" />
            Recording… {formatDuration(elapsed)}
          </span>
          <Button variant="danger" size="sm" onClick={stopRecording}>
            <StopIcon className="text-[1rem]" />
            Stop
          </Button>
        </div>
      ) : (
        <>
          <Button
            variant="secondary"
            fullWidth
            onClick={startRecording}
            disabled={disabled || !recordingSupported}
          >
            <MicIcon className="text-[1.1rem]" />
            Record from microphone
          </Button>
          {!recordingSupported && (
            <p className="mt-2 text-center text-xs text-muted">
              Microphone recording needs HTTPS or http://localhost. File upload
              works on any origin.
            </p>
          )}
        </>
      )}
    </div>
  )
}
