import { useState } from 'react'
import { motion } from 'framer-motion'

interface CorridorProps {
  symbol: string
  spot: number
  vwma20: number
  stopPrice: number
  strike: number
  breakeven: number
  targetPrice: number
  p10Pct?: number
  p25Pct?: number
  p75Pct?: number
  p90Pct?: number
  putWall?: number
  gammaFlip?: number
  callWall?: number
}

interface NodePin {
  id: string
  label: string
  price: number
  color: string
  lane: 0 | 1 | 2
}

export function TradeAnatomyCorridor({
  symbol,
  spot,
  vwma20,
  stopPrice,
  strike,
  breakeven,
  targetPrice,
  p10Pct = -4.6,
  p25Pct = -1.9,
  p75Pct = 2.9,
  p90Pct = 5.8,
  putWall = 0,
  gammaFlip = 0,
  callWall = 0,
}: CorridorProps) {
  const safeSpot = spot > 0 ? spot : 100
  const [activeId, setActiveId] = useState<string>('target')

  const bandPrices = [
    safeSpot * (1 + p10Pct / 100),
    safeSpot * (1 + p25Pct / 100),
    safeSpot * (1 + p75Pct / 100),
    safeSpot * (1 + p90Pct / 100),
  ]
    .map((v) => Math.max(0.5, v))
    .sort((a, b) => a - b)

  const [p10Px, p25Px, p75Px, p90Px] = bandPrices

  const rawNodes: Array<{ id: string; label: string; price: number; color: string }> = [
    { id: 'stop', label: 'Stop', price: stopPrice > 0 ? stopPrice : safeSpot * 0.95, color: '#FB7185' },
    { id: 'spot', label: 'Spot', price: safeSpot, color: '#F8FAFC' },
    { id: 'vwma', label: 'VWMA', price: vwma20 > 0 ? vwma20 : safeSpot, color: '#38BDF8' },
    { id: 'strike', label: 'Strike', price: strike > 0 ? strike : safeSpot, color: '#A78BFA' },
    { id: 'be', label: 'BE', price: breakeven > 0 ? breakeven : safeSpot, color: '#FBBF24' },
    { id: 'target', label: 'Target', price: targetPrice > 0 ? targetPrice : safeSpot * 1.05, color: '#34D399' },
  ]

  const allXs = [...rawNodes.map((n) => n.price), p10Px, p90Px]
  const wallMaxDist = safeSpot * 0.22
  const walls = [
    { id: 'pw', label: 'Put Wall', price: putWall, color: '#F43F5E' },
    { id: 'gf', label: 'γ-Flip', price: gammaFlip, color: '#FF6B00' },
    { id: 'cw', label: 'Call Wall', price: callWall, color: '#10B981' },
  ].filter((w) => w.price > 0 && Math.abs(w.price - safeSpot) <= wallMaxDist)

  walls.forEach((w) => allXs.push(w.price))

  const minX = Math.min(...allXs)
  const maxX = Math.max(...allXs)
  const rawSpan = Math.max(safeSpot * 0.05, maxX - minX)
  const xLo = Math.max(0.1, minX - rawSpan * 0.14)
  const xHi = maxX + rawSpan * 0.14
  const fullSpan = Math.max(1, xHi - xLo)

  const toPct = (px: number) => Math.max(4, Math.min(96, ((px - xLo) / fullSpan) * 100))

  // Assign non-overlapping vertical lanes greedily
  const sortedNodes = [...rawNodes].sort((a, b) => a.price - b.price)
  const laneLastPct: [number, number, number] = [-100, -100, -100]
  const pinnedNodes: NodePin[] = sortedNodes.map((node) => {
    const pct = toPct(node.price)
    let chosen: 0 | 1 | 2 = 0
    for (const candidate of [0, 1, 2] as const) {
      if (pct - laneLastPct[candidate] >= 18) {
        chosen = candidate
        break
      }
      if (candidate === 2) {
        // pick whichever lane has greatest separation
        const gaps = [0, 1, 2].map((i) => pct - laneLastPct[i])
        chosen = (gaps.indexOf(Math.max(...gaps)) as 0 | 1 | 2) || 0
      }
    }
    laneLastPct[chosen] = pct
    return { ...node, lane: chosen }
  })

  const laneTopPx: Record<0 | 1 | 2, number> = { 0: 26, 1: 72, 2: 118 }
  const selectedPin = [...pinnedNodes, ...walls.map((w) => ({ ...w, lane: 1 as const }))].find(
    (item) => item.id === activeId,
  ) ?? pinnedNodes[0]

  const selectedDiffPct = ((selectedPin.price - safeSpot) / safeSpot) * 100

  return (
    <div className="obsidian-card rounded-2xl p-3.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h4 className="text-xs font-bold tracking-tight text-slate-200">
            {symbol} Trade Anatomy &amp; 5Y Probability Corridor
          </h4>
          <p className="font-mono-num mt-0.5 text-[11px] text-slate-400">
            <span className="text-sky-400">P25–P75 Core: ${p25Px.toFixed(2)}–${p75Px.toFixed(2)}</span>
            <span className="mx-1.5 text-slate-600">|</span>
            <span>P10–P90: ${p10Px.toFixed(2)}–${p90Px.toFixed(2)}</span>
          </p>
        </div>

        <div className="font-mono-num rounded-lg border border-white/[0.08] bg-white/[0.03] px-2.5 py-1 text-[11px]">
          <span className="font-bold" style={{ color: selectedPin.color }}>
            {selectedPin.label}
          </span>{' '}
          <span className="text-slate-200">${selectedPin.price.toFixed(2)}</span>{' '}
          <span className={selectedDiffPct >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
            ({selectedDiffPct >= 0 ? '+' : ''}
            {selectedDiffPct.toFixed(1)}%)
          </span>
        </div>
      </div>

      {/* Price Ladder Canvas */}
      <div className="relative mt-3 h-[178px] w-full select-none overflow-hidden rounded-xl border border-white/[0.05] bg-[#080B11]">
        {/* Outer P10-P90 Shaded Corridor */}
        <div
          className="absolute inset-y-0 border-x border-dashed border-sky-400/25 bg-sky-400/[0.06]"
          style={{ left: `${toPct(p10Px)}%`, width: `${Math.max(1, toPct(p90Px) - toPct(p10Px))}%` }}
        />
        {/* Inner P25-P75 Shaded Corridor */}
        <div
          className="absolute inset-y-0 border-x border-sky-400/40 bg-sky-400/[0.13]"
          style={{ left: `${toPct(p25Px)}%`, width: `${Math.max(1, toPct(p75Px) - toPct(p25Px))}%` }}
        />

        {/* Horizontal track */}
        <div className="absolute inset-x-3 top-1/2 h-px bg-white/[0.08]" />

        {/* Setup Nodes */}
        {pinnedNodes.map((pin) => {
          const leftPct = toPct(pin.price)
          const topPx = laneTopPx[pin.lane]
          const isSelected = pin.id === activeId
          const alignRightEdge = leftPct > 82
          const alignLeftEdge = leftPct < 18

          return (
            <motion.button
              key={pin.id}
              type="button"
              onClick={() => setActiveId(pin.id)}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
              className="group absolute -translate-x-1/2 focus:outline-none"
              style={{ left: `${leftPct}%`, top: topPx }}
            >
              <div
                className={`mb-1 whitespace-nowrap rounded-md px-1.5 py-0.5 text-[10px] font-bold transition ${
                  isSelected
                    ? 'border border-white/25 bg-slate-900 text-white shadow-lg'
                    : 'bg-[#080B11]/90 text-slate-300 group-hover:text-white'
                } ${alignRightEdge ? '-translate-x-1/3' : alignLeftEdge ? 'translate-x-1/3' : ''}`}
              >
                <span className="font-mono-num" style={{ color: pin.color }}>
                  {pin.label} ${pin.price.toFixed(0)}
                </span>
              </div>
              <span
                className={`mx-auto block h-2.5 w-2.5 rounded-full border border-[#06070A] transition-transform ${
                  isSelected ? 'scale-125 ring-2 ring-white/40' : 'group-hover:scale-110'
                }`}
                style={{ backgroundColor: pin.color }}
              />
            </motion.button>
          )
        })}

        {/* Dealer Walls Bottom Strip */}
        {walls.map((w) => {
          const leftPct = toPct(w.price)
          return (
            <button
              key={w.id}
              type="button"
              onClick={() => setActiveId(w.id)}
              className="absolute bottom-2 -translate-x-1/2 rounded border border-white/[0.08] bg-[#0B0F18]/90 px-1.5 py-0.5 text-[9px] font-bold transition hover:border-white/25"
              style={{ left: `${leftPct}%`, color: w.color }}
            >
              <span className="font-mono-num">
                {w.label} ${w.price.toFixed(0)}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
