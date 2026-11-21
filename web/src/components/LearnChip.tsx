import { useId, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Lightbulb, X } from 'lucide-react'
import type { EduTopic } from '../types'

interface LearnChipProps {
  topic?: EduTopic | null
  enabled?: boolean
  label?: string
}

type LevelKey = 'l1' | 'l2' | 'l3'

const LEVELS: Array<{ key: LevelKey; badge: string; name: string; colorClass: string }> = [
  { key: 'l1', badge: 'L1', name: 'Plain English', colorClass: 'text-emerald-400' },
  { key: 'l2', badge: 'L2', name: 'Live Tape', colorClass: 'text-sky-400' },
  { key: 'l3', badge: 'L3', name: 'Desk Pro', colorClass: 'text-violet-400' },
]

export function LearnChip({ topic, enabled = true, label }: LearnChipProps) {
  const [open, setOpen] = useState(false)
  const [level, setLevel] = useState<LevelKey>('l1')
  const tabGroupId = useId()

  if (!enabled || !topic) return null

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="group inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-[#0D111A]/85 px-2.5 py-1 text-left transition-all hover:border-sky-400/40 active:scale-95"
      >
        <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-sky-400/40 bg-sky-400/10 text-[10px] font-black text-sky-400">
          ◈
        </span>
        <span className="text-[11px] font-semibold tracking-tight text-slate-300 group-hover:text-white">
          {label ?? topic.title}
        </span>
        <span className="font-mono-num rounded-full border border-white/[0.08] bg-white/[0.03] px-1.5 py-0.5 text-[9px] font-bold tracking-wider text-slate-400">
          L1·L2·L3
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
            />
            <motion.div
              initial={{ opacity: 0, y: 24, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 18, scale: 0.98 }}
              transition={{ type: 'spring', stiffness: 420, damping: 32 }}
              className="fixed inset-x-3 bottom-4 z-50 mx-auto max-w-xl rounded-2xl border border-white/10 bg-[#0B0F17]/95 p-4 shadow-2xl shadow-black/90 backdrop-blur-2xl sm:inset-x-auto sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:w-full sm:-translate-x-1/2 sm:-translate-y-1/2"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-sky-400/45 bg-sky-400/15 text-xs font-black text-sky-400">
                    ◈
                  </span>
                  <div>
                    <h3 className="text-sm font-bold tracking-tight text-slate-100">{topic.title}</h3>
                    <p className="font-mono-num mt-0.5 text-[11px] text-slate-400">{topic.live}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="Close guide"
                  className="rounded-lg border border-white/[0.07] bg-white/[0.03] p-1.5 text-slate-400 transition hover:text-white active:scale-95"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Sliding spring level switcher */}
              <div className="mt-3.5 grid grid-cols-3 gap-1 rounded-xl border border-white/[0.07] bg-[#07090E] p-1">
                {LEVELS.map((item) => {
                  const active = level === item.key
                  return (
                    <button
                      key={item.key}
                      type="button"
                      onClick={() => setLevel(item.key)}
                      className="relative rounded-lg px-2 py-1.5 text-center text-[11px] font-bold transition-colors active:scale-95"
                    >
                      {active && (
                        <motion.span
                          layoutId={`edu-tab-${tabGroupId}`}
                          transition={{ type: 'spring', stiffness: 450, damping: 32 }}
                          className="absolute inset-0 rounded-lg border border-white/10 bg-white/[0.07]"
                        />
                      )}
                      <span className="relative z-10 flex items-center justify-center gap-1.5">
                        <span className={`font-mono-num ${item.colorClass}`}>{item.badge}</span>
                        <span className={active ? 'text-slate-100' : 'text-slate-400'}>{item.name}</span>
                      </span>
                    </button>
                  )
                })}
              </div>

              <AnimatePresence mode="wait">
                <motion.div
                  key={level}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  transition={{ duration: 0.14 }}
                  className="mt-3 rounded-xl border border-white/[0.06] bg-white/[0.02] p-3.5 text-[13px] leading-relaxed text-slate-300"
                >
                  {topic[level]}
                </motion.div>
              </AnimatePresence>

              <div className="mt-3 flex items-start gap-2 rounded-xl border border-[#FF6B00]/25 bg-[#FF6B00]/[0.07] px-3 py-2 text-xs text-slate-200">
                <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#FF8533]" />
                <span>
                  <strong className="font-bold text-[#FF8533]">Rule of Thumb:</strong> {topic.rule_of_thumb}
                </span>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
