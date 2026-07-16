import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../lib/apiClient'
import {
  activateModel,
  fetchSystem,
  type ModelPreset,
} from '../lib/systemApi'
import { Badge, Select, Spinner, useToast } from '../ui'

/**
 * Model-size picker. Lists the selectable Whisper sizes, shows which is loaded,
 * and switches the resident model (load/unload, persisted server-side). Disabled
 * while the server is unhealthy or a transcription/switch is in flight, so the
 * console never offers a control that would fail against the current state.
 */
export function ModelSelector({
  disabled,
  onSwitchStart,
  onSwitchSettled,
}: {
  disabled?: boolean
  onSwitchStart?: () => void
  onSwitchSettled?: (ok: boolean) => void
}) {
  const toast = useToast()
  const [presets, setPresets] = useState<ModelPreset[]>([])
  const [active, setActive] = useState('')
  const [loaded, setLoaded] = useState<string | null>(null)
  const [switching, setSwitching] = useState(false)

  const refresh = useCallback(async () => {
    const sys = await fetchSystem()
    if (sys) {
      setPresets(sys.models.presets)
      setActive(sys.models.active)
      setLoaded(sys.models.loaded)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const onChange = async (size: string) => {
    if (size === active || switching) return
    setSwitching(true)
    setActive(size) // optimistic
    onSwitchStart?.()
    try {
      const info = await activateModel(size)
      setPresets(info.presets)
      setActive(info.active)
      setLoaded(info.loaded)
      toast.success('Model switched', `${size} is now loaded and active.`)
      onSwitchSettled?.(true)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onSwitchSettled?.(false)
        return // apiClient reopens the settings dialog
      }
      toast.error(
        'Model switch failed',
        err instanceof Error ? err.message : String(err),
      )
      void refresh() // resync to the real state
      onSwitchSettled?.(false)
    } finally {
      setSwitching(false)
    }
  }

  const options = presets.map((p) => ({
    value: p.size,
    label: p.params ? `${p.label} (${p.params})` : p.label,
  }))

  return (
    <div className="flex items-center gap-3">
      <div className="min-w-[12rem]">
        <Select
          aria-label="Model size"
          value={active}
          disabled={disabled || switching || options.length === 0}
          onChange={(e) => void onChange(e.target.value)}
          options={
            options.length
              ? options
              : [{ value: '', label: 'Loading models…' }]
          }
        />
      </div>
      {switching ? (
        <span className="flex items-center gap-2 text-xs text-muted">
          <Spinner /> Loading {active}…
        </span>
      ) : loaded && loaded === active ? (
        <Badge variant="accent" title="Resident on the GPU right now">
          loaded
        </Badge>
      ) : loaded ? (
        <Badge variant="muted" title="A switch is pending">
          {loaded} loaded
        </Badge>
      ) : null}
    </div>
  )
}
