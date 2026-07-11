/**
 * Shared design-system barrel. This entire `src/ui/` folder is BYTE-FOR-BYTE
 * IDENTICAL between the kokoro (web/) and faster-whisper (webui/) consoles.
 * Keep it free of app-specific logic so the two copies never diverge.
 */
export { cn } from './cn'
export * from './icons'
export { Button } from './Button'
export type { ButtonProps, ButtonVariant, ButtonSize } from './Button'
export { IconButton } from './IconButton'
export type { IconButtonProps } from './IconButton'
export { Card, CardHeader, CardBody } from './Card'
export { Field } from './Field'
export { Input } from './Input'
export { TextArea } from './TextArea'
export { Select } from './Select'
export type { SelectOption, SelectProps } from './Select'
export { Slider } from './Slider'
export type { SliderProps } from './Slider'
export { Dialog } from './Dialog'
export type { DialogProps } from './Dialog'
export { Spinner } from './Spinner'
export { Badge } from './Badge'
export type { BadgeVariant } from './Badge'
export { ToastProvider, useToast } from './Toast'
export type { ToastVariant } from './Toast'
export { ThemeProvider, useTheme, ThemeToggle } from './theme'
export type { ThemePref } from './theme'
