import { useCallback, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface ScrollRailProps {
  children: ReactNode
  className?: string
  contentClassName?: string
  ariaLabel?: string
}

/**
 * Low-profile horizontal scroll container that automatically surfaces subtle
 * left/right frosted-glass chevron buttons whenever content overflows its width,
 * making mobile-first snap rails effortless to navigate with a desktop mouse.
 */
export function ScrollRail({
  children,
  className = '',
  contentClassName = '',
  ariaLabel = 'Scrollable strip',
}: ScrollRailProps) {
  const scrollerRef = useRef<HTMLDivElement | null>(null)
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(false)

  const syncEdges = useCallback(() => {
    const el = scrollerRef.current
    if (!el) return
    const maxScroll = Math.max(0, el.scrollWidth - el.clientWidth)
    setCanLeft(el.scrollLeft > 4)
    setCanRight(maxScroll - el.scrollLeft > 4)
  }, [])

  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    syncEdges()
    const ro = new ResizeObserver(syncEdges)
    ro.observe(el)
    if (el.firstElementChild) {
      ro.observe(el.firstElementChild)
    }
    return () => ro.disconnect()
  }, [syncEdges, children])

  const nudge = (dir: -1 | 1) => {
    const el = scrollerRef.current
    if (!el) return
    const step = Math.max(150, Math.round(el.clientWidth * 0.72))
    el.scrollBy({ left: dir * step, behavior: 'smooth' })
  }

  return (
    <div className={`relative min-w-0 ${className}`}>
      <div
        ref={scrollerRef}
        onScroll={syncEdges}
        aria-label={ariaLabel}
        className={`flex items-center overflow-x-auto no-scrollbar ${contentClassName}`}
      >
        {children}
      </div>

      {canLeft && (
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center bg-gradient-to-r from-[#0C1018] via-[#0C1018]/85 to-transparent pr-4 pl-0.5">
          <button
            type="button"
            onClick={() => nudge(-1)}
            aria-label={`Scroll ${ariaLabel} left`}
            className="pointer-events-auto flex h-7 w-7 items-center justify-center rounded-full border border-white/12 bg-[#0B0F17]/92 text-slate-300 shadow-lg shadow-black/70 backdrop-blur-md transition hover:border-[#FF6B00]/50 hover:text-white active:scale-95"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {canRight && (
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center bg-gradient-to-l from-[#0C1018] via-[#0C1018]/85 to-transparent pl-4 pr-0.5">
          <button
            type="button"
            onClick={() => nudge(1)}
            aria-label={`Scroll ${ariaLabel} right`}
            className="pointer-events-auto flex h-7 w-7 items-center justify-center rounded-full border border-white/12 bg-[#0B0F17]/92 text-slate-300 shadow-lg shadow-black/70 backdrop-blur-md transition hover:border-[#FF6B00]/50 hover:text-white active:scale-95"
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  )
}
