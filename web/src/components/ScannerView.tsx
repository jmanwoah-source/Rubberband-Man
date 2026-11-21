import { useId } from 'react'
import { motion } from 'framer-motion'
import { Activity, ArrowUpRight, ShieldCheck, SlidersHorizontal } from 'lucide-react'
import type { BootstrapResponse, TradePrefill } from '../types'
import { ElasticityChart } from './ElasticityChart'
import { LearnChip } from './LearnChip'
import { TradeAnatomyCorridor } from './TradeAnatomyCorridor'

interface ScannerViewProps {
  data: BootstrapResponse
  learnEnabled: boolean
  loadingTicker: boolean
  onSelectSector: (sector: string) => void
  onSelectTicker: (ticker: string) => void
  onSimulate: (prefill: TradePrefill) => void
}

function n(val: unknown, fallback = 0): number {
  const num = Number(val)
  return Number.isFinite(num) ? num : fallback
}

function s(val: unknown, fallback = ''): string {
  return val == null ? fallback : String(val)
}

export function ScannerView({
  data,
  learnEnabled,
  loadingTicker,
  onSelectSector,
  onSelectTicker,
  onSimulate,
}: ScannerViewProps) {
  const pillGroupId = useId()
  const cand = data.active_candidate
  const m = (cand.metrics ?? {}) as Record<string, unknown>
  const bp = (cand.blueprint ?? {}) as Record<string, unknown>
  const gw = (cand.gamma_walls ?? m.gamma_walls ?? {}) as Record<string, unknown>
  const qe = (cand.quant_edge ?? m.quant_edge ?? {}) as Record<string, unknown>
  const near = (m.near_live_option ?? {}) as Record<string, unknown>
  const tel = (data.options_telemetry ?? cand.options_telemetry ?? {}) as Record<string, unknown>
  const pillars = (cand.conviction_pillars ?? bp.conviction_pillars ?? {}) as Record<string, number>

  const spot = n(m.price, 100)
  const chg1d = n(m.change_pct_1d, 0)
  const z5 = n(m.z_score_5d, 0)
  const ouHl = n(m.ou_half_life, 4.5)
  const empWin = n(m.empirical_win_rate_pct, 55)
  const action = s(m.action ?? bp.direction, 'MONITOR').toUpperCase()
  const isPut = action.includes('PUT')
  const isCall = action.includes('CALL')

  const score200 = Math.round(
    n(cand.conviction_score_200 ?? bp.conviction_score_200 ?? m.conviction_score_200, 0),
  )
  const convTier = s(cand.conviction_tier ?? bp.conviction_tier, 'WATCH')
  const recDte = Math.round(n(cand.recommended_dte ?? bp.recommended_dte, 35))
  const optExp = s(near.expiry ?? bp.target_expiration, '2026-12-18')
  const optStrike = n(near.strike ?? tel.strike_used ?? m.recommended_strike, spot)
  const optMid = n(near.mid ?? tel.prem_entry, Math.max(0.5, spot * 0.03))
  const optDelta = n(near.delta ?? m.estimated_delta, isPut ? -0.5 : 0.5)
  const bePrice = n(tel.breakeven_hold_price, isPut ? optStrike - optMid : optStrike + optMid)
  const tgtPrice = n(m.target_price, isPut ? spot * 0.94 : spot * 1.06)
  const stpPrice = n(m.invalidation_price, isPut ? spot * 1.05 : spot * 0.95)
  const preferSpread = Boolean(tel.prefer_spread)
  const shortStrike = tel.short_strike ? n(tel.short_strike) : null
  const netDebit = tel.net_debit ? n(tel.net_debit) : optMid

  const netEv = n(qe.net_ev_pct ?? bp.net_ev_pct, 0)
  const qKellyPct = n(qe.quarter_kelly_pct ?? bp.quarter_kelly_pct, 0)

  const macroSymb = (data.catalyst_outlook?.symbolism ?? data.macro_pulse?.symbolism ?? {}) as Record<
    string,
    unknown
  >
  const vixRatio = n(macroSymb.vix_ratio, 0.94)
  const capPct = Math.round(n(macroSymb.exposure_cap_pct, 100))
  const regimeLbl = s(
    macroSymb.regime_label ?? data.macro_pulse?.market_regime_badge,
    'MACRO EQUILIBRIUM',
  )
  const binRisk = s(data.catalyst_outlook?.binary_risk_level, 'MODERATE')
  const catDays = (data.catalyst_outlook?.days ?? []).slice(0, 5)

  const pillarRows = [
    { key: 'elasticity_kalman', label: 'Elasticity', max: 65 },
    { key: 'kinetic_asymmetry', label: 'Kinetic', max: 45 },
    { key: 'dealer_whale_flow', label: 'Dealer Flow', max: 40 },
    { key: 'surface_convexity', label: 'Convexity', max: 30 },
    { key: 'regime_solvency', label: 'Regime', max: 20 },
  ]

  const top5List = data.ranked_candidates.slice(0, 5)

  const handleStageOrder = () => {
    const useSpread = preferSpread && shortStrike != null && shortStrike > 0
    onSimulate({
      symbol: data.active_ticker,
      option_type: isPut ? 'PUT' : 'CALL',
      strategy: useSpread ? 'VERTICAL_DEBIT_SPREAD' : 'SINGLE_LEG',
      strike: optStrike,
      short_strike: useSpread ? shortStrike : null,
      expiration_date: optExp.length >= 10 ? optExp.slice(0, 10) : '2026-12-18',
      dte: recDte,
      limit_price: useSpread ? netDebit : optMid,
      stock_price_at_entry: spot,
      target_stock_price: tgtPrice,
      stop_stock_price: stpPrice,
      conviction_score: score200,
      notes: `${action} ${data.active_ticker} | Conv ${score200 >= 0 ? '+' : ''}${score200} (${convTier}) | Dual Z ${z5.toFixed(2)}σ`,
    })
  }

  return (
    <div className="space-y-4">
      {/* Macro Weather + 5D Catalyst Strip */}
      <div className="obsidian-card rounded-2xl p-3.5">
        <div className="flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[11px] font-bold tracking-tight text-slate-200">
              <Activity className="h-3.5 w-3.5 text-[#FF6B00]" />
              {regimeLbl}
            </span>
            <span className="font-mono-num rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 text-[11px] text-slate-300">
              VIX Term <strong className={vixRatio >= 1 ? 'text-rose-400' : 'text-emerald-400'}>{vixRatio.toFixed(2)}x</strong>
            </span>
            <span className="font-mono-num rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 text-[11px] text-slate-300">
              Cap <strong className="text-slate-100">{capPct}%</strong>
            </span>
            <span className="font-mono-num rounded-full border border-white/[0.06] bg-white/[0.02] px-2.5 py-1 text-[11px] text-slate-300">
              Shield <strong className="text-[#FF8533]">{binRisk}</strong>
            </span>
          </div>

          <LearnChip topic={data.edu_topics.macro_regime} enabled={learnEnabled} label="Macro Weather" />
        </div>

        {catDays.length > 0 && (
          <div className="mt-3 flex snap-x snap-mandatory gap-2 overflow-x-auto pb-0.5 no-scrollbar sm:grid sm:grid-cols-5 sm:overflow-visible sm:pb-0">
            {catDays.map((d, idx) => {
              const pct = Math.max(12, Math.min(100, n(d.intensity_pct, 45)))
              const r = 13
              const circ = 2 * Math.PI * r
              const dashOffset = circ * (1 - pct / 100)
              const strokeCol =
                d.risk_tone === 'HIGH' || d.risk_tone === 'BINARY'
                  ? '#FF6B00'
                  : d.risk_tone === 'CLEAR'
                    ? '#10B981'
                    : '#94A3B8'
              return (
                <div
                  key={`${d.day_short ?? idx}-${idx}`}
                  className={`flex min-w-[138px] shrink-0 snap-start items-center gap-2.5 rounded-xl border px-2.5 py-2 sm:min-w-0 sm:shrink ${
                    d.is_today
                      ? 'border-[#FF6B00]/40 bg-[#FF6B00]/[0.07]'
                      : 'border-white/[0.05] bg-white/[0.02]'
                  }`}
                >
                  <svg className="h-8 w-8 shrink-0 -rotate-90" viewBox="0 0 34 34">
                    <circle cx="17" cy="17" r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="2.5" />
                    <circle
                      cx="17"
                      cy="17"
                      r={r}
                      fill="none"
                      stroke={strokeCol}
                      strokeWidth="2.5"
                      strokeDasharray={circ}
                      strokeDashoffset={dashOffset}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="min-w-0">
                    <div className="font-mono-num whitespace-nowrap text-[11px] font-bold text-slate-100">
                      {d.day_short} {d.day_num}
                    </div>
                    <div className="truncate text-[10px] font-medium text-slate-400" title={s(d.headline_tag, 'FLOW')}>
                      {s(d.headline_tag, 'FLOW')}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Compact Sector Dropdown + Horizontal Pill Rails */}
      <div className="obsidian-card space-y-2.5 rounded-2xl p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="h-3.5 w-3.5 text-slate-400" />
            <select
              aria-label="Sector Desk"
              value={data.sector}
              onChange={(e) => onSelectSector(e.target.value)}
              className="rounded-lg border border-white/10 bg-[#080B11] px-2.5 py-1.5 text-xs font-semibold text-slate-100 outline-none transition focus:border-[#FF6B00]/60"
            >
              {data.sectors.map((sec) => (
                <option key={sec} value={sec}>
                  {sec}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            {data.thematic_etfs.map((etf) => {
              const active = etf === data.active_ticker
              return (
                <button
                  key={etf}
                  type="button"
                  onClick={() => onSelectTicker(etf)}
                  className="relative shrink-0 rounded-full px-2.5 py-1 text-[11px] font-bold transition active:scale-95"
                >
                  {active && (
                    <motion.span
                      layoutId={`etf-pill-${pillGroupId}`}
                      transition={{ type: 'spring', stiffness: 450, damping: 32 }}
                      className="absolute inset-0 rounded-full border border-[#FF6B00]/60 bg-[#FF6B00]/20"
                    />
                  )}
                  <span
                    className={`font-mono-num relative z-10 ${
                      active ? 'text-[#FF8533]' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {etf}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Sector Top-5 Quick Rail */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pt-0.5">
          <span className="shrink-0 text-[10px] font-bold tracking-wider text-slate-500 uppercase">
            Top-5
          </span>
          {top5List.map((row) => {
            const active = row.symbol === data.active_ticker
            const dirCol =
              row.conviction_score_200 >= 36
                ? 'text-emerald-400'
                : row.conviction_score_200 <= -36
                  ? 'text-rose-400'
                  : 'text-slate-400'
            return (
              <button
                key={row.symbol}
                type="button"
                onClick={() => onSelectTicker(row.symbol)}
                className={`relative flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold transition active:scale-95 ${
                  active
                    ? 'border-[#FF6B00]/60 bg-[#FF6B00]/15 text-white'
                    : 'border-white/[0.06] bg-white/[0.02] text-slate-300 hover:border-white/15'
                }`}
              >
                <span className="font-mono-num">{row.symbol}</span>
                <span className={`font-mono-num text-[10px] ${dirCol}`}>
                  {row.conviction_score_200 >= 0 ? '+' : ''}
                  {Math.round(row.conviction_score_200)}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Main Command Grid: Hero Conviction + Charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-12">
        {/* Hero Card & Ticket */}
        <motion.div
          key={data.active_ticker}
          initial={{ opacity: 0.75, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="obsidian-card flex flex-col justify-between rounded-2xl p-4 lg:col-span-5"
        >
          <div>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-mono-num text-2xl font-extrabold tracking-tight text-white">
                    {data.active_ticker}
                  </h2>
                  {cand.is_etf && (
                    <span className="rounded-md border border-white/10 bg-white/[0.04] px-1.5 py-0.5 text-[10px] font-bold text-slate-300">
                      ETF
                    </span>
                  )}
                </div>
                <p className="mt-0.5 truncate text-xs text-slate-400">
                  {cand.company_name ?? data.sector}
                </p>
                <div className="font-mono-num mt-2 flex items-baseline gap-2.5">
                  <span className="text-2xl font-extrabold text-slate-100">${spot.toFixed(2)}</span>
                  <span className={`text-xs font-bold ${chg1d >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {chg1d >= 0 ? '+' : ''}
                    {chg1d.toFixed(2)}%
                  </span>
                  <span className="text-[11px] text-slate-400">Z {z5 >= 0 ? '+' : ''}{z5.toFixed(2)}σ</span>
                </div>
              </div>

              <div className="text-right">
                <span
                  className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-extrabold tracking-wide ${
                    isCall
                      ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-400'
                      : isPut
                        ? 'border-rose-500/40 bg-rose-500/15 text-rose-400'
                        : 'border-white/10 bg-white/[0.04] text-slate-300'
                  }`}
                >
                  {action}
                </span>
                <div className="font-mono-num mt-2 text-lg font-extrabold text-[#FF8533]">
                  {score200 >= 0 ? '+' : ''}
                  {score200}
                  <span className="text-xs font-medium text-slate-500">/±200</span>
                </div>
                <div className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
                  {convTier}
                </div>
              </div>
            </div>

            {/* 5-Pillar Spring Progress Strip */}
            <div className="mt-4 grid grid-cols-5 gap-1.5">
              {pillarRows.map((p) => {
                const val = n(pillars[p.key], 0)
                const widthPct = Math.min(100, Math.max(6, (Math.abs(val) / p.max) * 100))
                const barColor = val >= 4 ? 'bg-emerald-400' : val <= -4 ? 'bg-rose-400' : 'bg-slate-500'
                return (
                  <div
                    key={p.key}
                    className="rounded-lg border border-white/[0.05] bg-[#080B11] px-2 py-1.5"
                  >
                    <div className="truncate text-[9px] font-semibold text-slate-400">{p.label}</div>
                    <div className="font-mono-num mt-0.5 text-[11px] font-bold text-slate-200">
                      {val >= 0 ? '+' : ''}
                      {val.toFixed(0)}
                    </div>
                    <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-white/[0.06]">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${widthPct}%` }}
                        transition={{ type: 'spring', stiffness: 260, damping: 24 }}
                        className={`h-full rounded-full ${barColor}`}
                      />
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Contract Execution Box */}
            <div className="mt-4 rounded-xl border border-white/[0.07] bg-[#080B11]/90 p-3">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span className="font-bold text-slate-200">
                  {preferSpread && shortStrike
                    ? `Vertical Spread $${optStrike.toFixed(0)}/$${shortStrike.toFixed(0)}`
                    : `${recDte}D High-Delta Contract`}
                </span>
                <span className="font-mono-num">{optExp}</span>
              </div>
              <div className="font-mono-num mt-2 flex items-baseline justify-between">
                <span className="text-base font-extrabold text-white">
                  ${optStrike.toFixed(2)} {isPut ? 'PUT' : 'CALL'}
                </span>
                <span className="text-base font-extrabold text-emerald-400">
                  ${(preferSpread && shortStrike ? netDebit : optMid).toFixed(2)}{' '}
                  <span className="text-[11px] font-normal text-slate-400">
                    (${Math.round((preferSpread && shortStrike ? netDebit : optMid) * 100)}/ct)
                  </span>
                </span>
              </div>
              <div className="font-mono-num mt-2.5 grid grid-cols-4 gap-1.5 border-t border-white/[0.06] pt-2 text-[10px]">
                <div>
                  <span className="block text-slate-500">Delta</span>
                  <span className="font-bold text-slate-200">{optDelta.toFixed(2)}</span>
                </div>
                <div>
                  <span className="block text-slate-500">Breakeven</span>
                  <span className="font-bold text-slate-200">${bePrice.toFixed(2)}</span>
                </div>
                <div>
                  <span className="block text-slate-500">Target</span>
                  <span className="font-bold text-emerald-400">${tgtPrice.toFixed(2)}</span>
                </div>
                <div>
                  <span className="block text-slate-500">Stop</span>
                  <span className="font-bold text-rose-400">${stpPrice.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <div className="font-mono-num mt-3 flex items-center justify-between text-[11px] text-slate-400">
              <span>
                5Y Win <strong className="text-slate-200">{empWin.toFixed(0)}%</strong>
              </span>
              <span>
                τ½ <strong className="text-slate-200">{ouHl.toFixed(1)}d</strong>
              </span>
              <span>
                5D EV{' '}
                <strong className={netEv >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
                  {netEv >= 0 ? '+' : ''}
                  {netEv.toFixed(1)}%
                </strong>
              </span>
              <span>
                ¼-Kelly <strong className="text-slate-200">{qKellyPct.toFixed(1)}%</strong>
              </span>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 pt-2">
            <button
              type="button"
              onClick={handleStageOrder}
              disabled={loadingTicker}
              className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-[#FF6B00] px-4 py-2.5 text-xs font-extrabold tracking-tight text-white shadow-lg shadow-[#FF6B00]/20 transition hover:bg-[#FF7D1F] active:scale-95 disabled:opacity-60"
            >
              <ShieldCheck className="h-4 w-4" />
              Simulate in Schwab
              <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
            <LearnChip topic={data.edu_topics.mobile_hero} enabled={learnEnabled} label="Hero Guide" />
          </div>
        </motion.div>

        {/* Right Column: TradingView Lightweight Charts + Trade Anatomy Corridor */}
        <div className="space-y-4 lg:col-span-7">
          <div className="space-y-2">
            <ElasticityChart
              symbol={data.active_ticker}
              bars={data.chart_series}
              strike={optStrike}
              targetPrice={tgtPrice}
              stopPrice={stpPrice}
            />
            <div className="flex flex-wrap items-center justify-end gap-2">
              <LearnChip topic={data.edu_topics.elasticity_micro} enabled={learnEnabled} label="Elasticity" />
              <LearnChip topic={data.edu_topics.conviction_5pillar} enabled={learnEnabled} label="5 Pillars" />
            </div>
          </div>

          <div className="space-y-2">
            <TradeAnatomyCorridor
              symbol={data.active_ticker}
              spot={spot}
              vwma20={n(m.vwma20, spot)}
              stopPrice={stpPrice}
              strike={optStrike}
              breakeven={bePrice}
              targetPrice={tgtPrice}
              p10Pct={n(m.p10_close_pct, -4.6)}
              p25Pct={n(m.p25_close_pct, -1.9)}
              p75Pct={n(m.p75_close_pct, 2.9)}
              p90Pct={n(m.p90_close_pct, 5.8)}
              putWall={n(gw.put_wall_strike, 0)}
              gammaFlip={n(gw.gamma_flip_strike, 0)}
              callWall={n(gw.call_wall_strike, 0)}
            />
            <div className="flex flex-wrap items-center justify-end gap-2">
              <LearnChip topic={data.edu_topics.trade_anatomy} enabled={learnEnabled} label="Corridor Map" />
              <LearnChip topic={data.edu_topics.options_surface} enabled={learnEnabled} label="GEX & VRP" />
            </div>
          </div>
        </div>
      </div>

      {/* Scanner Matrix: Ultra-clean 3-Column Ranked Table */}
      <div className="obsidian-card rounded-2xl p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold tracking-tight text-slate-100">
              {data.sector} Ranked Scanner
            </h3>
            <p className="text-xs text-slate-400">
              Ranked by magnitude of 5-pillar conviction and 5Y spread-adjusted expectancy.
            </p>
          </div>
          <LearnChip topic={data.edu_topics.scanner_matrix} enabled={learnEnabled} label="Matrix Guide" />
        </div>

        <div className="divide-y divide-white/[0.05]">
          {data.ranked_candidates.slice(0, 8).map((row, idx) => {
            const isSel = row.symbol === data.active_ticker
            const rowAct = s(row.action, 'MONITOR')
            const posConv = row.conviction_score_200 >= 0
            return (
              <button
                key={row.symbol}
                type="button"
                onClick={() => onSelectTicker(row.symbol)}
                className={`grid w-full grid-cols-12 items-center gap-2 rounded-xl px-2.5 py-2.5 text-left transition active:scale-[0.99] ${
                  isSel ? 'bg-[#FF6B00]/10' : 'hover:bg-white/[0.03]'
                }`}
              >
                <div className="col-span-4 flex items-center gap-2.5 sm:col-span-4">
                  <span className="font-mono-num w-5 text-[11px] font-bold text-slate-500">
                    #{idx + 1}
                  </span>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono-num text-sm font-extrabold text-white">
                        {row.symbol}
                      </span>
                      {row.is_etf && (
                        <span className="rounded border border-white/10 px-1 text-[9px] text-slate-400">
                          ETF
                        </span>
                      )}
                    </div>
                    <div className="font-mono-num text-[11px] text-slate-400">
                      ${n(row.price, 0).toFixed(2)} · Win {n(row.empirical_win_rate_pct, 55).toFixed(0)}%
                    </div>
                  </div>
                </div>

                <div className="col-span-5 flex flex-wrap items-center gap-2 sm:col-span-5">
                  <span
                    className={`font-mono-num rounded-full border px-2 py-0.5 text-[11px] font-extrabold ${
                      Math.abs(row.conviction_score_200) >= 110
                        ? 'border-[#FF6B00]/50 bg-[#FF6B00]/15 text-[#FF8533]'
                        : posConv
                          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                          : 'border-rose-500/30 bg-rose-500/10 text-rose-400'
                    }`}
                  >
                    {posConv ? '+' : ''}
                    {Math.round(row.conviction_score_200)}
                  </span>
                  <span className="font-mono-num text-xs text-slate-300">
                    ${n(row.strike, 0).toFixed(0)} {rowAct.includes('PUT') ? 'P' : 'C'} ·{' '}
                    {Math.round(n(row.recommended_dte, 35))}D
                  </span>
                </div>

                <div className="col-span-3 text-right sm:col-span-3">
                  <span
                    className={`font-mono-num text-xs font-extrabold ${
                      n(row.net_ev_pct, 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {n(row.net_ev_pct, 0) >= 0 ? '+' : ''}
                    {n(row.net_ev_pct, 0).toFixed(1)}% EV
                  </span>
                  <div className="text-[10px] text-slate-500">{isSel ? 'Active' : 'Inspect'}</div>
                </div>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
