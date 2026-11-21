export interface EduTopic {
  key: string
  title: string
  live: string
  l1: string
  l2: string
  l3: string
  rule_of_thumb: string
}

export interface ChartBar {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  vwma20: number
  upper2: number
  lower2: number
}

export interface CandidateSummary {
  symbol: string
  company_name?: string
  sector?: string
  is_etf?: boolean
  is_top5_vetted?: boolean
  sector_rank?: number
  price?: number
  change_pct_1d?: number
  z_score_5d?: number
  action?: string
  conviction_score_200: number
  conviction_tier?: string
  recommended_dte?: number
  empirical_win_rate_pct?: number
  empirical_sample_n?: number
  net_ev_pct?: number
  strike?: number
  delta?: number
  mid?: number
  vrp_vol_pts?: number
  prefer_spread?: boolean
  days_to_earnings?: number
  whale_badge?: string
}

export interface CandidateDetail {
  symbol: string
  company_name?: string
  sector?: string
  industry?: string
  is_etf?: boolean
  benchmark?: string
  is_top5_vetted?: boolean
  conviction_score_200?: number
  conviction_tier?: string
  recommended_dte?: number
  dte_rationale?: string
  synergy_unlocked?: boolean
  regime_gate_mult?: number
  conviction_pillars?: Record<string, number>
  metrics?: Record<string, unknown>
  fundamentals?: Record<string, unknown>
  blueprint?: Record<string, unknown>
  options_telemetry?: Record<string, unknown>
  gamma_walls?: Record<string, unknown>
  quant_edge?: Record<string, unknown>
}

export interface CatalystDay {
  day_short?: string
  day_num?: string
  is_today?: boolean
  intensity_pct?: number
  risk_tone?: string
  headline_tag?: string
}

export interface CatalystOutlook {
  directional_bias?: string
  binary_risk_level?: string
  recommended_dte?: number
  dte_rationale?: string
  days?: CatalystDay[]
  fed_and_macro_events?: Array<{ event?: string; title?: string; date?: string }>
  symbolism?: Record<string, unknown>
}

export interface MacroPulse {
  market_regime_badge?: string
  spy_change?: number
  spy_rvol?: number
  tape_conviction_score?: number
  symbolism?: Record<string, unknown>
}

export interface BootstrapResponse {
  sector: string
  sectors: string[]
  thematic_etfs: string[]
  macro_pulse: MacroPulse
  catalyst_outlook: CatalystOutlook
  ranked_candidates: CandidateSummary[]
  active_ticker: string
  active_candidate: CandidateDetail
  chart_series: ChartBar[]
  options_telemetry: Record<string, unknown>
  edu_topics: Record<string, EduTopic>
}

export interface TickerDetailResponse {
  symbol: string
  sector: string
  active_candidate: CandidateDetail
  catalyst_outlook: CatalystOutlook
  chart_series: ChartBar[]
  options_telemetry: Record<string, unknown>
  edu_topics: Record<string, EduTopic>
}

export interface DiaryPortfolioSummary {
  starting_paper_capital: number
  current_portfolio_value: number
  realized_pnl_dollars: number
  unrealized_pnl_dollars: number
  total_pnl_dollars: number
  total_closed_trades: number
  open_trades_count: number
  win_rate_pct: number
  active_capital_deployed: number
}

export interface DiaryTrade {
  id: number
  schwab_order_id?: string
  symbol: string
  action: string
  option_type: string
  strategy?: string
  strike: number
  short_strike?: number | null
  expiration_date: string
  quantity: number
  entry_premium: number
  stock_price_at_entry: number
  target_stock_price?: number | null
  stop_stock_price?: number | null
  exit_premium?: number | null
  exit_stock_price?: number | null
  realized_pnl_dollar?: number | null
  realized_pnl_pct?: number | null
  status: string
  created_at?: string
  notes?: string
}

export interface DiaryResponse {
  summary: DiaryPortfolioSummary
  open_trades: DiaryTrade[]
  closed_trades: DiaryTrade[]
  edu_topic?: EduTopic | null
}

export interface LedgerSnapshotRow {
  symbol: string
  sector?: string
  normalized_sector?: string
  rank: number
  action: string
  price_at_snapshot: number
  current_price: number
  move_pct: number
  directional_pct: number
  is_win: boolean
  recommended_strike?: number
  expected_basis_pct?: number
  composite_score?: number
  whale_badge?: string
  target_price?: number
  invalidation_price?: number
}

export interface LedgerResponse {
  dates: string[]
  selected_date: string
  sectors?: string[]
  snapshots: LedgerSnapshotRow[]
  stats: {
    count: number
    wins?: number
    win_rate_pct: number
    avg_dir_pct: number
  }
  edu_topic?: EduTopic | null
}

export interface TradePrefill {
  symbol: string
  option_type: 'CALL' | 'PUT'
  strategy: 'SINGLE_LEG' | 'VERTICAL_DEBIT_SPREAD'
  strike: number
  short_strike?: number | null
  expiration_date: string
  dte: number
  limit_price: number
  stock_price_at_entry: number
  target_stock_price?: number | null
  stop_stock_price?: number | null
  conviction_score: number
  notes: string
}
