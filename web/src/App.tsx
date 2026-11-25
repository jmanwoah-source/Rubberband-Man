import { Component, useEffect, useId, useState } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { BarChart3, BookOpen, GraduationCap, RefreshCw, Search, Zap } from 'lucide-react'
import { fetchBootstrap } from './api'
import { LedgerView } from './components/LedgerView'
import { ScannerView } from './components/ScannerView'
import { SchwabSimView } from './components/SchwabSimView'
import type { BootstrapResponse, TradePrefill } from './types'

type AppTab = 'scan' | 'sim' | 'ledger'

const NAV_TABS: Array<{ id: AppTab; label: string; Icon: typeof Zap }> = [
  { id: 'scan', label: 'Scan', Icon: Zap },
  { id: 'sim', label: 'Sim', Icon: BookOpen },
  { id: 'ledger', label: 'Ledger', Icon: BarChart3 },
]

interface ErrorBoundaryState {
  hasError: boolean
  message: string
}

class AppErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error?.message || 'Unexpected rendering failure.' }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Rubberband UI ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mx-auto mt-10 max-w-lg rounded-2xl border border-rose-500/35 bg-[#0C1018] p-6 text-center shadow-2xl">
          <h2 className="text-base font-extrabold tracking-tight text-white">
            Workspace View Interrupted
          </h2>
          <p className="mt-2 text-xs leading-relaxed text-slate-400">{this.state.message}</p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, message: '' })}
            className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-[#FF6B00] px-4 py-2 text-xs font-extrabold text-white transition hover:bg-[#FF7D1F] active:scale-95"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Recover Workspace
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

export function App() {
  const navId = useId()
  const [activeTab, setActiveTab] = useState<AppTab>('scan')
  const [sector, setSector] = useState('Semiconductors')
  const [ticker, setTicker] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [learnEnabled, setLearnEnabled] = useState(true)
  const [retryNonce, setRetryNonce] = useState(0)

  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null)
  const [settledKey, setSettledKey] = useState('')
  const [errorState, setErrorState] = useState<{ key: string; msg: string } | null>(null)
  const [prefill, setPrefill] = useState<TradePrefill | null>(null)

  const requestKey = `${sector}|${ticker}|${retryNonce}`
  const loading = settledKey !== requestKey
  const errorMsg = errorState?.key === requestKey ? errorState.msg : null

  useEffect(() => {
    const ac = new AbortController()
    fetchBootstrap(sector, ticker, ac.signal)
      .then((res) => {
        if (ac.signal.aborted) return
        setBootstrap(res)
        setErrorState(null)
        setSettledKey(requestKey)
      })
      .catch((err) => {
        if (ac.signal.aborted || (err as Error).name === 'AbortError') return
        setErrorState({ key: requestKey, msg: (err as Error).message })
        setSettledKey(requestKey)
      })
    return () => ac.abort()
  }, [sector, ticker, requestKey])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const clean = searchInput
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9.^-]/g, '')
      .slice(0, 12)
    if (clean) {
      setTicker(clean)
      setSearchInput('')
      setActiveTab('scan')
    }
  }

  const handleSimulate = (order: TradePrefill) => {
    setPrefill(order)
    setActiveTab('sim')
  }

  const handleRetryBootstrap = () => {
    setRetryNonce((n) => n + 1)
  }

  return (
    <div className="min-h-screen bg-[#06070A] pb-24 text-slate-200 sm:pb-10">
      {/* Top Frosted Glass Header */}
      <header className="sticky top-0 z-30 border-b border-white/[0.07] bg-[#06070A]/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-3.5 py-2.5 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl border border-[#FF6B00]/45 bg-[#FF6B00]/15 text-sm font-black text-[#FF8533]">
              R
            </div>
            <div>
              <h1 className="text-sm font-extrabold tracking-tight text-white sm:text-base">
                Rubberband Man
              </h1>
              <p className="font-mono-num hidden text-[10px] text-slate-400 sm:block">
                v4.0 Quant Options Terminal
              </p>
            </div>
          </div>

          {/* Desktop Navigation Pills */}
          <nav className="hidden items-center gap-1 rounded-full border border-white/[0.08] bg-[#0C1018] p-1 md:flex">
            {NAV_TABS.map(({ id, label, Icon }) => {
              const active = activeTab === id
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setActiveTab(id)}
                  className="relative inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-bold transition active:scale-95"
                >
                  {active && (
                    <motion.span
                      layoutId={`desktop-nav-${navId}`}
                      transition={{ type: 'spring', stiffness: 450, damping: 32 }}
                      className="absolute inset-0 rounded-full bg-[#FF6B00]"
                    />
                  )}
                  <span
                    className={`relative z-10 flex items-center gap-1.5 ${
                      active ? 'text-white' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {label}
                  </span>
                </button>
              )
            })}
          </nav>

          {/* Search & Global Learn Toggle */}
          <div className="flex items-center gap-2">
            <form onSubmit={handleSearchSubmit} className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
              <input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                maxLength={12}
                placeholder="Ticker..."
                aria-label="Quick ticker search"
                className="font-mono-num w-24 rounded-full border border-white/10 bg-[#0C1018] py-1.5 pl-8 pr-2.5 text-xs text-white placeholder:text-slate-500 outline-none transition focus:w-32 focus:border-[#FF6B00]/60 sm:w-32 sm:focus:w-40"
              />
            </form>

            <button
              type="button"
              onClick={() => setLearnEnabled((v) => !v)}
              title="Toggle Progressive L1·L2·L3 Learn Chips"
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-[11px] font-bold transition active:scale-95 ${
                learnEnabled
                  ? 'border-sky-400/45 bg-sky-400/15 text-sky-300'
                  : 'border-white/10 bg-[#0C1018] text-slate-400'
              }`}
            >
              <GraduationCap className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{learnEnabled ? 'Learn On' : 'Learn Off'}</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-3.5 pt-4 sm:px-6">
        <AppErrorBoundary>
          {errorMsg && (
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-500/35 bg-rose-500/10 p-4 text-xs text-rose-200">
              <span>API Error: {errorMsg}</span>
              <button
                type="button"
                onClick={handleRetryBootstrap}
                className="inline-flex items-center gap-1.5 rounded-xl border border-rose-400/40 bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-rose-500/30 active:scale-95"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                Retry
              </button>
            </div>
          )}

          <AnimatePresence mode="wait">
            {activeTab === 'scan' && (
              <motion.div
                key="view-scan"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.16 }}
              >
                {bootstrap ? (
                  <ScannerView
                    data={bootstrap}
                    learnEnabled={learnEnabled}
                    loadingTicker={loading}
                    onSelectSector={(sec) => {
                      setSector(sec)
                      setTicker('')
                    }}
                    onSelectTicker={(tk) => setTicker(tk)}
                    onSimulate={handleSimulate}
                  />
                ) : (
                  <div className="space-y-4">
                    <div className="h-24 animate-pulse rounded-2xl bg-white/[0.04]" />
                    <div className="h-80 animate-pulse rounded-2xl bg-white/[0.04]" />
                  </div>
                )}
              </motion.div>
            )}

            {activeTab === 'sim' && (
              <motion.div
                key="view-sim"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.16 }}
              >
                <SchwabSimView
                  prefill={prefill}
                  learnEnabled={learnEnabled}
                  onClearPrefill={() => setPrefill(null)}
                />
              </motion.div>
            )}

            {activeTab === 'ledger' && (
              <motion.div
                key="view-ledger"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.16 }}
              >
                <LedgerView learnEnabled={learnEnabled} onSimulate={handleSimulate} />
              </motion.div>
            )}
          </AnimatePresence>
        </AppErrorBoundary>
      </main>

      {/* Mobile Floating Frosted-Glass Bottom Dock */}
      <div className="fixed inset-x-0 bottom-3 z-40 flex justify-center px-3 md:hidden">
        <nav
          aria-label="Mobile navigation"
          className="grid w-full max-w-md grid-cols-3 gap-1.5 rounded-full border border-white/15 border-t-[#FF6B00]/40 bg-[#0B0E15]/92 p-1.5 shadow-2xl shadow-black/90 backdrop-blur-2xl"
        >
          {NAV_TABS.map(({ id, label, Icon }) => {
            const active = activeTab === id
            return (
              <button
                key={id}
                type="button"
                onClick={() => setActiveTab(id)}
                className="relative flex h-11 items-center justify-center gap-1.5 rounded-full text-xs font-extrabold transition active:scale-95"
              >
                {active && (
                  <motion.span
                    layoutId={`mob-dock-${navId}`}
                    transition={{ type: 'spring', stiffness: 460, damping: 34 }}
                    className="absolute inset-0 rounded-full bg-[#FF6B00] shadow-lg shadow-[#FF6B00]/30"
                  />
                )}
                <span
                  className={`relative z-10 flex items-center gap-1.5 ${
                    active ? 'text-white' : 'text-slate-300'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </span>
              </button>
            )
          })}
        </nav>
      </div>
    </div>
  )
}

export default App
