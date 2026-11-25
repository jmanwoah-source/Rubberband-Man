import { useCallback, useEffect, useState } from 'react'
import {
  CheckCircle2,
  DatabaseBackup,
  Download,
  Pencil,
  RefreshCw,
  Trash2,
  XCircle,
} from 'lucide-react'
import {
  closeSimulatedTrade,
  createSimulatedTrade,
  fetchDiary,
  getDiaryExportUrl,
  triggerDiaryBackup,
  updateSimulatedTrade,
  voidSimulatedTrade,
} from '../api'
import type { DiaryResponse, DiaryTrade, TradePrefill } from '../types'
import {
  computeDteFromIso,
  defaultNextMonthlyFriday,
  formatStrike,
  normalizeExpirationIso,
} from '../utils/dates'
import { LearnChip } from './LearnChip'

interface SchwabSimViewProps {
  prefill: TradePrefill | null
  learnEnabled: boolean
  onClearPrefill: () => void
}

function getEntryPremium(trade: DiaryTrade): number {
  const raw = Number(trade.limit_price ?? trade.entry_premium ?? 0)
  return Number.isFinite(raw) ? raw : 0
}

export function SchwabSimView({ prefill, learnEnabled, onClearPrefill }: SchwabSimViewProps) {
  const [diary, setDiary] = useState<DiaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [backingUp, setBackingUp] = useState(false)
  const [feedback, setFeedback] = useState<{ kind: 'ok' | 'err'; text: string } | null>(null)

  // Order Ticket State (Zero-Information-Loss)
  const [prevPrefill, setPrevPrefill] = useState<TradePrefill | null>(prefill)
  const [symbol, setSymbol] = useState(prefill?.symbol ?? 'NVDA')
  const [action, setAction] = useState<'BUY_TO_OPEN' | 'SELL_TO_OPEN'>(
    prefill?.action ?? 'BUY_TO_OPEN',
  )
  const [optionType, setOptionType] = useState<'CALL' | 'PUT'>(prefill?.option_type ?? 'CALL')
  const [strategy, setStrategy] = useState<'SINGLE_LEG' | 'VERTICAL_DEBIT_SPREAD'>(
    prefill?.strategy ?? 'SINGLE_LEG',
  )
  const [orderType, setOrderType] = useState<'LIMIT' | 'MARKET'>('LIMIT')
  const [timeInForce, setTimeInForce] = useState<'DAY' | 'GTC'>('DAY')
  const [strike, setStrike] = useState(String(prefill?.strike ?? 140))
  const [shortStrike, setShortStrike] = useState(
    prefill?.short_strike != null ? String(prefill.short_strike) : '',
  )
  const [expDate, setExpDate] = useState(() =>
    prefill?.expiration_date
      ? normalizeExpirationIso(prefill.expiration_date, prefill.dte)
      : defaultNextMonthlyFriday(),
  )
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

  // Sync incoming prefill during render (avoids set-state-in-effect)
  if (prefill !== prevPrefill) {
    setPrevPrefill(prefill)
    if (prefill) {
      setSymbol(prefill.symbol)
      setAction(prefill.action ?? 'BUY_TO_OPEN')
      setOptionType(prefill.option_type)
      setStrategy(prefill.strategy)
      setStrike(prefill.strike.toFixed(2))
      setShortStrike(prefill.short_strike != null ? prefill.short_strike.toFixed(2) : '')
      setExpDate(normalizeExpirationIso(prefill.expiration_date, prefill.dte))
      setLimitPrice(prefill.limit_price.toFixed(2))
      setSpotEntry(prefill.stock_price_at_entry.toFixed(2))
      setTargetStock(prefill.target_stock_price != null ? prefill.target_stock_price.toFixed(2) : '')
      setStopStock(prefill.stop_stock_price != null ? prefill.stop_stock_price.toFixed(2) : '')
      setNotes(prefill.notes)
    }
  }

  // Inline Close state
  const [closingId, setClosingId] = useState<number | null>(null)
  const [closePremium, setClosePremium] = useState('')
  const [closeSpot, setCloseSpot] = useState('')
  const [closeNotes, setCloseNotes] = useState('')

  // Inline Edit state (PATCH target/stop/TIF/notes)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editTarget, setEditTarget] = useState('')
  const [editStop, setEditStop] = useState('')
  const [editTif, setEditTif] = useState<'DAY' | 'GTC'>('DAY')
  const [editNotes, setEditNotes] = useState('')

  // Inline Void confirmation state (DELETE soft-void)
  const [voidingId, setVoidingId] = useState<number | null>(null)

  const refreshDiary = useCallback(async (signal?: AbortSignal) => {
    try {
      const res = await fetchDiary(signal)
      if (!signal?.aborted) {
        setDiary(res)
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setFeedback({ kind: 'err', text: (err as Error).message })
      }
    } finally {
      if (!signal?.aborted) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    const ac = new AbortController()
    fetchDiary(ac.signal)
      .then((res) => {
        if (!ac.signal.aborted) {
          setDiary(res)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (!ac.signal.aborted && (err as Error).name !== 'AbortError') {
          setFeedback({ kind: 'err', text: (err as Error).message })
          setLoading(false)
        }
      })
    return () => ac.abort()
  }, [])

  const handleManualRefresh = () => {
    setLoading(true)
    void refreshDiary()
  }

  const parsedQty = Number.parseInt(quantity, 10)
  const qtyNum = Number.isFinite(parsedQty) ? Math.min(500, Math.max(1, parsedQty)) : 1
  const limNum = Math.max(0.01, Number.parseFloat(limitPrice) || 0)
  const strikeNum = Number.parseFloat(strike) || 0
  const shortStrikeNum = Number.parseFloat(shortStrike) || 0
  const legsCount = strategy === 'VERTICAL_DEBIT_SPREAD' ? 2 : 1
  const schwabCommission = Number((qtyNum * 0.65 * legsCount).toFixed(2))
  const grossNotional = qtyNum * limNum * 100
  const isSellAction = action === 'SELL_TO_OPEN'
  const netCashEstimate = isSellAction
    ? Math.max(0, grossNotional - schwabCommission)
    : grossNotional + schwabCommission
  const spreadWidthRisk =
    isSellAction && strategy === 'VERTICAL_DEBIT_SPREAD' && shortStrikeNum > 0 && strikeNum > 0
      ? Math.max(0, Math.abs(shortStrikeNum - strikeNum) * 100 * qtyNum - netCashEstimate)
      : null
  const computedDte = computeDteFromIso(expDate, prefill?.dte ?? 35)

  const handleTransmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setFeedback(null)
    try {
      const cleanSym = symbol.trim().toUpperCase().replace(/[^A-Z0-9.^-]/g, '').slice(0, 12)
      const kNum = Number.parseFloat(strike)
      const sNum = Number.parseFloat(spotEntry)
      const lNum = Number.parseFloat(limitPrice)
      const qVal = Number.parseInt(quantity, 10)
      const shNum = shortStrike.trim() ? Number.parseFloat(shortStrike) : null
      const tgtNum = targetStock.trim() ? Number.parseFloat(targetStock) : null
      const stpNum = stopStock.trim() ? Number.parseFloat(stopStock) : null

      if (!cleanSym) {
        throw new Error('Symbol is required.')
      }
      if (!Number.isFinite(qVal) || qVal < 1 || qVal > 500) {
        throw new Error('Contracts must be an integer between 1 and 500.')
      }
      if (!Number.isFinite(kNum) || kNum <= 0 || !Number.isFinite(sNum) || sNum <= 0) {
        throw new Error('Strike and Spot Ref must be positive numbers.')
      }
      if (!Number.isFinite(lNum) || lNum <= 0) {
        throw new Error('Mid Limit price must be greater than 0.')
      }
      if (strategy === 'VERTICAL_DEBIT_SPREAD') {
        if (shNum == null || !Number.isFinite(shNum) || shNum <= 0) {
          throw new Error('Short Wing strike is required for a Vertical Debit Spread.')
        }
        if (Math.abs(shNum - kNum) < 0.01) {
          throw new Error('Short Wing strike must differ from the primary Strike.')
        }
      }
      if (tgtNum != null && (!Number.isFinite(tgtNum) || tgtNum <= 0)) {
        throw new Error('Target Stock must be a positive number.')
      }
      if (stpNum != null && (!Number.isFinite(stpNum) || stpNum <= 0)) {
        throw new Error('Stop Stock must be a positive number.')
      }

      const normExp = normalizeExpirationIso(expDate, prefill?.dte ?? 35)
      const liveDte = computeDteFromIso(normExp, prefill?.dte ?? 35)
      const prefillMatches = prefill && prefill.symbol.toUpperCase() === cleanSym

      const res = await createSimulatedTrade({
        symbol: cleanSym,
        action,
        option_type: optionType,
        strike: kNum,
        short_strike: strategy === 'VERTICAL_DEBIT_SPREAD' ? shNum : null,
        expiration_date: normExp,
        quantity: qVal,
        limit_price: lNum,
        stock_price_at_entry: sNum,
        strategy,
        order_type: orderType,
        time_in_force: timeInForce,
        target_stock_price: tgtNum,
        stop_stock_price: stpNum,
        implied_vol_at_entry: prefillMatches ? (prefill.implied_vol_at_entry ?? null) : null,
        conviction_score: prefillMatches ? prefill.conviction_score : 50,
        expected_basis_pct: prefillMatches ? (prefill.expected_basis_pct ?? 0) : 0,
        whale_badge: prefillMatches ? (prefill.whale_badge ?? 'TWO-WAY FLOW') : 'TWO-WAY FLOW',
        catalyst_tag: prefillMatches ? (prefill.catalyst_tag ?? '') : '',
        notes: notes.trim(),
        dte: liveDte,
      })

      const orderId = res.trade?.schwab_order_id
      const wingText =
        strategy === 'VERTICAL_DEBIT_SPREAD' && shNum != null ? `/${formatStrike(shNum)}` : ''
      setFeedback({
        kind: 'ok',
        text: `Filled ${orderId ? `[${orderId}] ` : ''}${action.replace(/_/g, ' ')} ${qVal}x ${cleanSym} ${formatStrike(kNum)}${wingText} ${optionType} (${orderType} · ${timeInForce} · ${liveDte}D)`,
      })
      onClearPrefill()
      await refreshDiary()
    } catch (err) {
      setFeedback({ kind: 'err', text: (err as Error).message })
    } finally {
      setSubmitting(false)
    }
  }

  const startClose = (trade: DiaryTrade) => {
    setEditingId(null)
    setVoidingId(null)
    setClosingId(trade.id)
    const defExitPrem = Number(trade.est_current_premium ?? getEntryPremium(trade))
    const defExitSpot = Number(trade.live_stock_price ?? trade.stock_price_at_entry ?? 0)
    setClosePremium(Number.isFinite(defExitPrem) ? defExitPrem.toFixed(2) : '0.00')
    setCloseSpot(Number.isFinite(defExitSpot) ? defExitSpot.toFixed(2) : '1.00')
    setCloseNotes('')
  }

  const handleCloseSubmit = async (tradeId: number) => {
    setSubmitting(true)
    setFeedback(null)
    try {
      const exPrem = Number.parseFloat(closePremium)
      const exSpot = Number.parseFloat(closeSpot)
      if (!Number.isFinite(exPrem) || exPrem < 0) {
        throw new Error('Exit Premium must be 0 or greater.')
      }
      if (!Number.isFinite(exSpot) || exSpot <= 0) {
        throw new Error('Exit Spot must be greater than 0.')
      }
      await closeSimulatedTrade(tradeId, {
        exit_premium: exPrem,
        exit_stock_price: exSpot,
        exit_notes: closeNotes.trim() || 'Closed from Practice Desk',
      })
      setClosingId(null)
      setCloseNotes('')
      setFeedback({ kind: 'ok', text: `Position #${tradeId} closed and logged.` })
      await refreshDiary()
    } catch (err) {
      setFeedback({ kind: 'err', text: (err as Error).message })
    } finally {
      setSubmitting(false)
    }
  }

  const startEdit = (trade: DiaryTrade) => {
    setClosingId(null)
    setVoidingId(null)
    setEditingId(trade.id)
    setEditTarget(trade.target_stock_price != null ? Number(trade.target_stock_price).toFixed(2) : '')
    setEditStop(trade.stop_stock_price != null ? Number(trade.stop_stock_price).toFixed(2) : '')
    setEditTif(String(trade.time_in_force ?? 'DAY').toUpperCase() === 'GTC' ? 'GTC' : 'DAY')
    setEditNotes(trade.notes ?? '')
  }

  const handleEditSubmit = async (tradeId: number) => {
    setSubmitting(true)
    setFeedback(null)
    try {
      const tgt = editTarget.trim() ? Number.parseFloat(editTarget) : null
      const stp = editStop.trim() ? Number.parseFloat(editStop) : null
      if (tgt != null && (!Number.isFinite(tgt) || tgt <= 0)) {
        throw new Error('Target Stock must be a positive number.')
      }
      if (stp != null && (!Number.isFinite(stp) || stp <= 0)) {
        throw new Error('Stop Stock must be a positive number.')
      }
      await updateSimulatedTrade(tradeId, {
        target_stock_price: tgt,
        stop_stock_price: stp,
        time_in_force: editTif,
        notes: editNotes.trim(),
      })
      setEditingId(null)
      setFeedback({ kind: 'ok', text: `Position #${tradeId} updated.` })
      await refreshDiary()
    } catch (err) {
      setFeedback({ kind: 'err', text: (err as Error).message })
    } finally {
      setSubmitting(false)
    }
  }

  const handleVoidConfirm = async (tradeId: number) => {
    setSubmitting(true)
    setFeedback(null)
    try {
      await voidSimulatedTrade(tradeId)
      setVoidingId(null)
      setFeedback({ kind: 'ok', text: `Position #${tradeId} voided (soft-deleted).` })
      await refreshDiary()
    } catch (err) {
      setFeedback({ kind: 'err', text: (err as Error).message })
    } finally {
      setSubmitting(false)
    }
  }

  const handleBackupDb = async () => {
    setBackingUp(true)
    setFeedback(null)
    try {
      const res = await triggerDiaryBackup()
      setFeedback({
        kind: 'ok',
        text: res.backup_path
          ? `SQLite backup created & WAL checkpointed (${res.backup_path}).`
          : 'SQLite backup & WAL checkpoint complete.',
      })
    } catch (err) {
      setFeedback({ kind: 'err', text: (err as Error).message })
    } finally {
      setBackingUp(false)
    }
  }

  const sum = diary?.summary
  const unrealizedTotal = sum?.unrealized_pnl_dollars ?? 0
  const realizedTotal = sum?.realized_pnl_dollars ?? 0

  return (
    <div className="space-y-4">
      {/* Portfolio KPI Header + Data Durability Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-extrabold tracking-tight text-white">
            Charles Schwab Practice Desk &amp; Diary
          </h2>
          <p className="text-xs text-slate-400">
            Zero-loss SQLite paper ledger with live Black-Scholes mark-to-market and $0.65/leg fee accounting.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <a
            href={getDiaryExportUrl('json')}
            download
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-[#0C1018] px-3 py-1.5 text-[11px] font-bold text-slate-200 transition hover:border-white/25 hover:text-white active:scale-95"
          >
            <Download className="h-3.5 w-3.5 text-sky-400" />
            Export JSON
          </a>
          <a
            href={getDiaryExportUrl('csv')}
            download
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-[#0C1018] px-3 py-1.5 text-[11px] font-bold text-slate-200 transition hover:border-white/25 hover:text-white active:scale-95"
          >
            <Download className="h-3.5 w-3.5 text-emerald-400" />
            Export CSV
          </a>
          <button
            type="button"
            onClick={() => void handleBackupDb()}
            disabled={backingUp}
            className="inline-flex items-center gap-1.5 rounded-xl border border-[#FF6B00]/35 bg-[#FF6B00]/12 px-3 py-1.5 text-[11px] font-bold text-[#FF8533] transition hover:bg-[#FF6B00]/20 active:scale-95 disabled:opacity-50"
          >
            <DatabaseBackup className={`h-3.5 w-3.5 ${backingUp ? 'animate-pulse' : ''}`} />
            {backingUp ? 'Backing up...' : 'Backup DB'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Paper Equity</div>
          <div className="font-mono-num mt-1 text-lg font-extrabold text-white sm:text-xl">
            ${(sum?.current_portfolio_value ?? 100000).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Unrealized P&amp;L</div>
          <div
            className={`font-mono-num mt-1 text-lg font-extrabold sm:text-xl ${
              unrealizedTotal >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {unrealizedTotal >= 0 ? '+' : '-'}${Math.abs(unrealizedTotal).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Realized P&amp;L</div>
          <div
            className={`font-mono-num mt-1 text-lg font-extrabold sm:text-xl ${
              realizedTotal >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {realizedTotal >= 0 ? '+' : '-'}${Math.abs(realizedTotal).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Active Capital</div>
          <div className="font-mono-num mt-1 text-lg font-extrabold text-[#FF8533] sm:text-xl">
            ${(sum?.active_capital_deployed ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </div>
        </div>
        <div className="obsidian-card col-span-2 rounded-2xl p-3.5 sm:col-span-1">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Win Rate</div>
          <div className="font-mono-num mt-1 text-lg font-extrabold text-slate-100 sm:text-xl">
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
          {feedback.kind === 'ok' ? (
            <CheckCircle2 className="h-4 w-4 shrink-0" />
          ) : (
            <XCircle className="h-4 w-4 shrink-0" />
          )}
          <span>{feedback.text}</span>
        </div>
      )}

      {/* Order Ticket + Open & Closed Positions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        <form onSubmit={handleTransmit} className="obsidian-card space-y-3 rounded-2xl p-4 lg:col-span-5">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold tracking-tight text-white">Practice Order Ticket</h3>
            <LearnChip topic={diary?.edu_topic} enabled={learnEnabled} label="Order Guide" />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <label className="block text-[11px] font-semibold text-slate-400">
              Symbol
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                maxLength={12}
                required
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Action
              <select
                value={action}
                onChange={(e) => setAction(e.target.value as 'BUY_TO_OPEN' | 'SELL_TO_OPEN')}
                className="mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              >
                <option value="BUY_TO_OPEN">BUY TO OPEN</option>
                <option value="SELL_TO_OPEN">SELL TO OPEN</option>
              </select>
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
              Order Type
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as 'LIMIT' | 'MARKET')}
                className="mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              >
                <option value="LIMIT">LIMIT</option>
                <option value="MARKET">MARKET</option>
              </select>
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Time in Force (TIF)
              <select
                value={timeInForce}
                onChange={(e) => setTimeInForce(e.target.value as 'DAY' | 'GTC')}
                className="mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              >
                <option value="DAY">DAY</option>
                <option value="GTC">GTC</option>
              </select>
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Expiration ({computedDte}D)
              <input
                type="date"
                value={expDate}
                onChange={(e) => setExpDate(e.target.value)}
                required
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Spot Ref ($)
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={spotEntry}
                onChange={(e) => setSpotEntry(e.target.value)}
                required
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Strike ($)
              <input
                type="number"
                step="0.5"
                min="0.5"
                value={strike}
                onChange={(e) => setStrike(e.target.value)}
                required
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            {strategy === 'VERTICAL_DEBIT_SPREAD' ? (
              <label className="block text-[11px] font-semibold text-slate-400">
                Short Wing ($)
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  value={shortStrike}
                  onChange={(e) => setShortStrike(e.target.value)}
                  required
                  placeholder="OTM wing strike"
                  className="font-mono-num mt-1 w-full rounded-lg border border-[#FF6B00]/35 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/70"
                />
              </label>
            ) : (
              <div className="flex flex-col justify-end pb-1">
                <div className="rounded-lg border border-white/[0.05] bg-white/[0.02] px-2.5 py-2 text-[11px] text-slate-400">
                  Single-Leg Convexity
                </div>
              </div>
            )}
            <label className="block text-[11px] font-semibold text-slate-400">
              Contracts (1–500)
              <input
                type="number"
                min={1}
                max={500}
                step={1}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                required
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Mid Limit ($)
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={limitPrice}
                onChange={(e) => setLimitPrice(e.target.value)}
                required
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-white outline-none focus:border-[#FF6B00]/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Target Stock ($)
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={targetStock}
                onChange={(e) => setTargetStock(e.target.value)}
                placeholder="Optional"
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-emerald-300 placeholder:text-slate-600 outline-none focus:border-emerald-400/60"
              />
            </label>
            <label className="block text-[11px] font-semibold text-slate-400">
              Stop Stock ($)
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={stopStock}
                onChange={(e) => setStopStock(e.target.value)}
                placeholder="Optional"
                className="font-mono-num mt-1 w-full rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs font-bold text-rose-300 placeholder:text-slate-600 outline-none focus:border-rose-400/60"
              />
            </label>
          </div>

          <label className="block text-[11px] font-semibold text-slate-400">
            Thesis &amp; Execution Notes
            <textarea
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Catalyst thesis, entry reason, invalidation rules..."
              className="mt-1 w-full resize-y rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-2 text-xs leading-relaxed text-slate-200 placeholder:text-slate-600 outline-none focus:border-[#FF6B00]/60"
            />
          </label>

          <div className="font-mono-num space-y-1 rounded-xl border border-white/[0.06] bg-[#080B11] px-3 py-2.5 text-xs">
            <div className="flex items-center justify-between text-[11px] text-slate-400">
              <span>Schwab Fee ($0.65/leg/ct × {legsCount} leg{legsCount > 1 ? 's' : ''})</span>
              <span className="text-slate-200">${schwabCommission.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-300">
                {isSellAction ? 'Est. Net Credit' : 'Max Debit Risk'}
              </span>
              <span className={`font-extrabold ${isSellAction ? 'text-emerald-400' : 'text-rose-400'}`}>
                {isSellAction ? '+' : ''}${netCashEstimate.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            {spreadWidthRisk != null && (
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Spread Max Risk</span>
                <span className="font-bold text-rose-400">
                  ${spreadWidthRisk.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-[#FF6B00] py-2.5 text-xs font-extrabold text-white shadow-lg shadow-[#FF6B00]/20 transition hover:bg-[#FF7D1F] active:scale-95 disabled:opacity-50"
          >
            {submitting
              ? 'Transmitting...'
              : `Transmit Practice ${orderType} Order (${timeInForce})`}
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
              onClick={handleManualRefresh}
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
            <div className="space-y-3">
              {(diary?.open_trades ?? []).map((t) => {
                const entryPx = getEntryPremium(t)
                const markPx =
                  t.est_current_premium != null && Number.isFinite(Number(t.est_current_premium))
                    ? Number(t.est_current_premium)
                    : null
                const unrDollar = Number(t.unrealized_pnl_dollar ?? 0)
                const unrPct = Number(t.unrealized_pnl_pct ?? 0)
                const isSell = String(t.action ?? '').toUpperCase().includes('SELL')
                const isSpread = String(t.strategy ?? '').toUpperCase() === 'VERTICAL_DEBIT_SPREAD'
                const tifLabel = String(t.time_in_force ?? 'DAY').toUpperCase()

                return (
                  <div
                    key={t.id}
                    className="rounded-xl border border-white/[0.07] bg-[#080B11]/90 p-3.5"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="font-mono-num text-sm font-extrabold text-white">
                            {t.symbol}
                          </span>
                          <span className="font-mono-num text-xs font-semibold text-slate-200">
                            {t.quantity}x {formatStrike(t.strike)}
                            {t.short_strike ? `/${formatStrike(t.short_strike)}` : ''} {t.option_type}
                          </span>
                          <span className="font-mono-num text-[11px] text-slate-400">
                            · Exp {t.expiration_date}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-1.5 text-[10px]">
                          {t.schwab_order_id && (
                            <span className="font-mono-num rounded border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-slate-400">
                              {t.schwab_order_id}
                            </span>
                          )}
                          <span
                            className={`rounded px-1.5 py-0.5 font-bold ${
                              isSell
                                ? 'bg-amber-500/15 text-amber-300'
                                : 'bg-sky-500/15 text-sky-300'
                            }`}
                          >
                            {isSell ? 'SELL' : 'BUY'}
                          </span>
                          <span className="rounded bg-white/[0.05] px-1.5 py-0.5 font-semibold text-slate-300">
                            {isSpread ? 'SPREAD' : 'SINGLE'}
                          </span>
                          <span className="font-mono-num rounded bg-white/[0.05] px-1.5 py-0.5 font-semibold text-slate-400">
                            {tifLabel}
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-mono-num text-right">
                          <div className="text-xs font-bold text-[#FF8533]">
                            Entry ${entryPx.toFixed(2)}
                            {markPx != null && (
                              <span className="text-slate-400"> → ${markPx.toFixed(2)}</span>
                            )}
                          </div>
                          <div
                            className={`text-xs font-extrabold ${
                              unrDollar >= 0 ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {unrDollar >= 0 ? '+' : '-'}${Math.abs(unrDollar).toFixed(2)} (
                            {unrPct >= 0 ? '+' : ''}
                            {unrPct.toFixed(1)}%)
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => startEdit(t)}
                            title="Edit target, stop, TIF, or notes"
                            className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.04] px-2 py-1 text-[11px] font-bold text-slate-300 transition hover:border-sky-400/50 hover:text-white active:scale-95"
                          >
                            <Pencil className="h-3 w-3" />
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => startClose(t)}
                            className="rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] font-bold text-slate-200 transition hover:border-[#FF6B00]/50 active:scale-95"
                          >
                            Close
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setClosingId(null)
                              setEditingId(null)
                              setVoidingId(voidingId === t.id ? null : t.id)
                            }}
                            title="Void simulated trade"
                            className="inline-flex items-center rounded-lg border border-rose-500/25 bg-rose-500/10 p-1.5 text-rose-300 transition hover:border-rose-400/60 active:scale-95"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Levels & Notes Metadata Row */}
                    <div className="font-mono-num mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/[0.05] pt-2 text-[11px] text-slate-400">
                      <span>
                        Spot:{' '}
                        <strong className="text-slate-200">
                          ${Number(t.live_stock_price ?? t.stock_price_at_entry ?? 0).toFixed(2)}
                        </strong>
                      </span>
                      {t.target_stock_price != null && (
                        <span>
                          Target:{' '}
                          <strong className="text-emerald-400">
                            ${Number(t.target_stock_price).toFixed(2)}
                          </strong>
                        </span>
                      )}
                      {t.stop_stock_price != null && (
                        <span>
                          Stop:{' '}
                          <strong className="text-rose-400">
                            ${Number(t.stop_stock_price).toFixed(2)}
                          </strong>
                        </span>
                      )}
                    </div>
                    {t.notes && (
                      <p className="mt-1.5 text-[11px] leading-relaxed text-slate-400">{t.notes}</p>
                    )}

                    {/* Inline Edit Panel */}
                    {editingId === t.id && (
                      <div className="mt-2.5 space-y-2 border-t border-white/[0.07] pt-2.5">
                        <div className="grid grid-cols-3 gap-2">
                          <label className="text-[10px] font-semibold text-slate-400">
                            Target Stock ($)
                            <input
                              type="number"
                              step="0.01"
                              value={editTarget}
                              onChange={(e) => setEditTarget(e.target.value)}
                              className="font-mono-num mt-1 block w-full rounded border border-white/15 bg-[#06070A] px-2 py-1 text-xs text-white"
                            />
                          </label>
                          <label className="text-[10px] font-semibold text-slate-400">
                            Stop Stock ($)
                            <input
                              type="number"
                              step="0.01"
                              value={editStop}
                              onChange={(e) => setEditStop(e.target.value)}
                              className="font-mono-num mt-1 block w-full rounded border border-white/15 bg-[#06070A] px-2 py-1 text-xs text-white"
                            />
                          </label>
                          <label className="text-[10px] font-semibold text-slate-400">
                            TIF
                            <select
                              value={editTif}
                              onChange={(e) => setEditTif(e.target.value as 'DAY' | 'GTC')}
                              className="mt-1 block w-full rounded border border-white/15 bg-[#06070A] px-2 py-1 text-xs text-white"
                            >
                              <option value="DAY">DAY</option>
                              <option value="GTC">GTC</option>
                            </select>
                          </label>
                        </div>
                        <label className="block text-[10px] font-semibold text-slate-400">
                          Notes
                          <textarea
                            rows={2}
                            value={editNotes}
                            onChange={(e) => setEditNotes(e.target.value)}
                            className="mt-1 block w-full rounded border border-white/15 bg-[#06070A] px-2 py-1 text-xs text-slate-200"
                          />
                        </label>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => void handleEditSubmit(t.id)}
                            disabled={submitting}
                            className="rounded-lg bg-sky-500 px-3 py-1.5 text-xs font-bold text-slate-950 transition active:scale-95 disabled:opacity-50"
                          >
                            Save Changes
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-slate-400"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Inline Close Panel (with Editable Exit Notes) */}
                    {closingId === t.id && (
                      <div className="mt-2.5 space-y-2 border-t border-white/[0.07] pt-2.5">
                        <div className="flex flex-wrap items-end gap-2">
                          <label className="text-[10px] font-semibold text-slate-400">
                            Exit Premium ($)
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              value={closePremium}
                              onChange={(e) => setClosePremium(e.target.value)}
                              className="font-mono-num mt-1 block w-28 rounded border border-white/15 bg-[#06070A] px-2 py-1 text-xs text-white"
                            />
                          </label>
                          <label className="text-[10px] font-semibold text-slate-400">
                            Exit Spot ($)
                            <input
                              type="number"
                              step="0.01"
                              min="0.01"
                              value={closeSpot}
                              onChange={(e) => setCloseSpot(e.target.value)}
                              className="font-mono-num mt-1 block w-28 rounded border border-white/15 bg-[#06070A] px-2 py-1 text-xs text-white"
                            />
                          </label>
                        </div>
                        <label className="block text-[10px] font-semibold text-slate-400">
                          Exit Notes
                          <input
                            type="text"
                            value={closeNotes}
                            onChange={(e) => setCloseNotes(e.target.value)}
                            placeholder="Profit target hit, stop triggered, IV crush, thesis review..."
                            className="mt-1 block w-full rounded border border-white/15 bg-[#06070A] px-2.5 py-1.5 text-xs text-slate-200 placeholder:text-slate-600"
                          />
                        </label>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => void handleCloseSubmit(t.id)}
                            disabled={submitting}
                            className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-slate-950 transition active:scale-95 disabled:opacity-50"
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
                      </div>
                    )}

                    {/* Inline Confirmed Void Panel */}
                    {voidingId === t.id && (
                      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-rose-500/35 bg-rose-500/10 px-3 py-2">
                        <span className="text-xs font-semibold text-rose-200">
                          Void {t.symbol} {formatStrike(t.strike)} {t.option_type}? Record stays archived as VOIDED.
                        </span>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => void handleVoidConfirm(t.id)}
                            disabled={submitting}
                            className="rounded-lg bg-rose-500 px-3 py-1 text-xs font-bold text-white transition active:scale-95 disabled:opacity-50"
                          >
                            Confirm Void
                          </button>
                          <button
                            type="button"
                            onClick={() => setVoidingId(null)}
                            className="rounded-lg border border-white/15 px-2.5 py-1 text-xs text-slate-300"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {(diary?.closed_trades ?? []).length > 0 && (
            <div className="pt-2">
              <div className="mb-2 flex items-center justify-between">
                <h4 className="text-xs font-bold tracking-wider text-slate-400 uppercase">
                  Closed Trade History ({diary?.closed_trades.length ?? 0})
                </h4>
              </div>
              <div className="max-h-[420px] space-y-1.5 overflow-y-auto pr-0.5">
                {(diary?.closed_trades ?? []).map((ct) => {
                  const pnl = Number(ct.realized_pnl_dollar ?? 0)
                  const pnlPct = Number(ct.realized_pnl_pct ?? 0)
                  const entryPx = getEntryPremium(ct)
                  const exitPx = Number(ct.exit_premium ?? 0)
                  const entryDate = String(ct.entry_timestamp ?? ct.created_at ?? '').slice(0, 10)
                  const exitDate = String(ct.exit_timestamp ?? '').slice(0, 10)
                  return (
                    <div
                      key={ct.id}
                      className="font-mono-num flex flex-wrap items-center justify-between gap-2 rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-2 text-xs"
                    >
                      <div className="space-y-0.5">
                        <div className="font-bold text-slate-200">
                          {ct.symbol} {formatStrike(ct.strike)}
                          {ct.short_strike ? `/${formatStrike(ct.short_strike)}` : ''} {ct.option_type} ({ct.quantity}x)
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {ct.schwab_order_id ? `${ct.schwab_order_id} · ` : ''}
                          ${entryPx.toFixed(2)} → ${exitPx.toFixed(2)}
                          {entryDate ? ` · ${entryDate}` : ''}
                          {exitDate ? ` → ${exitDate}` : ''}
                        </div>
                      </div>
                      <span className={`font-extrabold ${pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {pnl >= 0 ? '+' : '-'}${Math.abs(pnl).toFixed(2)} ({pnlPct >= 0 ? '+' : ''}
                        {pnlPct.toFixed(1)}%)
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
