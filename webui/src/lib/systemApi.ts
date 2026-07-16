import { api } from './apiClient'

/**
 * Live system telemetry (GET /system, open) and model-mode switching
 * (GET/POST /api/model/*, auth-guarded). App-specific — not part of the shared
 * design system.
 */

export interface GpuInfo {
  name?: string
  memory_used_bytes?: number
  memory_total_bytes?: number
  utilization_pct?: number
  memory_utilization_pct?: number
  temperature_c?: number
  power_w?: number
  power_limit_w?: number
}

export interface ModelPreset {
  size: string
  label: string
  params: string
  is_active: boolean
  is_loaded: boolean
}

export interface PresetsInfo {
  active: string
  loaded: string | null
  presets: ModelPreset[]
}

export interface SystemInfo {
  version: string
  state: string
  device: string
  compute_type: string
  model: string
  gpu: GpuInfo | null
  activity: { active: number; waiting: number }
  models: PresetsInfo
}

/** Poll the open telemetry endpoint. Returns null on any transport error. */
export async function fetchSystem(): Promise<SystemInfo | null> {
  try {
    const url = await api.apiUrl('/system')
    const res = await fetch(url, { headers: { Accept: 'application/json' } })
    if (!res.ok) return null
    return (await res.json()) as SystemInfo
  } catch {
    return null
  }
}

/** Switch the resident model. Auth-guarded; throws ApiError on failure. */
export async function activateModel(size: string): Promise<PresetsInfo> {
  return api.postJson<PresetsInfo>('/api/model/activate', { size })
}
