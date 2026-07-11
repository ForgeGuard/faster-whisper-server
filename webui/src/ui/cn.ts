/**
 * Tiny classnames joiner. Filters falsy values and joins with spaces.
 * Kept dependency-free so src/ui stays identical across apps.
 */
export type ClassValue = string | number | false | null | undefined

export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ')
}
