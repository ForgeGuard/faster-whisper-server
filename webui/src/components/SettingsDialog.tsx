import { useEffect, useState } from 'react'
import { Button, Dialog, Field, Input, KeyIcon, useToast } from '../ui'
import { api } from '../lib/apiClient'

/**
 * API-key settings dialog. Shared shape across both consoles: reads/writes the
 * 'apiKey' localStorage entry via the shared apiClient.
 */
export function SettingsDialog({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const toast = useToast()
  const [value, setValue] = useState('')
  const [reveal, setReveal] = useState(false)

  useEffect(() => {
    if (open) {
      setValue(api.getApiKey())
      setReveal(false)
    }
  }, [open])

  const save = () => {
    api.setApiKey(value)
    toast.success(
      value.trim() ? 'API key saved' : 'API key cleared',
      value.trim()
        ? 'Requests will be authenticated.'
        : 'Requests will be sent without authentication.',
    )
    onClose()
  }

  const clear = () => {
    setValue('')
    api.clearApiKey()
    toast.info('API key cleared')
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      icon={<KeyIcon />}
      title="Settings"
      description="Configure the API key used to authenticate requests."
      footer={
        <>
          <Button variant="ghost" onClick={clear}>
            Clear
          </Button>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={save}>Save</Button>
        </>
      }
    >
      <div className="space-y-4">
        <Field
          label="API key"
          hint={reveal ? 'visible' : 'hidden'}
        >
          {(id) => (
            <div className="flex gap-2">
              <Input
                id={id}
                type={reveal ? 'text' : 'password'}
                autoComplete="off"
                spellCheck={false}
                placeholder="sk-…"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') save()
                }}
                className="font-mono"
              />
              <Button
                variant="secondary"
                size="md"
                onClick={() => setReveal((r) => !r)}
                type="button"
              >
                {reveal ? 'Hide' : 'Show'}
              </Button>
            </div>
          )}
        </Field>
        <p className="text-xs leading-relaxed text-muted">
          The key is stored locally in your browser only and sent as a{' '}
          <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[0.7rem] text-fg">
            Bearer
          </code>{' '}
          token. Leave it empty if the server has authentication disabled.
        </p>
      </div>
    </Dialog>
  )
}
