import { useEffect, useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { fetchLedger } from '../api'
import type { LedgerResponse, LedgerSnapshotRow, TradePrefill } from '../types'
import { computeDteFromIso, defaultNextMonthlyFriday, formatStrike } from '../utils/dates'
import { LearnChip } from './LearnChip'

interface LedgerViewProps {
  learnEnabled: boolean
  onSimulate: (prefill: TradePrefill) => void
}

export function LedgerView({ learnEnabled, onSimulate }: LedgerViewProps) {
  const [ledger, setLedger] = useState<LedgerResponse | null>(null)
  const [selectedDate, setSelectedDate] = useState('')
  const [selectedSector, setSelectedSector] = useState('All Sectors')
  const [settledKey, setSettledKey] = useState('')
  const [errState, setErrState] = useState<{ key: string; msg: string } | null>(null)

  const requestKey = `${selectedDate}|${selectedSector}`
  const loading = settledKey !== requestKey
  const errMsg = errState?.key === requestKey ? errState.msg : null

  useEffect(() => {
    const ac = new AbortController()
    fetchLedger(selectedDate, selectedSector, ac.signal)
      .then((res) => {
        if (ac.signal.aborted) return
        setLedger(res)
        setErrState(null)
        setSettledKey(requestKey)
      })
      .catch((err) => {
        if (ac.signal.aborted || (err as Error).name === 'AbortError') return
        setErrState({ key: requestKey, msg: (err as Error).message })
        setSettledKey(requestKey)
      })
    return () => ac.abort()
  }, [selectedDate, selectedSector, requestKey])

  const stageRow = (r: LedgerSnapshotRow) => {
    const isPut = r.action.toUpperCase().includes('PUT')
    const defaultExp = defaultNextMonthlyFriday()
    onSimulate({
      symbol: r.symbol,
      action: 'BUY_TO_OPEN',
      option_type: isPut ? 'PUT' : 'CALL',
      strategy: 'SINGLE_LEG',
      strike:
        r.recommended_strike && r.recommended_strike > 0 ? r.recommended_strike : r.current_price,
      expiration_date: defaultExp,
      dte: computeDteFromIso(defaultExp, 35),
      limit_price: Math.max(1.0, Number((r.current_price * 0.032).toFixed(2))),
      stock_price_at_entry: r.current_price,
      target_stock_price: r.target_price ?? null,
      stop_stock_price: r.invalidation_price ?? null,
      conviction_score: r.composite_score ?? 50,
      expected_basis_pct: r.expected_basis_pct ?? 0,
      whale_badge: r.whale_badge ?? 'TWO-WAY FLOW',
      notes: `Daily Top-5 Ledger (${ledger?.selected_date ?? ''} #${r.rank})`,
    })
  }

  return (
    <div className="space-y-4">
      <div className="obsidian-card flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4">
        <div>
          <h2 className="text-base font-bold tracking-tight text-white">
            Daily Top-5 Empirical Recommendation Ledger
          </h2>
          <p className="text-xs text-slate-400">
            Out-of-sample snapshots captured by the daemon and marked against live equity movement.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Snapshot Date"
            value={selectedDate || (ledger?.selected_date ?? '')}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="font-mono-num rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-1.5 text-xs text-slate-200"
          >
            {(ledger?.dates ?? []).map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>

          <select
            aria-label="Ledger Sector"
            value={selectedSector}
            onChange={(e) => setSelectedSector(e.target.value)}
            className="rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-1.5 text-xs text-slate-200"
          >
            {(ledger?.sectors ?? ['All Sectors']).map((sec) => (
              <option key={sec} value={sec}>
                {sec}
              </option>
            ))}
          </select>

          <LearnChip topic={ledger?.edu_topic} enabled={learnEnabled} label="Audit Guide" />
        </div>
      </div>

      {/* Stats Strip */}
      <div className="grid grid-cols-3 gap-3">
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Audited Picks</div>
          <div className="font-mono-num mt-1 text-xl font-extrabold text-white">
            {ledger?.stats.count ?? 0}
          </div>
        </div>
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Win Rate</div>
          <div
            className={`font-mono-num mt-1 text-xl font-extrabold ${
              (ledger?.stats.win_rate_pct ?? 0) >= 50 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {(ledger?.stats.win_rate_pct ?? 0).toFixed(1)}%
          </div>
        </div>
        <div className="obsidian-card rounded-2xl p-3.5">
          <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Avg Dir Return</div>
          <div
            className={`font-mono-num mt-1 text-xl font-extrabold ${
              (ledger?.stats.avg_dir_pct ?? 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {(ledger?.stats.avg_dir_pct ?? 0) >= 0 ? '+' : ''}
            {(ledger?.stats.avg_dir_pct ?? 0).toFixed(2)}%
          </div>
        </div>
      </div>

      {errMsg && (
        <div className="rounded-xl border border-rose-500/35 bg-rose-500/10 px-4 py-3 text-xs text-rose-300">
          {errMsg}
        </div>
      )}

      <div className="obsidian-card divide-y divide-white/[0.05] rounded-2xl p-2">
        {loading ? (
          <div className="p-6 text-center text-xs text-slate-500">Loading ledger snapshots...</div>
        ) : (ledger?.snapshots ?? []).length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No snapshot records recorded yet for this filter.
          </div>
        ) : (
          (ledger?.snapshots ?? []).map((row, idx) => {
            const actUpper = String(row.action ?? '').toUpperCase()
            const isCall = actUpper.includes('CALL')
            const isPut = actUpper.includes('PUT')
            const isNeutral = !isCall && !isPut
            return (
              <div
                key={`${row.symbol}-${row.rank}-${idx}`}
                className="flex flex-wrap items-center justify-between gap-3 px-3 py-3"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono-num text-xs font-bold text-[#FF8533]">#{row.rank}</span>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono-num text-sm font-extrabold text-white">{row.symbol}</span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          isCall
                            ? 'bg-emerald-500/15 text-emerald-400'
                            : isPut
                              ? 'bg-rose-500/15 text-rose-400'
                              : 'bg-white/[0.07] text-slate-300'
                        }`}
                      >
                        {row.action}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        {row.normalized_sector ?? row.sector}
                      </span>
                    </div>
                    <div className="font-mono-num mt-0.5 text-[11px] text-slate-400">
                      Snap ${row.price_at_snapshot.toFixed(2)} → Live ${row.current_price.toFixed(2)} · Strike{' '}
                      {formatStrike(row.recommended_strike ?? row.current_price)}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {isNeutral || row.is_win === null ? (
                    <span className="font-mono-num text-xs font-bold text-slate-400">
                      {row.move_pct >= 0 ? '+' : ''}
                      {row.move_pct.toFixed(2)}% (Neutral)
                    </span>
                  ) : (
                    <span
                      className={`font-mono-num text-sm font-extrabold ${
                        row.is_win ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {row.directional_pct >= 0 ? '+' : ''}
                      {row.directional_pct.toFixed(2)}%
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={() => stageRow(row)}
                    className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-[11px] font-bold text-slate-200 transition hover:border-[#FF6B00]/50 active:scale-95"
                  >
                    Sim <ArrowUpRight className="h-3 w-3" />
                  </button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
