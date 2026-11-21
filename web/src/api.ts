import type {
  BootstrapResponse,
  DiaryResponse,
  LedgerResponse,
  TickerDetailResponse,
} from './types'

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let msg = `Request failed (${res.status})`
    try {
      const errBody = (await res.json()) as { detail?: string }
      if (errBody?.detail) msg = errBody.detail
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

export function createSimulatedTrade(payload: {
  symbol: string
  action: string
  option_type: string
  strike: number
  short_strike?: number | null
  expiration_date: string
  quantity: number
  limit_price: number
  stock_price_at_entry: number
  strategy: string
  order_type: string
  target_stock_price?: number | null
  stop_stock_price?: number | null
  conviction_score: number
  notes: string
  dte?: number
}) {
  return requestJson<{ ok: boolean }>('/api/diary/trades', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function closeSimulatedTrade(
  tradeId: number,
  payload: { exit_premium: number; exit_stock_price: number; exit_notes?: string },
) {
  return requestJson<{ ok: boolean }>(`/api/diary/trades/${tradeId}/close`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
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
