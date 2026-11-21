import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, RefreshCw, XCircle } from 'lucide-react'
import { closeSimulatedTrade, createSimulatedTrade, fetchDiary } from '../api'
import type { DiaryResponse, DiaryTrade, TradePrefill } from '../types'
import { LearnChip } from './LearnChip'

interface SchwabSimViewProps {
  prefill: TradePrefill | null
  learnEnabled: boolean
  onClearPrefill: () => void
}

export function SchwabSimView({ prefill, learnEnabled, onClearPrefill }: SchwabSimViewProps) {
  const [diary, setDiary] = useState<DiaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)

  // Order Form State
  const [symbol, setSymbol] = useState(prefill?.symbol ?? 'NVDA')
  const [optionType, setOptionType] = useState<'CALL' | 'PUT'>(prefill?.option_type ?? 'CALL')
  const [strategy, setStrategy] = useState<'SINGLE_LEG' | 'VERTICAL_DEBIT_SPREAD'>(
    prefill?.strategy ?? 'SINGLE_LEG',
  )
  const [strike, setStrike] = useState(String(prefill?.strike ?? 140))
  const [shortStrike, setShortStrike] = useState(
    prefill?.short_strike != null ? String(prefill.short_strike) : '',
  )
  const [expDate, setExpDate] = useState(prefill?.expiration_date ?? '2026-12-18')
  const [quantity, setQuantity] = useState('1')
  const [limitPrice, setLimitPrice] = useState(String(prefill?.limit_price ?? 4.5))
  const [spotEntry, setSpotEntry] = useState(String(prefill?.stock_price_at_entry ?? 138))
  const [targetStock, setTargetStock] = useState(
    prefill?.target_stock_price != null ? String(prefill.target_stock_price) : '',
  )
  const [stopStock, setStopStock] = useState(
    prefill?.stop_stock_price != null ? String(prefill.stop_stock_price) : '',
  )
  const [notes, setNotes] = useState(prefill?.notes ?? '')

  // Close form inline state
  const [closingId, setClosingId] = useState<number | null>(null)
  const [closePremium, setClosePremium] = useState('')
  const [closeSpot, setCloseSpot] = useState('')

  useEffect(() => {
    if (!prefill) return
    setSymbol(prefill.symbol)
    setOptionType(prefill.option_type)
    setStrategy(prefill.strategy)
    setStrike(prefill.strike.toFixed(2))
    setShortStrike(prefill.short_strike != null ? prefill.short_strike.toFixed(2) : '')
    setExpDate(prefill.expiration_date)
    setLimitPrice(prefill.limit_price.toFixed(2))
    setSpotEntry(prefill.stock_price_at_entry.toFixed(2))
    setTargetStock(prefill.target_stock_price != null ? prefill.target_stock_price.toFixed(2) : '')
    setStopStock(prefill.stop_stock_price != null ? prefill.stop_stock_price.toFixed(2) : '')
    setNotes(prefill.notes)
  }, [prefill])

  const loadDiary = useCallback(async (signal?: AbortSignal) => {
    setLoading(true)
    try {
      const res = await fetchDiary(signal)
      setDiary(res)
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setFeedback({ kind: 'err', text: (err as Error).message })
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const ac = new AbortController()
    void loadDiary(ac.signal)
    return () => ac.abort()
  }, [loadDiary])

  const qtyNum = Math.max(1, Number.parseInt(quantity, 10) || 1)
  const limNum = Math.max(0.01, Number.parseFloat(limitPrice) || 0)
  const maxRisk = qtyNum * limNum * 100

  const handleTransmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setFeedback(null)
    try {
      const kNum = Number.parseFloat(strike)
      const sNum = Number.parseFloat(spotEntry)
      const shNum = shortStrike ? Number.parseFloat(shortStrike) : null
      if (!Number.isFinite(kNum) || kNum <= 0 || !Number.isFinite(sNum) || sNum <= 0) {
        throw new Error('Strike and Spot price must be positive numbers.')
      }
      await createSimulatedTrade({
        symbol: symbol.trim().toUpperCase(),
        action: 'BUY_TO_OPEN',
        option_type: optionType,
        strike: kNum,
        short_strike: strategy === 'VERTICAL_DEBIT_SPREAD' ? shNum : null,
        expiration_date: expDate,
        quantity: qtyNum,
        limit_price: limNum,
        stock_price_at_entry: sNum,
        strategy,
        order_type: 'LIMIT',
        target_stock_price: targetStock ? Number.parseFloat(targetStock) : null,
        stop_stock_price: stopStock ? Number.parseFloat(stopStock) : null,
        conviction_score: prefill?.conviction_score ?? 50,
        notes,
        dte: prefill?.dte ?? 35,
      })
      setFeedback({ kind: 'ok', text: `Paper LIMIT order filled: ${qtyNum}x ${symbol.toUpperCase()} $${kNum.toFixed(2)} ${optionType}` })
      onClearPrefill()
      await loadDiary()
    } catch (err) {
      setFeedback({ kind: 'err', text: (err as Error).message })
    } finally {
      setSubmitting(false)
    }
  }

  const startClose = (trade: DiaryTrade) => {
    setClosingId(trade.id)
    setClosePremium(trade.entry_premium.toFixed(2))
    setCloseSpot(trade.stock_price_at_entry.toFixed(2))
  }

  const handleCloseSubmit = async (tradeId: number) => {
    setSubmitting(true)
    setFeedback(null)
    try {
      await closeSimulatedTrade(tradeId, {
        exit_premium: Math.max(0, Number.parseFloat(closePremium) || 0),
        exit_stock_price: Math.max(0.01, Number.parseFloat(closeSpot) || 1),
        exit_notes: 'Closed from React Practice Desk',
      })
      setClosingId(null)
      setFeedback({ kind: 'ok', text: `Position #${tradeId} closed.` })
      await loadDiary()
    } catch (err) {
      setFeedback({ kind: 'err', text: (err as Error).message })
    } finally {
      setSubmitting(false)
    }
  }

  const sum = diary?.summary

  return (
    <div className="space-y-4">
      {/* Portfolio KPI Header */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Paper Equity</div>
          <div className="font-mono-num mt-1 text-xl font-extrabold text-white">
            ${(sum?.current_portfolio_value ?? 100000).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Realized P&amp;L</div>
          <div
            className={`font-mono-num mt-1 text-xl font-extrabold ${
              (sum?.realized_pnl_dollars ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {(sum?.realized_pnl_dollars ?? 0) >= 0 ? '+' : ''}${(sum?.realized_pnl_dollars ?? 0).toFixed(0)}
          </div>
        </div>
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Active Capital</div>
          <div className="font-mono-num mt-1 text-xl font-extrabold text-[#FF8533]">
            ${(sum?.active_capital_deployed ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Win Rate</div>
          <div className="font-mono-num mt-1 text-xl font-extrabold text-slate-100">
            {(sum?.win_rate_pct ?? 0).toFixed(0)}%{' '}
            <span className="text-xs font-medium text-slate-500">({sum?.total_closed_trades ?? 0})</span>
          </div>
        </div>
      </div>

      {feedback && (
        <div
          className={`flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-xs font-semibold ${
            feedback.kind === 'ok'
              ? 'border-emerald-500/35 bg-emerald-500/10 text-emerald-300'
              : 'border-rose-500/35 bg-rose-500/10 text-rose-300'
          }`}
        >
          {feedback.kind === 'ok' ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Order Ticket + Open Positions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <form onSubmit={handleTransmit} className="obsidian-card space-y-3 rounded-2xl p-4 lg:col-span-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold tracking-tight text-white">Practice Order Ticket</h3>
            <LearnChip topic={diary?.edu_topic} enabled={learnEnabled} label="Order Guide" />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <label className="block text-[11px] font-semibold text-slate-400">
              Symbol
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Option Type
              <select
                value={optionType}
                onChange={(e) => setOptionType(e.target.value as 'CALL' | 'PUT')}
                className="mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              >
                <option value="CALL">CALL</option>
                <option value="PUT">PUT</option>
              </select>
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Strategy
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value as 'SINGLE_LEG' | 'VERTICAL_DEBIT_SPREAD')}
                className="mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              >
                <option value="SINGLE_LEG">Single Leg</option>
                <option value="VERTICAL_DEBIT_SPREAD">Vertical Debit Spread</option>
              </select>
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Expiration
              <input
                value={expDate}
                onChange={(e) => setExpDate(e.target.value)}
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Strike ($)
              <input
                type="number"
                step="0.5"
                value={strike}
                onChange={(e) => setStrike(e.target.value)}
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            {strategy === 'VERTICAL_DEBIT_SPREAD' ? (
              <label className="block text-[11px] font-semibold text-slate-400">
                Short Wing ($)
                <input
                  type="number"
                  step="0.5"
                  value={shortStrike}
                  onChange={(e) => setShortStrike(e.target.value)}
                  className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
                />
              </label>
            ) : (
              <label className="block text-[11px] font-semibold text-slate-400">
                Spot Ref ($)
                <input
                  type="number"
                  step="0.01"
                  value={spotEntry}
                  onChange={(e) => setSpotEntry(e.target.value)}
                  className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
                />
              </label>
            )}
            <label className="block text-[11px] font-semibold text-slate-400">
              Contracts
              <input
                type="number"
                min="1"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Mid Limit ($)
              <input
                type="number"
                step="0.05"
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
          </div>

          <div className="font-mono-num flex items-center justify-between rounded-xl border border-white/[0.06] bg-[#080B11] px-3 py-2 text-xs">
            <span className="text-slate-400">Max Debit Risk</span>
            <span className="font-extrabold text-rose-400">${maxRisk.toFixed(0)}</span>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-[#FF6B00] py-2.5 text-xs font-extrabold text-white shadow-lg shadow-[#FF6B00]/20 transition hover:bg-[#FF7D1F] active:scale-95 disabled:opacity-50"
          >
            {submitting ? 'Transmitting...' : 'Transmit Practice LIMIT Order'}
          </button>
        </form>

        {/* Active & Closed Trades */}
        <div className="obsidian-card space-y-4 rounded-2xl p-4 lg:col-span-7">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold tracking-tight text-white">
              Open Practice Positions ({diary?.open_trades.length ?? 0})
            </h3>
            <button
              type="button"
              onClick={() => void loadDiary()}
              className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1 text-[11px] font-semibold text-slate-300 transition hover:text-white active:scale-95"
            >
              <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {(diary?.open_trades ?? []).length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 py-8 text-center text-xs text-slate-500">
              No open simulated trades. Stage one from the Scanner or submit the order ticket.
            </div>
          ) : (
            <div className="space-y-2.5">
              {(diary?.open_trades ?? []).map((t) => (
                <div
                  key={t.id}
                  className="rounded-xl border border-white/[0.07] bg-[#080B11]/90 p-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="font-mono-num text-sm font-extrabold text-white">{t.symbol}</span>{' '}
                      <span className="font-mono-num text-xs text-slate-300">
                        {t.quantity}x ${t.strike.toFixed(0)}
                        {t.short_strike ? `/$${t.short_strike.toFixed(0)}` : ''} {t.option_type} · Exp{' '}
                        {t.expiration_date}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono-num text-xs font-bold text-[#FF8533]">
                        Entry ${t.entry_premium.toFixed(2)}
                      </span>
                      {closingId !== t.id && (
                        <button
                          type="button"
                          onClick={() => startClose(t)}
                          className="rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] font-bold text-slate-200 transition hover:border-[#FF6B00]/50 active:scale-95"
                        >
                          Close
                        </button>
                      )}
                    </div>
                  </div>

                  {closingId === t.id && (
                    <div className="mt-2.5 flex flex-wrap items-end gap-2 border-t border-white/[0.06] pt-2.5">
                      <label className="text-[10px] text-slate-400">
                        Exit Premium
                        <input
                          type="number"
                          step="0.05"
                          value={closePremium}
                          onChange={(e) => setClosePremium(e.target.value)}
                          className="font-mono-num mt-1 block w-24 rounded border border-white/15 bg-[#06070A] px-2 py-1 text-xs text-white"
                        />
                      </label>
                      <label className="text-[10px] text-slate-400">
                        Exit Spot
                        <input
                          type="number"
                          step="0.01"
                          value={closeSpot}
                          onChange={(e) => setCloseSpot(e.target.value)}
                          className="font-mono-num mt-1 block w-24 rounded border border-white/15 bg-[#06070A] px-2 py-1 text-xs text-white"
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() => void handleCloseSubmit(t.id)}
                        disabled={submitting}
                        className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-slate-950 transition active:scale-95"
                      >
                        Confirm Close
                      </button>
                      <button
                        type="button"
                        onClick={() => setClosingId(null)}
                        className="rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-400"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {(diary?.closed_trades ?? []).length > 0 && (
            <div className="pt-2">
              <h4 className="mb-2 text-xs font-bold text-slate-400 uppercase">Recent Closed Trades</h4>
              <div className="space-y-1.5">
                {(diary?.closed_trades ?? []).slice(0, 8).map((ct) => {
                  const pnl = ct.realized_pnl_dollar ?? 0
                  return (
                    <div
                      key={ct.id}
                      className="font-mono-num flex items-center justify-between rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-2 text-xs"
                    >
                      <span className="font-bold text-slate-200">
                        {ct.symbol} ${ct.strike.toFixed(0)} {ct.option_type} ({ct.quantity}x)
                      </span>
                      <span className={`font-extrabold ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {pnl >= 0 ? '+' : ''}${pnl.toFixed(0)} ({(ct.realized_pnl_pct ?? 0).toFixed(1)}%)
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
