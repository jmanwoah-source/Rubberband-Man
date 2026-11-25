/**
 * Shared date & formatting utilities for options expirations and strike display.
 */

function toIsoDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function thirdFridayOfMonth(year: number, monthIndex: number): Date {
  const firstDay = new Date(year, monthIndex, 1)
  const firstFridayOffset = (5 - firstDay.getDay() + 7) % 7
  return new Date(year, monthIndex, 1 + firstFridayOffset + 14)
}

/**
 * Returns the nearest standard 3rd-Friday monthly expiration targeting ~35 DTE
 * (at least 25 days out) formatted as YYYY-MM-DD.
 */
export function defaultNextMonthlyFriday(fromDate: Date = new Date()): string {
  const base = new Date(fromDate.getFullYear(), fromDate.getMonth(), fromDate.getDate())
  const targetMin = new Date(base.getTime() + 25 * 86_400_000)

  for (let offset = 0; offset <= 4; offset += 1) {
    const candidate = thirdFridayOfMonth(base.getFullYear(), base.getMonth() + offset)
    if (candidate >= targetMin) {
      return toIsoDate(candidate)
    }
  }
  const fallback = new Date(base.getTime() + 35 * 86_400_000)
  return toIsoDate(fallback)
}

/**
 * Safely parses option expiration strings such as:
 * - "2026-12-18"
 * - "2026-12-18 (35 DTE)"
 * - "Dec 18, 2026"
 * - "Dec 18, 2026 (35 DTE - Monthly)"
 * into a strict YYYY-MM-DD string.
 */
export function normalizeExpirationIso(raw?: string | null, fallbackDte?: number): string {
  const text = String(raw ?? '').trim()
  if (text) {
    const isoMatch = text.match(/(\d{4})-(\d{2})-(\d{2})/)
    if (isoMatch) {
      return `${isoMatch[1]}-${isoMatch[2]}-${isoMatch[3]}`
    }

    const withoutParen = text.split('(')[0].trim()
    const parsed = new Date(withoutParen)
    if (!Number.isNaN(parsed.getTime()) && parsed.getFullYear() >= 2020 && parsed.getFullYear() <= 2100) {
      return toIsoDate(parsed)
    }
  }

  if (fallbackDte && Number.isFinite(fallbackDte) && fallbackDte > 0) {
    const now = new Date()
    const target = new Date(now.getFullYear(), now.getMonth(), now.getDate() + Math.round(fallbackDte))
    // Snap to nearest Friday
    const dayDiff = (5 - target.getDay() + 7) % 7
    target.setDate(target.getDate() + dayDiff)
    return toIsoDate(target)
  }

  return defaultNextMonthlyFriday()
}

/**
 * Dynamically computes calendar DTE (minimum 1) from a YYYY-MM-DD expiration string.
 */
export function computeDteFromIso(isoDate: string, fallback = 35): number {
  const match = String(isoDate || '').trim().match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!match) return fallback
  const y = Number(match[1])
  const m = Number(match[2]) - 1
  const d = Number(match[3])
  const expUtc = Date.UTC(y, m, d)
  const now = new Date()
  const todayUtc = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((expUtc - todayUtc) / 86_400_000)
  return Number.isFinite(diffDays) ? Math.max(1, diffDays) : fallback
}

/**
 * Formats option strike prices cleanly without rounding half-dollar strikes (e.g. $142.50 stays $142.50, $140 stays $140).
 */
export function formatStrike(val: number | null | undefined): string {
  const num = Number(val)
  if (!Number.isFinite(num)) return '$0'
  return Math.abs(num - Math.round(num)) < 1e-4 ? `$${Math.round(num)}` : `$${num.toFixed(2)}`
}
