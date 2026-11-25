import type {
  BootstrapResponse,
  DiaryPortfolioSummary,
  DiaryResponse,
  DiaryTrade,
  LedgerResponse,
  TickerDetailResponse,
} from './types'

function formatFastApiErrorDetail(detail: unknown): string | null {
  if (typeof detail === 'string' && detail.trim()) {
    return detail.trim()
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const parts = detail
      .map((entry) => {
        if (typeof entry === 'string') return entry.trim()
        if (entry && typeof entry === 'object') {
          const item = entry as { loc?: unknown[]; msg?: unknown; message?: unknown }
          const rawMsg =
            typeof item.msg === 'string'
              ? item.msg
              : typeof item.message === 'string'
                ? item.message
                : ''
          const cleanMsg = rawMsg.replace(/^Value error,\s*/i, '').trim()
          const locPath = Array.isArray(item.loc)
            ? item.loc
                .filter((seg) => seg !== 'body' && seg !== 'query' && seg !== 'path')
                .map((seg) => String(seg))
                .join('.')
            : ''
          if (locPath && cleanMsg) return `${locPath}: ${cleanMsg}`
          if (cleanMsg) return cleanMsg
        }
        return ''
      })
      .filter(Boolean)
    if (parts.length > 0) return parts.join(' • ')
  }
  if (detail && typeof detail === 'object') {
    const obj = detail as { message?: unknown; error?: unknown }
    if (typeof obj.message === 'string' && obj.message.trim()) return obj.message.trim()
    if (typeof obj.error === 'string' && obj.error.trim()) return obj.error.trim()
    try {
      return JSON.stringify(detail)
    } catch {
      return null
    }
  }
  return null
}

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const errBody = (await res.json()) as { detail?: unknown; message?: unknown }
      const parsed = formatFastApiErrorDetail(errBody?.detail ?? errBody?.message)
      if (parsed) msg = parsed
    } catch {
      // ignore non-JSON body
    }
    throw new Error(msg)
  }
  return (await res.json()) as T
}

export function fetchBootstrap(
  sector: string,
  ticker?: string,
  signal?: AbortSignal,
): Promise<BootstrapResponse> {
  const params = new URLSearchParams({ sector })
  if (ticker) params.set('ticker', ticker)
  return requestJson<BootstrapResponse>(`/api/bootstrap?${params.toString()}`, { signal })
}

export function fetchTickerDetail(
  symbol: string,
  sector: string,
  opts?: { dte?: number; holdDays?: number; ivShift?: number },
  signal?: AbortSignal,
): Promise<TickerDetailResponse> {
  const params = new URLSearchParams({
    sector,
    dte: String(opts?.dte ?? 35),
    hold_days: String(opts?.holdDays ?? 5),
    iv_shift: String(opts?.ivShift ?? 0),
  })
  return requestJson<TickerDetailResponse>(
    `/api/ticker/${encodeURIComponent(symbol)}?${params.toString()}`,
    { signal },
  )
}

export function fetchDiary(signal?: AbortSignal): Promise<DiaryResponse> {
  return requestJson<DiaryResponse>('/api/diary', { signal })
}

export interface CreateSimulatedTradePayload {
  symbol: string
  action: 'BUY_TO_OPEN' | 'SELL_TO_OPEN'
  option_type: 'CALL' | 'PUT'
  strike: number
  short_strike?: number | null
  expiration_date: string
  quantity: number
  limit_price: number
  stock_price_at_entry: number
  strategy: 'SINGLE_LEG' | 'VERTICAL_DEBIT_SPREAD'
  order_type: 'LIMIT' | 'MARKET' | 'STOP_ON_QUOTE'
  time_in_force: 'DAY' | 'GTC'
  target_stock_price?: number | null
  stop_stock_price?: number | null
  target_premium?: number | null
  stop_premium?: number | null
  implied_vol_at_entry?: number | null
  conviction_score: number
  expected_basis_pct?: number
  whale_badge?: string
  catalyst_tag?: string
  notes: string
  dte?: number
}

export function createSimulatedTrade(payload: CreateSimulatedTradePayload) {
  return requestJson<{ ok: boolean; trade?: DiaryTrade; summary?: DiaryPortfolioSummary }>(
    '/api/diary/trades',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export function updateSimulatedTrade(
  tradeId: number,
  payload: {
    target_stock_price?: number | null
    stop_stock_price?: number | null
    notes?: string
    time_in_force?: 'DAY' | 'GTC'
  },
) {
  return requestJson<{ ok: boolean; trade?: DiaryTrade; summary?: DiaryPortfolioSummary }>(
    `/api/diary/trades/${tradeId}`,
    {
      method: 'PATCH',
      body: JSON.stringify(payload),
    },
  )
}

export function voidSimulatedTrade(tradeId: number) {
  return requestJson<{ ok: boolean; summary?: DiaryPortfolioSummary }>(
    `/api/diary/trades/${tradeId}`,
    {
      method: 'DELETE',
    },
  )
}

export function closeSimulatedTrade(
  tradeId: number,
  payload: { exit_premium: number; exit_stock_price: number; exit_notes?: string },
) {
  return requestJson<{ ok: boolean; summary?: DiaryPortfolioSummary }>(
    `/api/diary/trades/${tradeId}/close`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
  )
}

export function triggerDiaryBackup() {
  return requestJson<{ ok: boolean; backup_path?: string | null }>('/api/diary/backup', {
    method: 'POST',
  })
}

export function getDiaryExportUrl(format: 'json' | 'csv'): string {
  return `/api/diary/export?format=${format}`
}

export function fetchLedger(
  date?: string,
  sector?: string,
  signal?: AbortSignal,
): Promise<LedgerResponse> {
  const params = new URLSearchParams()
  if (date) params.set('date', date)
  if (sector) params.set('sector', sector)
  return requestJson<LedgerResponse>(`/api/ledger?${params.toString()}`, { signal })
}
