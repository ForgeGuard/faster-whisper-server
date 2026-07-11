import { api } from './apiClient'

export type ResponseFormat = 'text' | 'json' | 'verbose_json'

export interface Word {
  word: string
  start: number
  end: number
  probability: number
}

export interface Segment {
  id: number
  start: number
  end: number
  text: string
  words?: Word[] | null
}

export interface TranscriptionResult {
  text: string
  language?: string
  duration?: number
  segments?: Segment[]
  words?: Word[]
  raw: unknown
}

export type Task = 'transcribe' | 'translate'

export interface TranscribeParams {
  file: File | Blob
  filename: string
  model?: string
  task?: Task
  language?: string
  responseFormat: ResponseFormat
  wordTimestamps?: boolean
}

/** POST a transcription/translation request as multipart form and normalize the result. */
export async function transcribe(
  params: TranscribeParams,
): Promise<TranscriptionResult> {
  const task: Task = params.task ?? 'transcribe'
  // OpenAI's translation endpoint always targets English and takes no source
  // `language` or timestamp granularities.
  const endpoint =
    task === 'translate' ? '/v1/audio/translations' : '/v1/audio/transcriptions'

  const form = new FormData()
  form.append('file', params.file, params.filename)
  form.append('model', params.model ?? 'whisper-1')
  form.append('response_format', params.responseFormat)
  if (task === 'transcribe' && params.language) {
    form.append('language', params.language)
  }
  if (
    task === 'transcribe' &&
    params.wordTimestamps &&
    params.responseFormat === 'verbose_json'
  ) {
    form.append('timestamp_granularities[]', 'word')
  }

  if (params.responseFormat === 'text') {
    const text = await api.postFormText(endpoint, form)
    return { text: text.trim(), raw: text }
  }

  const data = await api.postForm<Record<string, unknown>>(endpoint, form)
  return {
    text: String((data.text as string) ?? ''),
    language: data.language as string | undefined,
    duration: data.duration as number | undefined,
    segments: (data.segments as Segment[] | undefined) ?? undefined,
    words: (data.words as Word[] | undefined) ?? undefined,
    raw: data,
  }
}

interface ModelEntry {
  id: string
}

/** Fetch the configured model id (the non-alias entry from GET /v1/models). */
export async function fetchModel(): Promise<string> {
  const data = await api.getJson<{ data?: ModelEntry[] }>('/v1/models')
  const ids = (data.data ?? []).map((m) => m.id)
  return ids.find((id) => id !== 'whisper-1') ?? ids[0] ?? 'whisper-1'
}

function srtTime(s: number, sep: string): string {
  const ms = Math.round(s * 1000)
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  const sec = Math.floor((ms % 60000) / 1000)
  const milli = ms % 1000
  const p = (n: number, w = 2) => String(n).padStart(w, '0')
  return `${p(h)}:${p(m)}:${p(sec)}${sep}${p(milli, 3)}`
}

/** Build an SRT subtitle document from segment timings. */
export function toSrt(segments: Segment[]): string {
  return segments
    .map((seg, i) => {
      const start = srtTime(seg.start, ',')
      const end = srtTime(seg.end, ',')
      return `${i + 1}\n${start} --> ${end}\n${seg.text.trim()}\n`
    })
    .join('\n')
}

/** Build a WebVTT subtitle document from segment timings. */
export function toVtt(segments: Segment[]): string {
  const body = segments
    .map((seg) => {
      const start = srtTime(seg.start, '.')
      const end = srtTime(seg.end, '.')
      return `${start} --> ${end}\n${seg.text.trim()}\n`
    })
    .join('\n')
  return `WEBVTT\n\n${body}`
}

/** A curated set of common language codes for the selector (empty = auto-detect). */
export const LANGUAGES: { value: string; label: string }[] = [
  { value: '', label: 'Auto-detect' },
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'nl', label: 'Dutch' },
  { value: 'ru', label: 'Russian' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'ko', label: 'Korean' },
  { value: 'hi', label: 'Hindi' },
  { value: 'ar', label: 'Arabic' },
  { value: 'tr', label: 'Turkish' },
  { value: 'pl', label: 'Polish' },
  { value: 'uk', label: 'Ukrainian' },
]
