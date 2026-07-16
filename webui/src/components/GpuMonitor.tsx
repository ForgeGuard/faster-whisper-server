import { useEffect, useRef, useState } from 'react'
import { fetchSystem, type GpuInfo, type SystemInfo } from '../lib/systemApi'
import { cn } from '../ui'

function gb(n: number): string {
  return `${(n / 1e9).toFixed(1)} GB`
}

// Green under moderate load, amber as it fills, red when saturated — a quick
// read on how hard the GPU is working without parsing the numbers.
function loadColor(pct: number): string {
  if (pct >= 90) return 'bg-danger'
  if (pct >= 70) return 'bg-warning'
  return 'bg-success'
}

function Meter({
  label,
  value,
  pct,
}: {
  label: string
  value: string
  pct: number
}) {
  const clamped = Math.max(0, Math.min(100, pct))
  return (
    <div className="min-w-[7rem] flex-1">
      <div className="flex items-baseline justify-between gap-2 text-xs">
        <span className="text-faint">{label}</span>
        <span className="font-medium tabular-nums text-muted">{value}</span>
      </div>
      <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className={cn('h-full rounded-full transition-all', loadColor(clamped))}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}

function GpuMeters({ gpu }: { gpu: GpuInfo }) {
  const used = gpu.memory_used_bytes ?? 0
  const total = gpu.memory_total_bytes ?? 0
  const memPct = total > 0 ? (used / total) * 100 : 0
  return (
    <>
      {gpu.utilization_pct != null && (
        <Meter
          label="GPU"
          value={`${gpu.utilization_pct}%`}
          pct={gpu.utilization_pct}
        />
      )}
      {total > 0 && (
        <Meter
          label="VRAM"
          value={`${gb(used)} / ${gb(total)}`}
          pct={memPct}
        />
      )}
      {gpu.temperature_c != null && (
        <div className="text-xs text-faint">
          temp{' '}
          <span className="font-medium tabular-nums text-muted">
            {gpu.temperature_c}°C
          </span>
        </div>
      )}
      {gpu.power_w != null && (
        <div className="text-xs text-faint">
          power{' '}
          <span className="font-medium tabular-nums text-muted">
            {gpu.power_w}
            {gpu.power_limit_w != null ? ` / ${gpu.power_limit_w}` : ''} W
          </span>
        </div>
      )}
    </>
  )
}

function ActivityPill({ active, waiting }: { active: number; waiting: number }) {
  const busy = active > 0 || waiting > 0
  return (
    <div className="flex items-center gap-1.5 text-xs">
      <span
        className={cn(
          'inline-block h-2 w-2 rounded-full',
          busy ? 'animate-pulse bg-accent' : 'bg-border-strong',
        )}
      />
      <span className="text-muted">
        {active} running{waiting > 0 ? ` · ${waiting} queued` : ''}
      </span>
    </div>
  )
}

/**
 * Compact GPU-performance + request-activity monitor, theme-matched to the
 * console. Polls the open /system endpoint every 3s; the reusable sibling of
 * qwen3-tts-server's GpuMonitor. Renders nothing until the first poll returns.
 */
export function GpuMonitor() {
  const [system, setSystem] = useState<SystemInfo | null>(null)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    let alive = true
    const poll = async () => {
      const data = await fetchSystem()
      if (!alive) return
      if (data) setSystem(data)
      timer.current = window.setTimeout(poll, 3000)
    }
    void poll()
    return () => {
      alive = false
      if (timer.current !== null) window.clearTimeout(timer.current)
    }
  }, [])

  if (!system) return null

  const gpu = system.gpu
  const activity = system.activity ?? { active: 0, waiting: 0 }

  return (
    <div className="rounded-xl border border-border bg-surface-2/50 px-4 py-2.5">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-faint">
            Monitor
          </span>
          {gpu?.name && (
            <span
              className="max-w-[12rem] truncate text-xs text-faint"
              title={gpu.name}
            >
              {gpu.name}
            </span>
          )}
        </div>
        {gpu ? (
          <GpuMeters gpu={gpu} />
        ) : (
          <span className="text-xs text-faint">
            GPU telemetry unavailable (no NVIDIA driver)
          </span>
        )}
        <ActivityPill active={activity.active} waiting={activity.waiting} />
      </div>
    </div>
  )
}
