import { useEffect, useRef, useState } from 'react'
import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  LineSeries,
  LineStyle,
  createChart,
} from 'lightweight-charts'
import type { ChartBar } from '../types'

interface ElasticityChartProps {
  symbol: string
  bars: ChartBar[]
  strike?: number
  targetPrice?: number
  stopPrice?: number
  height?: number
}

export function ElasticityChart({
  symbol,
  bars,
  strike,
  targetPrice,
  stopPrice,
  height = 310,
}: ElasticityChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const lastBar = bars[bars.length - 1]
  const [hoverInfo, setHoverInfo] = useState<{
    time: string
    close: number
    vwma20: number
  } | null>(null)

  useEffect(() => {
    setHoverInfo(null)
  }, [symbol, bars])

  useEffect(() => {
    const el = containerRef.current
    if (!el || bars.length === 0) return

    const chart = createChart(el, {
      width: el.clientWidth,
      height,
      layout: {
        background: { type: ColorType.Solid, color: '#080B11' },
        textColor: '#94A3B8',
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(255, 107, 0, 0.38)', width: 1, style: LineStyle.Dashed },
        horzLine: { color: 'rgba(255, 107, 0, 0.38)', width: 1, style: LineStyle.Dashed },
      },
      rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.08)',
      },
      timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.08)',
        timeVisible: false,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      handleScale: { pinch: true, axisPressedMouseMove: true, mouseWheel: true },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10B981',
      downColor: '#F43F5E',
      borderVisible: false,
      wickUpColor: '#10B981',
      wickDownColor: '#F43F5E',
    })
    candleSeries.setData(
      bars.map((b) => ({
        time: b.time,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    )

    const vwmaSeries = chart.addSeries(LineSeries, {
      color: '#FF8533',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    })
    vwmaSeries.setData(bars.map((b) => ({ time: b.time, value: b.vwma20 })))

    const upperSeries = chart.addSeries(LineSeries, {
      color: 'rgba(244, 63, 94, 0.55)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    upperSeries.setData(bars.map((b) => ({ time: b.time, value: b.upper2 })))

    const lowerSeries = chart.addSeries(LineSeries, {
      color: 'rgba(16, 185, 129, 0.55)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
    })
    lowerSeries.setData(bars.map((b) => ({ time: b.time, value: b.lower2 })))

    if (strike && strike > 0) {
      candleSeries.createPriceLine({
        price: strike,
        color: '#A78BFA',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: 'Strike',
      })
    }
    if (targetPrice && targetPrice > 0) {
      candleSeries.createPriceLine({
        price: targetPrice,
        color: '#10B981',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: '+1σ Target',
      })
    }
    if (stopPrice && stopPrice > 0) {
      candleSeries.createPriceLine({
        price: stopPrice,
        color: '#F43F5E',
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: true,
        title: 'Stop',
      })
    }

    const byTime = new Map(bars.map((b) => [b.time, b]))
    chart.subscribeCrosshairMove((param) => {
      if (!param.time || typeof param.time !== 'string') {
        setHoverInfo(null)
        return
      }
      const match = byTime.get(param.time)
      if (match) {
        setHoverInfo({ time: match.time, close: match.close, vwma20: match.vwma20 })
      }
    })

    chart.timeScale().fitContent()

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          chart.applyOptions({ width: Math.floor(entry.contentRect.width) })
        }
      }
    })
    ro.observe(el)

    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [bars, strike, targetPrice, stopPrice, height])

  const hud = hoverInfo ?? (lastBar ? { time: lastBar.time, close: lastBar.close, vwma20: lastBar.vwma20 } : null)

  return (
    <div className="obsidian-card overflow-hidden rounded-2xl p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 px-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold tracking-tight text-slate-200">{symbol} Price &amp; VWMA-20 Envelope</span>
          <span className="font-mono-num hidden rounded border border-white/[0.06] bg-white/[0.03] px-1.5 py-0.5 text-[10px] text-slate-400 sm:inline">
            ±2σ ATR Channel
          </span>
        </div>
        {hud && (
          <div className="font-mono-num flex items-center gap-3 text-[11px]">
            <span className="text-slate-400">{hud.time}</span>
            <span className="font-bold text-slate-100">${hud.close.toFixed(2)}</span>
            <span className="text-[#FF8533]">VWMA ${hud.vwma20.toFixed(2)}</span>
          </div>
        )}
      </div>

      {bars.length === 0 ? (
        <div className="flex h-[240px] items-center justify-center text-xs text-slate-500">
          Historical bars unavailable for {symbol}
        </div>
      ) : (
        <div ref={containerRef} className="w-full touch-pan-y" style={{ height }} />
      )}
    </div>
  )
}
