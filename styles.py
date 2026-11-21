"""
Rubberband Man - Obsidian Frosted-Glass + Rich Hyper-Orange Institutional Terminal CSS
Design System:
- Disciplined #06070A Obsidian Canvas + subtle warm Hyper-Orange (#FF6B00 / #F97316) radial aura
- Frosted glassmorphism (backdrop-filter: blur(22px)) with 1px rgba(255, 255, 255, 0.08) micro-borders
- Typography: Plus Jakarta Sans / Inter + JetBrains Mono (tabular-nums)
- Zero pure #000000 / #FFFFFF body copy; base-4 / base-8 spatial geometry; zero CLS
- Tactile micro-interactions (active: scale(0.95), smooth cubic-bezier spring transitions)
"""


def get_custom_css() -> str:
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700;800&display=swap');
    @import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css');

    :root {
        --rm-bg-obsidian: #06070A;
        --rm-bg-surface: rgba(13, 16, 23, 0.72);
        --rm-bg-surface-elevated: rgba(18, 22, 32, 0.80);
        --rm-border-micro: rgba(255, 255, 255, 0.08);
        --rm-border-specular: rgba(255, 255, 255, 0.14);
        --rm-orange: #FF6B00;
        --rm-orange-hi: #FF8533;
        --rm-orange-soft: #FB923C;
        --rm-emerald: #10B981;
        --rm-rose: #F43F5E;
        --rm-text-primary: #E2E8F0;
        --rm-text-secondary: #CBD5E1;
        --rm-text-muted: #94A3B8;
        --rm-shadow-card: 0 12px 36px -10px rgba(0, 0, 0, 0.75), 0 4px 14px -4px rgba(0, 0, 0, 0.50), inset 0 1px 0 rgba(255, 255, 255, 0.06);
        --rm-shadow-orange: 0 6px 24px -4px rgba(255, 107, 0, 0.36), 0 2px 8px rgba(0, 0, 0, 0.45);
    }

    /* Lucide / FontAwesome Vector Micro-Icons */
    .icon-brand {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        vertical-align: -0.18em;
    }
    .fa-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 6px;
        vertical-align: -0.1em;
    }
    .fa-icon-inline {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        vertical-align: -0.08em;
    }

    /* Global Typography & Disciplined Obsidian Canvas */
    html, body, [class*="css"], .stApp {
        font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #06070A !important;
        color: #E2E8F0 !important;
        letter-spacing: -0.01em;
    }

    .tabular-nums,
    .telem-val,
    .telem-val-hero,
    .watchlist-price,
    .rm-conv-score,
    .rm-command-value,
    .float-metric-val,
    .rm-glass-kpi-val,
    [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-variant-numeric: tabular-nums !important;
    }

    /* Subtle Warm Hyper-Orange Radial Glow Over #06070A Obsidian Base */
    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 0;
        background:
            radial-gradient(ellipse 900px 520px at 14% 0%, rgba(255, 107, 0, 0.085) 0%, rgba(249, 115, 22, 0.03) 45%, transparent 72%),
            radial-gradient(ellipse 760px 480px at 88% 8%, rgba(251, 146, 60, 0.055) 0%, transparent 65%),
            radial-gradient(ellipse 960px 600px at 50% 100%, rgba(148, 163, 184, 0.035) 0%, transparent 70%);
    }

    /* Clean Transparent Streamlit Header */
    header[data-testid="stHeader"],
    div[data-testid="stHeader"] {
        background: transparent !important;
        height: 0px !important;
        min-height: 0px !important;
        padding: 0 !important;
        margin: 0 !important;
        z-index: 99999 !important;
        pointer-events: none !important;
        overflow: visible !important;
    }

    div[data-testid="stToolbar"] {
        background: transparent !important;
        height: 0px !important;
        min-height: 0px !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: visible !important;
        pointer-events: none !important;
    }

    /* Suppress Unwanted Streamlit Chrome (preserve stStatusWidget for live connection status) */
    div[data-testid="stDecoration"],
    .stDeployButton,
    .stAppDeployButton,
    [data-testid="stHeaderActionElements"],
    [data-testid="manage-app-button"],
    #MainMenu,
    footer {
        display: none !important;
        visibility: hidden !important;
        height: 0px !important;
        min-height: 0px !important;
        max-height: 0px !important;
        padding: 0 !important;
        margin: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Native Sidebar Controls: Sleek Obsidian Frosted Expand Button when Collapsed */
    [data-testid="stExpandSidebarButton"],
    [data-testid="collapsedControl"],
    div[data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        position: fixed !important;
        top: 14px !important;
        left: 14px !important;
        z-index: 100000 !important;
    }

    [data-testid="stExpandSidebarButton"] button,
    [data-testid="collapsedControl"] button,
    [data-testid="stSidebarCollapsedControl"] button {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: rgba(16, 20, 29, 0.88) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        color: #F97316 !important;
        border: 1px solid rgba(255, 107, 0, 0.40) !important;
        border-radius: 10px !important;
        padding: 6px 10px !important;
        box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.70), 0 0 12px -2px rgba(255, 107, 0, 0.30) !important;
        cursor: pointer !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    [data-testid="stExpandSidebarButton"] button:hover,
    [data-testid="collapsedControl"] button:hover,
    [data-testid="stSidebarCollapsedControl"] button:hover {
        background: rgba(255, 107, 0, 0.16) !important;
        border-color: #FF8533 !important;
        color: #FF8533 !important;
        transform: scale(1.05) !important;
        box-shadow: 0 6px 20px -2px rgba(0, 0, 0, 0.80), 0 0 18px rgba(255, 107, 0, 0.45) !important;
    }

    [data-testid="stSidebarHeader"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        align-items: center !important;
        justify-content: flex-end !important;
        padding: 4px 8px !important;
    }

    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] button {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        cursor: pointer !important;
    }

    [data-testid="stSidebarCollapseButton"] button {
        color: #94A3B8 !important;
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        padding: 4px 8px !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    [data-testid="stSidebarCollapseButton"] button:hover {
        color: #FF8533 !important;
        background: rgba(255, 107, 0, 0.10) !important;
        border-color: rgba(255, 107, 0, 0.35) !important;
        transform: scale(1.04) !important;
    }

    .block-container {
        padding-top: 1.0rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        max-width: 100% !important;
        width: 100% !important;
        box-sizing: border-box !important;
        background-color: transparent !important;
        position: relative !important;
        z-index: 1 !important;
    }

    /* ========================================================= */
    /* FROSTED OBSIDIAN SIDEBAR                                  */
    /* ========================================================= */
    [data-testid="stAppViewContainer"] {
        overflow-x: hidden !important;
    }
    section[data-testid="stMain"] {
        flex: 1 1 auto !important;
        min-width: 0 !important;
        margin-left: 0 !important;
    }
    section[data-testid="stSidebar"],
    .stSidebar {
        background: linear-gradient(180deg, rgba(11, 13, 19, 0.86) 0%, rgba(7, 9, 13, 0.92) 100%) !important;
        backdrop-filter: blur(22px) saturate(145%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(145%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 12px 0 36px -12px rgba(0, 0, 0, 0.72) !important;
        z-index: 10 !important;
    }
    @media (min-width: 768px) {
        section[data-testid="stSidebar"]:not([aria-expanded="false"]),
        .stSidebar:not([aria-expanded="false"]) {
            min-width: 310px !important;
        }
    }
    section[data-testid="stSidebar"][aria-expanded="false"],
    .stSidebar[aria-expanded="false"] {
        min-width: 0px !important;
        max-width: 0px !important;
        width: 0px !important;
        flex: 0 0 0px !important;
        margin-left: 0px !important;
        padding: 0px !important;
        overflow: hidden !important;
        border-right: none !important;
        box-shadow: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }
    section[data-testid="stSidebar"] > div,
    div[data-testid="stSidebarContent"],
    div[data-testid="stSidebarUserContent"],
    div[data-testid="stSidebarCollapseButton"],
    div[data-testid="stSidebarResizer"] {
        background: transparent !important;
        border-right: none !important;
        box-shadow: none !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.07) !important;
    }
    .rm-sb-section-label {
        font-size: 0.70rem !important;
        font-weight: 800 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        margin: 12px 0 6px 0 !important;
    }

    /* ========================================================= */
    /* FLOATING OBSIDIAN FROSTED-GLASS NAVIGATION PILL DOCK      */
    /* ========================================================= */
    .st-key-rm_top_nav_dock {
        background: linear-gradient(160deg, rgba(16, 20, 29, 0.76) 0%, rgba(10, 12, 18, 0.86) 100%) !important;
        backdrop-filter: blur(22px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(150%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 9999px !important;
        padding: 8px 16px !important;
        margin-bottom: 16px !important;
        box-shadow:
            0 16px 40px -12px rgba(0, 0, 0, 0.80),
            0 4px 16px -4px rgba(0, 0, 0, 0.55),
            0 0 24px -8px rgba(255, 107, 0, 0.14) !important;
    }
    .st-key-rm_top_nav_dock [data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    .st-key-rm_top_nav_dock button {
        min-height: 36px !important;
        height: 36px !important;
        padding: 4px 14px !important;
        font-size: 0.80rem !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
    }
    .rm-nav-brand-inline {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        padding-left: 4px !important;
    }
    .rm-nav-brand-dot {
        width: 9px !important;
        height: 9px !important;
        border-radius: 50% !important;
        background: #FF6B00 !important;
        box-shadow: 0 0 12px rgba(255, 107, 0, 0.85) !important;
        flex-shrink: 0 !important;
    }
    .rm-nav-brand-text {
        font-size: 0.98rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
        background: linear-gradient(180deg, #F1F5F9 0%, #94A3B8 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }
    .rm-nav-tag {
        background: rgba(255, 107, 0, 0.14) !important;
        border: 1px solid rgba(255, 107, 0, 0.40) !important;
        color: #FF8533 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.65rem !important;
        font-weight: 800 !important;
        padding: 2px 8px !important;
        border-radius: 9999px !important;
        letter-spacing: 0.05em !important;
    }
    .rm-nav-subtag {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        color: #CBD5E1 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.65rem !important;
        font-weight: 700 !important;
        padding: 2px 8px !important;
        border-radius: 9999px !important;
        letter-spacing: 0.05em !important;
    }
    .rm-nav-mobile-hdr {
        background: rgba(13, 16, 23, 0.82) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 10px 14px !important;
        margin-bottom: 12px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .rm-nav-brand {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }

    /* ========================================================= */
    /* NEW INSTITUTIONAL GLASS PANELS, 5D STRIP & PILLS          */
    /* ========================================================= */
    .rm-glass-panel {
        background: linear-gradient(155deg, rgba(16, 20, 29, 0.72) 0%, rgba(9, 12, 18, 0.84) 100%) !important;
        backdrop-filter: blur(22px) saturate(145%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(145%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.13) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
        transition: border-color 0.22s cubic-bezier(0.16, 1, 0.3, 1), transform 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .rm-glass-panel:hover {
        border-color: rgba(255, 107, 0, 0.28) !important;
    }

    .rm-symbolism-bar {
        background: linear-gradient(145deg, rgba(16, 20, 29, 0.78) 0%, rgba(10, 12, 18, 0.88) 100%) !important;
        backdrop-filter: blur(22px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(150%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 107, 0, 0.24) !important;
        border-radius: 16px !important;
        padding: 12px 18px !important;
        margin-bottom: 16px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 12px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }

    .rm-5d-strip {
        display: grid !important;
        grid-template-columns: repeat(5, minmax(0, 1fr)) !important;
        gap: 12px !important;
        width: 100% !important;
        margin-bottom: 16px !important;
    }
    @media (max-width: 900px) {
        .rm-5d-strip {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
        }
    }

    .rm-day-card {
        background: linear-gradient(160deg, rgba(17, 21, 31, 0.74) 0%, rgba(10, 13, 20, 0.86) 100%) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 14px 10px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        gap: 6px !important;
        box-shadow: 0 8px 24px -8px rgba(0, 0, 0, 0.65) !important;
        transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
        min-height: 132px !important;
    }
    .rm-day-card:hover {
        transform: translateY(-2px) !important;
        border-color: rgba(255, 255, 255, 0.16) !important;
    }
    .rm-day-card.is-active {
        border-color: rgba(255, 107, 0, 0.55) !important;
        background: linear-gradient(160deg, rgba(255, 107, 0, 0.11) 0%, rgba(12, 15, 22, 0.90) 100%) !important;
        box-shadow: 0 12px 28px -8px rgba(0, 0, 0, 0.75), 0 0 22px -6px rgba(255, 107, 0, 0.32) !important;
    }
    .rm-day-ring-wrap {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 62px !important;
        height: 62px !important;
    }
    .rm-day-label {
        font-size: 0.76rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.02em !important;
        color: #E2E8F0 !important;
        line-height: 1.2 !important;
    }
    .rm-day-sub {
        font-size: 0.68rem !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
        line-height: 1.25 !important;
        max-width: 100% !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }

    .rm-conviction-pill {
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        padding: 4px 10px !important;
        border-radius: 9999px !important;
        background: rgba(15, 19, 28, 0.78) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
        line-height: 1.1 !important;
        white-space: nowrap !important;
    }
    .rm-conviction-pill.is-call {
        border-color: rgba(16, 185, 129, 0.38) !important;
        background: rgba(16, 185, 129, 0.10) !important;
    }
    .rm-conviction-pill.is-put {
        border-color: rgba(244, 63, 94, 0.38) !important;
        background: rgba(244, 63, 94, 0.10) !important;
    }
    .rm-conviction-pill.is-neutral {
        border-color: rgba(148, 163, 184, 0.25) !important;
        background: rgba(148, 163, 184, 0.08) !important;
    }
    .rm-conviction-pill.is-asymmetric {
        border-color: rgba(255, 107, 0, 0.58) !important;
        box-shadow: 0 0 16px -4px rgba(255, 107, 0, 0.38) !important;
    }
    .rm-conv-dot {
        width: 7px !important;
        height: 7px !important;
        border-radius: 50% !important;
        flex-shrink: 0 !important;
    }
    .rm-conv-score {
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }
    .rm-conv-dir {
        font-size: 0.68rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.05em !important;
    }
    .rm-conv-tier {
        font-size: 0.60rem !important;
        font-weight: 800 !important;
        color: #FF8533 !important;
        background: rgba(255, 107, 0, 0.16) !important;
        border: 1px solid rgba(255, 107, 0, 0.35) !important;
        padding: 1px 5px !important;
        border-radius: 9999px !important;
        letter-spacing: 0.04em !important;
    }

    .rm-dte-pill {
        display: inline-flex !important;
        align-items: center !important;
        gap: 5px !important;
        padding: 3px 10px !important;
        border-radius: 9999px !important;
        background: rgba(255, 107, 0, 0.14) !important;
        border: 1px solid rgba(255, 107, 0, 0.42) !important;
        color: #FF8533 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.72rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.04em !important;
        white-space: nowrap !important;
    }

    .rm-scanner-row {
        background: rgba(13, 16, 23, 0.64) !important;
        backdrop-filter: blur(18px) !important;
        -webkit-backdrop-filter: blur(18px) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        margin-bottom: 8px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 12px !important;
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .rm-scanner-row:hover {
        border-color: rgba(255, 107, 0, 0.38) !important;
        background: rgba(20, 24, 35, 0.80) !important;
        transform: translateY(-1px) !important;
    }
    .rm-scanner-row.is-active {
        border-color: rgba(255, 107, 0, 0.60) !important;
        background: rgba(255, 107, 0, 0.08) !important;
        box-shadow: 0 0 18px -6px rgba(255, 107, 0, 0.32) !important;
    }

    .rm-catalyst-col {
        background: linear-gradient(165deg, rgba(15, 19, 28, 0.70) 0%, rgba(9, 12, 18, 0.82) 100%) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 14px 16px !important;
        height: 100% !important;
        box-shadow: 0 10px 28px -10px rgba(0, 0, 0, 0.65) !important;
    }

    /* Uniform UI Kit Zone & Section Headers (rmz-*) */
    .rmz-zone {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        margin: 16px 0 12px 0 !important;
        padding-bottom: 8px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07) !important;
    }
    .rmz-zone-left {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
    }
    .rmz-zone-idx {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.72rem !important;
        font-weight: 800 !important;
        color: #FF8533 !important;
        background: rgba(255, 107, 0, 0.14) !important;
        border: 1px solid rgba(255, 107, 0, 0.35) !important;
        padding: 3px 9px !important;
        border-radius: 9999px !important;
    }
    .rmz-zone-title {
        font-size: 1.02rem !important;
        font-weight: 800 !important;
        color: #E2E8F0 !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        letter-spacing: -0.02em !important;
    }
    .rmz-zone-sub {
        font-size: 0.76rem !important;
        color: #94A3B8 !important;
        margin-top: 2px !important;
    }
    .rmz-sec {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        margin: 8px 0 12px 0 !important;
    }
    .rmz-sec-title {
        font-size: 0.92rem !important;
        font-weight: 800 !important;
        color: #E2E8F0 !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        letter-spacing: -0.015em !important;
    }
    .rmz-sec-sub {
        font-size: 0.75rem !important;
        color: #94A3B8 !important;
        margin-top: 2px !important;
    }
    .rmz-sec-meta {
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        flex-wrap: wrap !important;
    }

    /* ========================================================= */
    /* EXECUTIVE COMMAND HUD BAR (Legacy Compatible)             */
    /* ========================================================= */
    .rm-hud-bar {
        background: rgba(13, 16, 23, 0.74) !important;
        backdrop-filter: blur(22px) saturate(145%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(145%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 16px !important;
        padding: 12px 20px !important;
        margin-bottom: 16px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
        cursor: default !important;
        user-select: none !important;
    }
    .rm-hud-left {
        display: flex !important;
        align-items: center !important;
        gap: 16px !important;
        flex-wrap: wrap !important;
    }
    .rm-hud-brand {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    .rm-hud-title {
        font-size: 1.16rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
        background: linear-gradient(180deg, #F1F5F9 0%, #CBD5E1 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }
    .rm-hud-badge {
        background: rgba(255, 107, 0, 0.14) !important;
        border: 1px solid rgba(255, 107, 0, 0.38) !important;
        color: #FF8533 !important;
        font-size: 0.68rem !important;
        font-weight: 800 !important;
        padding: 2px 8px !important;
        border-radius: 9999px !important;
        letter-spacing: 0.05em !important;
    }
    .rm-hud-pills {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    .hud-pill {
        background: rgba(18, 22, 31, 0.78) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 9999px !important;
        padding: 4px 12px !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        color: #CBD5E1 !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        transition: all 0.15s ease !important;
    }
    .hud-pill.target-pill {
        background: rgba(255, 107, 0, 0.14) !important;
        border-color: rgba(255, 107, 0, 0.42) !important;
        color: #FF8533 !important;
    }
    .rm-hud-right {
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        flex-wrap: wrap !important;
    }

    /* Sankey & Radar Subheads */
    .sankey-subhead-pill {
        display: inline-flex !important;
        align-items: center !important;
        background: rgba(15, 19, 28, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        padding: 5px 12px !important;
        margin-bottom: 8px !important;
        font-size: 0.76rem !important;
        letter-spacing: -0.01em !important;
    }
    .sankey-dot {
        width: 7px !important;
        height: 7px !important;
        border-radius: 50% !important;
        margin-right: 8px !important;
        display: inline-block !important;
    }
    .radar-header-strip {
        background: rgba(15, 19, 28, 0.72) !important;
        backdrop-filter: blur(18px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 8px 16px !important;
        margin-bottom: 12px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
    }
    .radar-header-title {
        font-size: 0.86rem !important;
        font-weight: 700 !important;
        color: #E2E8F0 !important;
        display: flex !important;
        align-items: center !important;
        gap: 6px !important;
        letter-spacing: -0.01em !important;
    }
    .radar-header-subtitle {
        font-size: 0.78rem !important;
        color: #94A3B8 !important;
    }

    .flow-card-micro {
        background: rgba(15, 19, 28, 0.70) !important;
        backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 8px 12px !important;
        margin-top: 4px !important;
        margin-bottom: 8px !important;
        min-height: 48px !important;
        transition: all 0.2s ease !important;
    }
    .flow-card-micro:hover {
        border-color: rgba(255, 107, 0, 0.35) !important;
        transform: translateY(-1px) !important;
    }
    .flow-headline-micro {
        font-size: 0.72rem !important;
        color: #94A3B8 !important;
        font-style: italic !important;
        margin-top: 2px !important;
        line-height: 1.25 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* ========================================================= */
    /* SEAMLESS INTEGRATED TICKER SEARCH BAR                     */
    /* ========================================================= */
    form[data-testid="stForm"]:has(.st-key-search_hero_ticker_input),
    [data-testid="stForm"]:has(.st-key-search_hero_ticker_input) {
        border: 1px solid rgba(255, 107, 0, 0.45) !important;
        border-radius: 9999px !important;
        background: rgba(13, 16, 23, 0.80) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        padding: 4px 6px 4px 8px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.50), 0 0 18px -4px rgba(255, 107, 0, 0.22) !important;
        transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
        display: block !important;
    }
    form[data-testid="stForm"]:has(.st-key-search_hero_ticker_input):hover,
    [data-testid="stForm"]:has(.st-key-search_hero_ticker_input):hover {
        border-color: rgba(255, 107, 0, 0.80) !important;
        box-shadow: 0 8px 28px rgba(0, 0, 0, 0.60), 0 0 24px -2px rgba(255, 107, 0, 0.35) !important;
    }
    form[data-testid="stForm"]:has(.st-key-search_hero_ticker_input):focus-within,
    [data-testid="stForm"]:has(.st-key-search_hero_ticker_input):focus-within {
        border-color: #FF6B00 !important;
        box-shadow: 0 0 0 2px rgba(255, 107, 0, 0.25), 0 0 28px rgba(255, 107, 0, 0.38) !important;
    }
    .st-key-search_hero_ticker_input,
    .st-key-search_hero_ticker_input > div,
    .st-key-search_hero_ticker_input input {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        color: #E2E8F0 !important;
        padding-left: 14px !important;
        padding-right: 10px !important;
        height: 40px !important;
    }
    .st-key-search_hero_ticker_input input::placeholder {
        color: #64748B !important;
        font-size: 0.84rem !important;
    }
    form[data-testid="stForm"]:has(.st-key-search_hero_ticker_input) [data-testid="stFormSubmitButton"],
    [data-testid="stForm"]:has(.st-key-search_hero_ticker_input) [data-testid="stFormSubmitButton"] {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    form[data-testid="stForm"]:has(.st-key-search_hero_ticker_input) button,
    [data-testid="stForm"]:has(.st-key-search_hero_ticker_input) button {
        background: linear-gradient(135deg, #FF6B00 0%, #FF8533 100%) !important;
        color: #090B0F !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.78rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        border: 1px solid rgba(255, 180, 120, 0.45) !important;
        border-radius: 9999px !important;
        height: 38px !important;
        min-height: 38px !important;
        padding: 0 20px !important;
        box-shadow: 0 4px 16px rgba(255, 107, 0, 0.36) !important;
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    form[data-testid="stForm"]:has(.st-key-search_hero_ticker_input) button:active,
    [data-testid="stForm"]:has(.st-key-search_hero_ticker_input) button:active {
        transform: scale(0.95) !important;
    }

    /* ========================================================= */
    /* TICKER HERO TELEMETRY BAR                                 */
    /* ========================================================= */
    .ticker-telemetry-bar {
        background: linear-gradient(155deg, rgba(18, 22, 32, 0.80) 0%, rgba(10, 12, 18, 0.90) 100%) !important;
        backdrop-filter: blur(22px) saturate(145%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(145%) !important;
        border: 1px solid rgba(255, 107, 0, 0.36) !important;
        border-radius: 16px !important;
        padding: 14px 20px !important;
        margin-bottom: 16px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex-wrap: wrap !important;
        gap: 16px !important;
        box-shadow: 0 12px 34px -10px rgba(0, 0, 0, 0.75), 0 0 22px -6px rgba(255, 107, 0, 0.18) !important;
        cursor: default !important;
        user-select: none !important;
    }
    .ticker-identity-item {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
    }
    .ticker-logo-avatar {
        width: 42px !important;
        height: 42px !important;
        border-radius: 12px !important;
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        padding: 3px !important;
        object-fit: contain !important;
    }
    .ticker-logo-badge {
        width: 18px !important;
        height: 18px !important;
        border-radius: 4px !important;
        object-fit: contain !important;
        vertical-align: middle !important;
        margin-right: 5px !important;
        background: rgba(255, 255, 255, 0.08) !important;
    }
    .telem-group {
        display: flex !important;
        align-items: center !important;
        gap: 20px !important;
        flex-wrap: wrap !important;
    }
    .telem-item {
        display: flex !important;
        flex-direction: column !important;
        cursor: default !important;
    }
    .telem-label {
        font-size: 0.68rem !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
    }
    .telem-val-hero {
        font-size: 1.48rem !important;
        font-weight: 800 !important;
        color: #E2E8F0 !important;
        line-height: 1.15 !important;
        letter-spacing: -0.02em !important;
    }
    .telem-val {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        color: #CBD5E1 !important;
        line-height: 1.15 !important;
    }
    .telem-sub {
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
        margin-top: 2px !important;
    }
    .telem-sep {
        width: 1px !important;
        height: 30px !important;
        background: rgba(255, 255, 255, 0.08) !important;
    }

    /* ========================================================= */
    /* FROSTED OBSIDIAN CARDS (.rm-card)                         */
    /* ========================================================= */
    .rm-card {
        background: linear-gradient(160deg, rgba(16, 20, 29, 0.72) 0%, rgba(10, 12, 18, 0.84) 100%) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.13) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        cursor: default !important;
        user-select: none !important;
        transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .rm-card:hover {
        border-color: rgba(255, 107, 0, 0.32) !important;
        transform: translateY(-1.5px) !important;
        box-shadow: 0 16px 40px -10px rgba(0, 0, 0, 0.82), 0 0 20px -6px rgba(255, 107, 0, 0.14) !important;
    }
    .rm-card-title {
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: #94A3B8 !important;
        margin-bottom: 8px !important;
    }
    .rm-card-value {
        font-size: 1.68rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
        color: #E2E8F0 !important;
        line-height: 1.2 !important;
        font-variant-numeric: tabular-nums !important;
    }
    .rm-card-sub {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        margin-top: 8px !important;
        color: #94A3B8 !important;
        line-height: 1.4 !important;
    }

    /* Personal Watchlist */
    .watchlist-box {
        background: rgba(13, 16, 23, 0.72) !important;
        backdrop-filter: blur(18px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 12px !important;
        margin-bottom: 16px !important;
    }
    .watchlist-item {
        background: rgba(20, 24, 34, 0.65) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
        margin-bottom: 8px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        cursor: pointer !important;
        transition: all 0.16s ease !important;
    }
    .watchlist-item:hover {
        border-color: rgba(255, 107, 0, 0.42) !important;
        background: rgba(255, 107, 0, 0.08) !important;
        transform: translateX(2px) !important;
    }
    .watchlist-item.active {
        border-color: #FF6B00 !important;
        background: rgba(255, 107, 0, 0.14) !important;
    }
    .watchlist-sym {
        font-weight: 800 !important;
        font-size: 0.94rem !important;
        color: #E2E8F0 !important;
    }
    .watchlist-price {
        font-size: 0.82rem !important;
        font-weight: 600 !important;
        color: #CBD5E1 !important;
    }

    /* ========================================================= */
    /* TACTILE GLASS BUTTONS & HYPER-ORANGE PRIMARY CTAs         */
    /* ========================================================= */
    .stButton > button,
    [data-testid="stBaseButton-secondary"],
    [data-testid="baseButton-secondary"] {
        background: rgba(255, 255, 255, 0.04) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 9999px !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
        letter-spacing: 0.01em !important;
        padding: 8px 18px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
        cursor: pointer !important;
        outline: none !important;
    }
    .stButton > button:hover,
    [data-testid="stBaseButton-secondary"]:hover,
    [data-testid="baseButton-secondary"]:hover {
        background: rgba(255, 107, 0, 0.12) !important;
        color: #F8FAFC !important;
        border-color: rgba(255, 107, 0, 0.45) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.48), 0 0 14px -2px rgba(255, 107, 0, 0.24) !important;
    }
    .stButton > button:active,
    [data-testid="stBaseButton-secondary"]:active,
    [data-testid="baseButton-secondary"]:active {
        transform: scale(0.95) !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.55) !important;
    }

    /* Primary CTA Button - Rich Hyper-Orange Gradient (#FF6B00 -> #FF8533) */
    [data-testid="stBaseButton-primary"],
    [data-testid="baseButton-primary"],
    .stButton > button[kind="primary"],
    button[kind="primary"] {
        background: linear-gradient(135deg, #FF6B00 0%, #FF8533 100%) !important;
        color: #090B0F !important;
        border: 1px solid rgba(255, 185, 130, 0.50) !important;
        border-radius: 9999px !important;
        font-weight: 800 !important;
        box-shadow: var(--rm-shadow-orange) !important;
    }
    [data-testid="stBaseButton-primary"] p,
    [data-testid="baseButton-primary"] p,
    .stButton > button[kind="primary"] p,
    button[kind="primary"] p {
        color: #090B0F !important;
        font-weight: 800 !important;
    }
    [data-testid="stBaseButton-primary"]:hover,
    [data-testid="baseButton-primary"]:hover,
    .stButton > button[kind="primary"]:hover,
    button[kind="primary"]:hover {
        background: linear-gradient(135deg, #FF7A1A 0%, #FF944D 100%) !important;
        color: #06070A !important;
        border-color: rgba(255, 200, 155, 0.72) !important;
        box-shadow: 0 8px 28px -2px rgba(255, 107, 0, 0.55), 0 0 18px rgba(255, 133, 51, 0.35) !important;
        transform: translateY(-1px) !important;
    }
    [data-testid="stBaseButton-primary"]:active,
    [data-testid="baseButton-primary"]:active,
    .stButton > button[kind="primary"]:active,
    button[kind="primary"]:active {
        transform: scale(0.95) !important;
        box-shadow: 0 2px 8px rgba(255, 107, 0, 0.40) !important;
    }

    /* Compact Sidebar & Multi-Column Ticker/ETF Pill Buttons (Zero Truncation) */
    section[data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div > div > div[data-testid="stButton"] button {
        font-family: 'JetBrains Mono', 'Plus Jakarta Sans', monospace !important;
        font-size: 0.78rem !important;
        padding: 0.35rem 0.45rem !important;
        min-height: 2.05rem !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        letter-spacing: -0.01em !important;
        line-height: 1.15 !important;
    }
    section[data-testid="stSidebar"] .stButton > button p,
    section[data-testid="stSidebar"] .stButton > button span,
    [data-testid="stHorizontalBlock"] .stButton > button p,
    [data-testid="stHorizontalBlock"] .stButton > button span {
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
    }
    /* Prevent multi-column ticker/constituent pill clipping in main canvas / Schwab desk */
    div[data-testid="stHorizontalBlock"] .stButton > button[kind="secondary"] {
        padding: 0.38rem 0.55rem !important;
        font-size: 0.78rem !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        min-height: 2.05rem !important;
    }
    /* Sidebar Watchlist Delete Micro-Buttons */
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[kind="secondary"] {
        padding: 0.35rem 0.45rem !important;
        min-width: 28px !important;
        font-size: 0.78rem !important;
        color: #CBD5E1 !important;
        border-radius: 9999px !important;
        text-align: center !important;
        white-space: nowrap !important;
    }
    [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        color: #FB923C !important;
        border-color: rgba(255, 107, 0, 0.48) !important;
        background: rgba(255, 107, 0, 0.14) !important;
    }

    /* Top-5 Candidate Outline Buttons */
    [class*="st-key-top5_btn_slot"] button,
    div[data-testid="stVerticalBlock"]:has(> div > div > [class*="st-key-top5_btn_slot"]) button,
    .st-key-top5_btn_slot button,
    div[data-testid="stVerticalBlock"]:has(> div > div > .st-key-top5_btn_slot) button,
    div:has(> .top5-btn-slot) + div button,
    div:has(> div > .top5-btn-slot) + div button,
    div[data-testid="element-container"]:has(.top5-btn-slot) + div[data-testid="element-container"] button,
    div[data-testid="stVerticalBlock"]:has(> div > .top5-btn-slot) button,
    div:has(.top5-marker-hook) + div button,
    button.btn-top5-candidate {
        border: 1px solid rgba(255, 107, 0, 0.55) !important;
        box-shadow: 0 0 12px rgba(255, 107, 0, 0.18), inset 0 0 4px rgba(255, 107, 0, 0.08) !important;
    }

    /* ========================================================= */
    /* TOOLTIP ISOLATION (Instant Obsidian Tooltip, No Fade Trap)*/
    /* ========================================================= */
    div[data-baseweb="popover"],
    [data-baseweb="popover"],
    div[data-testid="stTooltip"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        outline: none !important;
        z-index: 999999 !important;
    }
    div[data-baseweb="popover"] > div,
    [data-baseweb="popover"] > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    div[data-testid="stTooltipContent"],
    div[role="tooltip"],
    .stTooltipContent {
        border: 1px solid rgba(255, 107, 0, 0.55) !important;
        border-radius: 10px !important;
        background: linear-gradient(145deg, rgba(13, 16, 23, 0.96) 0%, rgba(8, 10, 15, 0.98) 100%) !important;
        backdrop-filter: blur(22px) !important;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.85), 0 0 18px rgba(255, 107, 0, 0.20) !important;
        color: #E2E8F0 !important;
        font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
        font-size: 0.80rem !important;
        line-height: 1.55 !important;
        padding: 12px 16px !important;
        max-width: 440px !important;
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto !important;
    }
    div[data-testid="stTooltipContent"] > div,
    div[role="tooltip"] > div,
    .stTooltipContent > div {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin: 0 !important;
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto !important;
    }
    div[data-testid="stTooltipContent"] p,
    div[role="tooltip"] p {
        color: #E2E8F0 !important;
        margin: 0 !important;
    }
    div[data-testid="stTooltipContent"] strong,
    div[role="tooltip"] strong {
        color: #FB923C !important;
    }

    /* ========================================================= */
    /* FROSTED INPUTS, SELECTS, METRICS, EXPANDERS & DATAFRAMES  */
    /* ========================================================= */
    [data-testid="stChatInput"],
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] textarea,
    .stTextInput input,
    .stNumberInput input {
        background: rgba(13, 16, 23, 0.78) !important;
        backdrop-filter: blur(18px) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 12px !important;
        color: #E2E8F0 !important;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.35) !important;
    }
    .stTextInput input {
        border-radius: 9999px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
    }
    [data-testid="stChatInput"] textarea::placeholder,
    .stTextInput input::placeholder {
        color: #64748B !important;
    }
    [data-testid="stChatInput"] textarea:focus,
    .stTextInput input:focus,
    .stNumberInput input:focus {
        border-color: #FF6B00 !important;
        box-shadow: 0 0 0 2px rgba(255, 107, 0, 0.24) !important;
    }
    [data-testid="stChatInput"] button {
        background: rgba(255, 107, 0, 0.16) !important;
        border: 1px solid rgba(255, 107, 0, 0.40) !important;
        color: #FF8533 !important;
        border-radius: 9999px !important;
    }

    /* Selectboxes */
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
        background: rgba(13, 16, 23, 0.78) !important;
        backdrop-filter: blur(18px) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 12px !important;
        color: #E2E8F0 !important;
    }
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div:hover,
    [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:hover {
        border-color: rgba(255, 107, 0, 0.45) !important;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: rgba(13, 16, 23, 0.70) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 12px 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    [data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    [data-testid="stMetricValue"] {
        color: #E2E8F0 !important;
        font-weight: 800 !important;
    }

    /* Segmented Control */
    [data-testid="stSegmentedControl"] {
        background: rgba(13, 16, 23, 0.76) !important;
        backdrop-filter: blur(18px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 9999px !important;
        padding: 3px !important;
    }

    /* Chat Messages */
    .stChatMessage,
    [data-testid="stChatMessage"] {
        background: rgba(15, 18, 26, 0.74) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        margin-bottom: 12px !important;
        padding: 16px 20px !important;
        color: #E2E8F0 !important;
        line-height: 1.65 !important;
    }

    /* Action & Tier Badges */
    .badge-call {
        background: rgba(16, 185, 129, 0.14) !important;
        border: 1px solid rgba(16, 185, 129, 0.42) !important;
        color: #34D399 !important;
        font-weight: 700 !important;
        font-size: 0.80rem !important;
        padding: 5px 14px !important;
        border-radius: 9999px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    .badge-put {
        background: rgba(244, 63, 94, 0.14) !important;
        border: 1px solid rgba(244, 63, 94, 0.42) !important;
        color: #FB7185 !important;
        font-weight: 700 !important;
        font-size: 0.80rem !important;
        padding: 5px 14px !important;
        border-radius: 9999px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    .badge-neutral {
        background: rgba(148, 163, 184, 0.14) !important;
        border: 1px solid rgba(148, 163, 184, 0.28) !important;
        color: #CBD5E1 !important;
        font-weight: 700 !important;
        font-size: 0.80rem !important;
        padding: 5px 14px !important;
        border-radius: 9999px !important;
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
    }
    .badge-sector {
        background: rgba(255, 107, 0, 0.14) !important;
        border: 1px solid rgba(255, 107, 0, 0.36) !important;
        color: #FF8533 !important;
        font-size: 0.80rem !important;
        font-weight: 700 !important;
        padding: 4px 14px !important;
        border-radius: 9999px !important;
    }

    /* Arbiter & Trade Cards */
    .arbiter-card {
        background: linear-gradient(160deg, rgba(16, 20, 29, 0.76) 0%, rgba(10, 12, 18, 0.86) 100%) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
        transition: transform 0.2s ease, border-color 0.2s ease !important;
    }
    .arbiter-card:hover {
        border-color: rgba(255, 107, 0, 0.36) !important;
        transform: translateY(-1px) !important;
    }
    .arbiter-card-header {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        padding-bottom: 10px !important;
        margin-bottom: 12px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07) !important;
    }
    .arbiter-card-title {
        font-size: 0.96rem !important;
        font-weight: 800 !important;
        color: #E2E8F0 !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    .arbiter-card-body {
        font-size: 0.86rem !important;
        line-height: 1.65 !important;
        color: #CBD5E1 !important;
    }
    .arbiter-card-body ul { margin: 6px 0 !important; padding-left: 20px !important; }
    .arbiter-card-body li { margin-bottom: 5px !important; }

    .rm-trade-card {
        background: rgba(15, 18, 26, 0.78) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 107, 0, 0.28) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        margin-top: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
        line-height: 1.65 !important;
        color: #E2E8F0 !important;
    }

    .tool-badge {
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        background: rgba(255, 107, 0, 0.14) !important;
        border: 1px solid rgba(255, 107, 0, 0.35) !important;
        color: #FB923C !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-size: 0.78rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        margin-bottom: 8px !important;
    }

    /* Semantic Utility Text Colors */
    .txt-green { color: #10B981 !important; }
    .txt-yellow { color: #FB923C !important; }
    .txt-red { color: #F43F5E !important; }
    .txt-cyan { color: #FB923C !important; }
    .txt-purple { color: #A78BFA !important; }
    .txt-orange { color: #FF6B00 !important; }
    .txt-muted { color: #94A3B8 !important; }

    /* Sector Capital Flow */
    .flow-banner {
        background: rgba(15, 18, 26, 0.74) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .flow-card {
        background: rgba(15, 18, 26, 0.70) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 14px 16px !important;
        margin-bottom: 10px !important;
        transition: all 0.2s ease !important;
    }
    .flow-card:hover {
        border-color: rgba(255, 107, 0, 0.36) !important;
        transform: translateY(-1.5px) !important;
    }
    .flow-badge-inflow {
        background: rgba(16, 185, 129, 0.14) !important;
        color: #10B981 !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
        padding: 3px 10px !important;
        border-radius: 9999px !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
    }
    .flow-badge-outflow {
        background: rgba(244, 63, 94, 0.14) !important;
        color: #F43F5E !important;
        border: 1px solid rgba(244, 63, 94, 0.35) !important;
        padding: 3px 10px !important;
        border-radius: 9999px !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
    }
    .flow-headline {
        font-size: 0.82rem !important;
        color: #CBD5E1 !important;
        font-style: italic !important;
        margin-top: 6px !important;
        line-height: 1.35 !important;
    }

    /* ========================================================= */
    /* FROSTED SEGMENTED TABS PILL BAR                           */
    /* ========================================================= */
    [data-testid="stTabs"] {
        background-color: transparent !important;
        margin-top: 12px !important;
        margin-bottom: 20px !important;
    }
    [data-testid="stTabs"] [role="tablist"] {
        background: rgba(13, 16, 23, 0.76) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 9999px !important;
        padding: 5px 6px !important;
        gap: 6px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45) !important;
    }
    [data-testid="stTabs"] [role="tab"] {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 9999px !important;
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.86rem !important;
        padding: 8px 18px !important;
        transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    [data-testid="stTabs"] [role="tab"]:hover {
        color: #E2E8F0 !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(255, 107, 0, 0.20) 0%, rgba(249, 115, 22, 0.12) 100%) !important;
        color: #FF8533 !important;
        font-weight: 700 !important;
        border: 1px solid rgba(255, 107, 0, 0.48) !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.40), 0 0 16px -2px rgba(255, 107, 0, 0.25) !important;
    }

    /* Radio / Expanders / Dataframes / Alerts */
    [data-testid="stRadio"] label {
        color: #CBD5E1 !important;
        font-weight: 600 !important;
    }
    [data-testid="stRadio"] > div {
        background: rgba(13, 16, 23, 0.72) !important;
        backdrop-filter: blur(18px) !important;
        padding: 6px 10px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    .streamlit-expanderHeader,
    [data-testid="stExpander"] details summary {
        background: rgba(15, 18, 26, 0.74) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        color: #E2E8F0 !important;
        font-weight: 700 !important;
    }
    [data-testid="stExpander"] details {
        border-color: rgba(255, 255, 255, 0.08) !important;
        background: rgba(11, 14, 20, 0.68) !important;
        backdrop-filter: blur(22px) !important;
        border-radius: 14px !important;
    }

    [data-testid="stDataFrame"] {
        background: rgba(13, 16, 23, 0.72) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        overflow: hidden !important;
    }

    [data-testid="stAlert"] {
        background: rgba(15, 18, 26, 0.76) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 107, 0, 0.30) !important;
        color: #E2E8F0 !important;
        border-radius: 14px !important;
    }
    [data-testid="stAlert"] p {
        color: #E2E8F0 !important;
    }

    /* ========================================================= */
    /* EXECUTION, REASONING & PILLAR CONTAINERS                  */
    /* ========================================================= */
    .rm-reasoning-cockpit {
        background: linear-gradient(160deg, rgba(18, 22, 32, 0.76) 0%, rgba(10, 12, 18, 0.88) 100%) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 107, 0, 0.25) !important;
        border-radius: 18px !important;
        padding: 16px 20px !important;
        margin-top: 16px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .rm-reasoning-header {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-bottom: 12px !important;
        flex-wrap: wrap !important;
        gap: 10px !important;
    }
    .rm-reasoning-title {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        font-size: 1.04rem !important;
        font-weight: 800 !important;
        color: #E2E8F0 !important;
    }
    .rm-threat-card {
        background: rgba(13, 16, 23, 0.75) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        margin-top: 16px !important;
        color: #E2E8F0 !important;
        line-height: 1.65 !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .badge-threat-critical {
        background: rgba(244, 63, 94, 0.15) !important;
        border: 1px solid rgba(244, 63, 94, 0.45) !important;
        color: #FB7185 !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-weight: 800 !important;
        font-size: 0.75rem !important;
    }
    .badge-threat-pass {
        background: rgba(16, 185, 129, 0.15) !important;
        border: 1px solid rgba(16, 185, 129, 0.45) !important;
        color: #34D399 !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-weight: 800 !important;
        font-size: 0.75rem !important;
    }
    .badge-threat-warning {
        background: rgba(255, 107, 0, 0.16) !important;
        border: 1px solid rgba(255, 107, 0, 0.45) !important;
        color: #FB923C !important;
        padding: 4px 12px !important;
        border-radius: 9999px !important;
        font-weight: 800 !important;
        font-size: 0.75rem !important;
    }

    .rm-command-bar {
        display: grid !important;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)) !important;
        gap: 12px !important;
        background: rgba(13, 16, 23, 0.74) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .rm-command-card {
        background: rgba(255, 255, 255, 0.025) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 4px !important;
    }
    .rm-command-label {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: #94A3B8 !important;
    }
    .rm-command-value {
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        color: #E2E8F0 !important;
    }
    .rm-command-sub {
        font-size: 0.74rem !important;
        color: #64748B !important;
    }

    .rm-execution-container {
        background: rgba(13, 16, 23, 0.74) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 18px !important;
        padding: 20px 24px !important;
        margin-top: 16px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
        transition: border-color 0.2s ease !important;
    }
    .rm-execution-container:hover {
        border-color: rgba(255, 107, 0, 0.30) !important;
    }
    .rm-brief-col {
        background: rgba(18, 22, 31, 0.72) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 14px !important;
        padding: 16px 18px !important;
        height: 100% !important;
    }
    .rm-blueprint-col {
        background: linear-gradient(160deg, rgba(22, 26, 36, 0.80) 0%, rgba(13, 16, 23, 0.88) 100%) !important;
        border: 1px solid rgba(255, 107, 0, 0.32) !important;
        border-radius: 14px !important;
        padding: 16px 18px !important;
        height: 100% !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.40) !important;
    }
    .score-badge-circle {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 44px !important;
        height: 44px !important;
        border-radius: 50% !important;
        background: rgba(16, 185, 129, 0.14) !important;
        border: 2px solid #10B981 !important;
        color: #10B981 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 800 !important;
        font-size: 1.12rem !important;
    }

    .rm-signage-banner {
        background: linear-gradient(145deg, rgba(16, 20, 29, 0.82) 0%, rgba(10, 12, 18, 0.92) 100%) !important;
        backdrop-filter: blur(22px) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 12px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .rm-pillar-grid {
        display: grid !important;
        grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)) !important;
        gap: 16px !important;
        margin-bottom: 16px !important;
    }
    .rm-pillar-card {
        background: linear-gradient(160deg, rgba(16, 20, 29, 0.74) 0%, rgba(10, 13, 20, 0.86) 100%) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .rm-pillar-card:hover {
        border-color: rgba(255, 107, 0, 0.35) !important;
        transform: translateY(-2px) !important;
    }
    @media (max-width: 1100px) {
        .rm-pillar-grid { grid-template-columns: repeat(3, minmax(140px, 1fr)) !important; }
    }
    @media (max-width: 680px) {
        .rm-pillar-grid { grid-template-columns: repeat(2, minmax(130px, 1fr)) !important; }
    }

    /* ========================================================= */
    /* MOBILE COMPANION & FLOATING BOTTOM DOCK                   */
    /* ========================================================= */
    .mobile-companion-wrapper {
        max-width: 620px;
        margin: 0 auto;
        padding-bottom: 92px;
    }
    .rm-mobile-hero-card {
        background: linear-gradient(155deg, rgba(18, 22, 32, 0.82) 0%, rgba(10, 13, 20, 0.92) 100%) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 107, 0, 0.36) !important;
        border-radius: 18px !important;
        padding: 20px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card), 0 0 24px -6px rgba(255, 107, 0, 0.18) !important;
    }
    .rm-mobile-play-box {
        background: rgba(10, 13, 20, 0.78) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 14px 16px !important;
        margin: 16px 0 !important;
    }
    .rm-mobile-cand-card {
        background: linear-gradient(160deg, rgba(16, 20, 29, 0.74) 0%, rgba(10, 12, 18, 0.86) 100%) !important;
        backdrop-filter: blur(18px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 14px 16px !important;
        margin-bottom: 12px !important;
        transition: all 0.18s ease !important;
    }
    .rm-mobile-cand-card:hover {
        border-color: rgba(255, 107, 0, 0.45) !important;
        transform: translateY(-1px) !important;
    }
    .rm-mobile-dock-spacer {
        height: 80px;
        width: 100%;
    }

    .st-key-rm_mobile_bottom_dock {
        position: fixed !important;
        bottom: 14px !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: calc(100% - 24px) !important;
        max-width: 500px !important;
        z-index: 999999 !important;
        background: rgba(11, 14, 20, 0.88) !important;
        backdrop-filter: blur(24px) saturate(155%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(155%) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-top: 1px solid rgba(255, 107, 0, 0.35) !important;
        border-radius: 9999px !important;
        padding: 6px 10px max(6px, env(safe-area-inset-bottom)) 10px !important;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.85), 0 0 22px -4px rgba(255, 107, 0, 0.22) !important;
    }
    .st-key-rm_mobile_bottom_dock [data-testid="stHorizontalBlock"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 6px !important;
    }
    .st-key-rm_mobile_bottom_dock [data-testid="stColumn"],
    .st-key-rm_mobile_bottom_dock [data-testid="column"] {
        flex: 1 1 0% !important;
        width: 0 !important;
        min-width: 0 !important;
    }
    .st-key-dock_btn_scanner button,
    .st-key-dock_btn_schwab button,
    .st-key-dock_btn_ledger button,
    .st-key-dock_btn_pro_mode button {
        border-radius: 9999px !important;
        font-size: 0.71rem !important;
        font-weight: 800 !important;
        padding: 2px 4px !important;
        min-height: 44px !important;
        height: 44px !important;
        white-space: nowrap !important;
    }

    @media (max-width: 768px) {
        section[data-testid="stMain"] [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewContainer"] > .main {
            padding: 8px 10px calc(92px + env(safe-area-inset-bottom)) 10px !important;
        }
        .rm-hud-bar { padding: 10px 12px !important; border-radius: 12px !important; gap: 8px !important; }
        .rm-hud-title { font-size: 1.05rem !important; }
        .rm-hud-badge { display: none !important; }
        .hud-pill { padding: 3px 8px !important; font-size: 0.70rem !important; }
        .rm-card { padding: 14px 16px !important; margin-bottom: 12px !important; }
        .rm-card-value { font-size: 1.45rem !important; }
        button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-secondary"],
        button[data-testid="baseButton-primary"],
        button[data-testid="baseButton-secondary"] { min-height: 44px !important; }
    }

    /* ========================================================= */
    /* SCHWAB SIMULATOR & TICKER JOURNAL OBSIDIAN GLASS          */
    /* ========================================================= */
    .schwab-ribbon,
    .schwab-ticker-hud {
        background: linear-gradient(155deg, rgba(16, 20, 29, 0.78) 0%, rgba(10, 12, 18, 0.88) 100%) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 107, 0, 0.28) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .schwab-ticket-card,
    .schwab-order-rail {
        background: linear-gradient(160deg, rgba(16, 20, 29, 0.76) 0%, rgba(10, 12, 18, 0.88) 100%) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 107, 0, 0.26) !important;
        border-radius: 16px !important;
        padding: 20px 24px !important;
        box-shadow: var(--rm-shadow-card) !important;
        margin-bottom: 20px !important;
    }
    .schwab-calc-box {
        background: rgba(8, 10, 15, 0.65) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        margin: 16px 0 !important;
    }
    .schwab-receipt-banner {
        background: linear-gradient(145deg, rgba(255, 107, 0, 0.12) 0%, rgba(13, 16, 23, 0.90) 100%) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 107, 0, 0.45) !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 8px 24px rgba(255, 107, 0, 0.16) !important;
    }
    .schwab-pos-card,
    .ledger-rec-card {
        background: linear-gradient(160deg, rgba(16, 20, 29, 0.74) 0%, rgba(10, 12, 18, 0.86) 100%) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 14px !important;
        box-shadow: var(--rm-shadow-card) !important;
        transition: all 0.2s ease !important;
    }
    .schwab-pos-card:hover,
    .ledger-rec-card:hover {
        border-color: rgba(255, 107, 0, 0.40) !important;
        transform: translateY(-1.5px) !important;
    }
    .schwab-chain-box,
    .schwab-chain-container-aaa,
    .schwab-strike-visualizer {
        background: rgba(13, 16, 23, 0.76) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-top: 12px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .schwab-chain-hdr-cell {
        font-size: 0.72rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        color: #94A3B8 !important;
        padding: 6px 8px !important;
    }
    .chain-call-bg { background: rgba(16, 185, 129, 0.08) !important; }
    .chain-put-bg { background: rgba(244, 63, 94, 0.08) !important; }
    .chain-strike-badge {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 800 !important;
        font-size: 0.90rem !important;
        color: #E2E8F0 !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.10) !important;
        padding: 4px 10px !important;
        border-radius: 8px !important;
        display: inline-block !important;
    }

    /* ========================================================= */
    /* SECTOR WORKSPACE, COMPASS & FLOAT TOPOLOGY GLASS          */
    /* ========================================================= */
    .sector-card-cluster {
        background: rgba(14, 18, 26, 0.74) !important;
        backdrop-filter: blur(18px) !important;
        border-radius: 14px !important;
        padding: 12px 14px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: var(--rm-shadow-card) !important;
        min-height: 96px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: space-between !important;
    }
    .sector-card-cluster:hover { transform: translateY(-2px) !important; }
    .sector-pulse-dot {
        display: inline-block !important;
        width: 8px !important;
        height: 8px !important;
        border-radius: 50% !important;
        animation: pulseSectorDot 1.8s infinite !important;
        margin-right: 6px !important;
        vertical-align: middle !important;
    }
    @keyframes pulseSectorDot {
        0% { transform: scale(0.9); opacity: 0.7; }
        50% { transform: scale(1.35); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.7; }
    }
    .sector-workspace-frame {
        border-radius: 18px !important;
        padding: 20px 22px !important;
        margin-top: 16px !important;
        margin-bottom: 24px !important;
        background: rgba(13, 16, 23, 0.76) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    .sector-command-header {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 12px !important;
        padding-bottom: 12px !important;
        margin-bottom: 16px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    .sector-candidate-strip {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        flex-wrap: wrap !important;
        margin-bottom: 16px !important;
        padding: 8px 12px !important;
        background: rgba(0, 0, 0, 0.28) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    .sector-candidate-chip-label {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        margin-right: 6px !important;
    }

    .catalyst-ai-beacon {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        position: relative !important;
        width: 12px !important;
        height: 12px !important;
        margin-right: 8px !important;
    }
    .catalyst-ai-beacon::before {
        content: '' !important;
        position: absolute !important;
        width: 100% !important;
        height: 100% !important;
        border-radius: 50% !important;
        background: radial-gradient(circle, rgba(255, 107, 0, 0.75) 0%, transparent 100%) !important;
        animation: catalystRadarPulse 2.2s cubic-bezier(0.4, 0, 0.6, 1) infinite !important;
    }
    .catalyst-ai-beacon::after {
        content: '' !important;
        position: absolute !important;
        width: 6px !important;
        height: 6px !important;
        border-radius: 50% !important;
        background: #FF6B00 !important;
        box-shadow: 0 0 8px #FF6B00 !important;
    }
    @keyframes catalystRadarPulse {
        0% { transform: scale(0.8); opacity: 1; }
        70% { transform: scale(2.2); opacity: 0; }
        100% { transform: scale(0.8); opacity: 0; }
    }
    .catalyst-card-gradient {
        background: rgba(13, 16, 23, 0.74) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid rgba(255, 107, 0, 0.24) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }

    .st-key-rm_liquidity_centerpiece {
        position: relative !important;
        background:
            radial-gradient(120% 90% at 8% 0%, rgba(255, 107, 0, 0.07) 0%, transparent 52%),
            linear-gradient(155deg, rgba(16, 20, 29, 0.78) 0%, rgba(9, 12, 18, 0.88) 100%) !important;
        backdrop-filter: blur(22px) saturate(150%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(150%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.14) !important;
        border-radius: 20px !important;
        padding: 22px 24px !important;
        margin-top: 10px !important;
        margin-bottom: 24px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .st-key-rm_compass_glass_pane {
        background: rgba(12, 15, 22, 0.74) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .st-key-rm_compass_glass_pane:hover {
        border-color: rgba(255, 107, 0, 0.28) !important;
    }
    .rm-compass-hero-hdr {
        display: flex !important;
        justify-content: space-between !important;
        align-items: flex-start !important;
        flex-wrap: wrap !important;
        gap: 16px !important;
        padding-bottom: 16px !important;
        margin-bottom: 16px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07) !important;
    }
    .rm-compass-title-grad {
        font-size: 1.12rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
        background: linear-gradient(92deg, #E2E8F0 0%, #CBD5E1 52%, #FB923C 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        line-height: 1.2 !important;
    }
    .rm-compass-kpi-row {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
        flex-wrap: wrap !important;
    }
    .rm-glass-kpi-pill {
        background: rgba(13, 16, 23, 0.76) !important;
        backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 6px 12px !important;
        display: flex !important;
        flex-direction: column !important;
        gap: 1px !important;
    }
    .rm-glass-kpi-lbl {
        font-size: 0.62rem !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }
    .rm-glass-kpi-val {
        font-size: 0.80rem !important;
        font-weight: 800 !important;
        color: #E2E8F0 !important;
    }

    .rm-sector-stack-grid {
        display: grid !important;
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 12px !important;
        width: 100% !important;
    }
    @media (max-width: 1100px) { .rm-sector-stack-grid { grid-template-columns: repeat(2, 1fr) !important; } }
    @media (max-width: 650px) { .rm-sector-stack-grid { grid-template-columns: 1fr !important; } }
    .rm-sector-stack-card {
        background: rgba(15, 19, 28, 0.74) !important;
        backdrop-filter: blur(18px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 14px 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
        transition: all 0.2s ease !important;
    }
    .rm-sector-stack-card:hover {
        transform: translateY(-2px) !important;
        border-color: rgba(255, 107, 0, 0.30) !important;
    }
    .rm-breadth-track {
        width: 100% !important;
        height: 7px !important;
        background: rgba(244, 63, 94, 0.18) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 9999px !important;
        overflow: hidden !important;
    }
    .rm-breadth-fill {
        height: 100% !important;
        border-radius: 9999px !important;
        transition: width 0.45s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .rm-tier-legend-pill {
        display: inline-flex !important;
        align-items: center !important;
        gap: 5px !important;
        font-size: 0.68rem !important;
        font-weight: 600 !important;
        color: #CBD5E1 !important;
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 9999px !important;
        padding: 2px 8px !important;
    }

    /* Float Topology Card */
    .float-topology-card {
        background: linear-gradient(160deg, rgba(16, 20, 29, 0.76) 0%, rgba(10, 12, 18, 0.88) 100%) !important;
        backdrop-filter: blur(22px) !important;
        -webkit-backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
        padding: 16px 20px !important;
        margin-top: 10px !important;
        margin-bottom: 16px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .float-topology-hdr {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        margin-bottom: 12px !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
    }
    .float-topology-title {
        font-size: 0.76rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        color: #94A3B8 !important;
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    .float-bar-track {
        height: 12px !important;
        border-radius: 9999px !important;
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        display: flex !important;
        overflow: hidden !important;
        margin-bottom: 10px !important;
    }
    .float-bar-seg {
        height: 100% !important;
        transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .float-legend-row {
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        margin-bottom: 16px !important;
        padding-bottom: 12px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07) !important;
    }
    .float-legend-item {
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        color: #CBD5E1 !important;
    }
    .float-legend-dot {
        width: 8px !important;
        height: 8px !important;
        border-radius: 50% !important;
    }
    .float-grid-4 {
        display: grid !important;
        grid-template-columns: repeat(4, 1fr) !important;
        gap: 12px !important;
        margin-bottom: 12px !important;
    }
    @media (max-width: 900px) { .float-grid-4 { grid-template-columns: repeat(2, 1fr) !important; } }
    .float-metric-tile {
        background: rgba(255, 255, 255, 0.025) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 10px !important;
        padding: 10px 12px !important;
    }
    .float-metric-lbl {
        font-size: 0.65rem !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        margin-bottom: 4px !important;
    }
    .float-metric-val {
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }
    .float-metric-sub {
        font-size: 0.70rem !important;
        color: #64748B !important;
        margin-top: 3px !important;
        font-weight: 500 !important;
    }
    .float-collar-banner {
        background: rgba(255, 107, 0, 0.07) !important;
        border: 1px solid rgba(255, 107, 0, 0.28) !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        font-size: 0.76rem !important;
        color: #E2E8F0 !important;
        line-height: 1.45 !important;
    }
    .squeeze-hazard-pill {
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.72rem !important;
        font-weight: 800 !important;
        padding: 3px 10px !important;
        border-radius: 9999px !important;
        letter-spacing: 0.04em !important;
    }
    .squeeze-hazard-extreme {
        background: rgba(244, 63, 94, 0.16) !important;
        color: #F43F5E !important;
        border: 1px solid rgba(244, 63, 94, 0.45) !important;
    }
    .squeeze-hazard-elevated {
        background: rgba(255, 107, 0, 0.16) !important;
        color: #FB923C !important;
        border: 1px solid rgba(255, 107, 0, 0.45) !important;
    }
    .squeeze-hazard-moderate {
        background: rgba(251, 146, 60, 0.12) !important;
        color: #FDBA74 !important;
        border: 1px solid rgba(251, 146, 60, 0.35) !important;
    }
    .squeeze-hazard-low {
        background: rgba(16, 185, 129, 0.12) !important;
        color: #10B981 !important;
        border: 1px solid rgba(16, 185, 129, 0.30) !important;
    }

    /* Cohesive Section Architecture */
    .rm-section-shell {
        background: rgba(13, 16, 23, 0.74) !important;
        backdrop-filter: blur(22px) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 18px !important;
        padding: 20px 24px !important;
        margin-bottom: 24px !important;
        box-shadow: var(--rm-shadow-card) !important;
    }
    .rm-section-header {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 12px !important;
        padding-bottom: 12px !important;
        margin-bottom: 16px !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.07) !important;
    }
    .rm-section-title-wrap { display: flex !important; align-items: center !important; gap: 10px !important; flex-wrap: wrap !important; }
    .rm-section-tag {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.70rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        padding: 3px 10px !important;
        border-radius: 9999px !important;
    }
    .rm-section-title { font-size: 1.04rem !important; font-weight: 800 !important; color: #E2E8F0 !important; }
    .rm-section-subtitle { font-size: 0.75rem !important; color: #94A3B8 !important; margin-top: 2px !important; }
    .rm-subcard-cushion {
        background: rgba(255, 255, 255, 0.025) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        border-radius: 12px !important;
        padding: 14px 16px !important;
        margin-bottom: 12px !important;
    }
    .rm-metric-pill-bright-green {
        color: #10B981 !important;
        background: rgba(16, 185, 129, 0.12) !important;
        border: 1px solid rgba(16, 185, 129, 0.35) !important;
    }
    .rm-metric-pill-bright-red {
        color: #F43F5E !important;
        background: rgba(244, 63, 94, 0.12) !important;
        border: 1px solid rgba(244, 63, 94, 0.35) !important;
    }
    .rm-metric-pill-bright-amber {
        color: #FB923C !important;
        background: rgba(255, 107, 0, 0.12) !important;
        border: 1px solid rgba(255, 107, 0, 0.35) !important;
    }

    /* ========================================================= */
    /* AAA LUMINESCENT LIQUID PUT-VS-CALL METER (-200 .. +200)   */
    /* ========================================================= */
    @keyframes rmLiquidFlow {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes rmLiquidWave {
        0% { transform: translateX(-35%) skewX(-18deg); }
        100% { transform: translateX(135%) skewX(-18deg); }
    }
    @keyframes rmLiquidBubbles {
        0% { background-position: 0% 100%, 20% 0%; opacity: 0.55; }
        50% { background-position: 60% 20%, 80% 80%; opacity: 0.90; }
        100% { background-position: 120% 100%, 140% 0%; opacity: 0.55; }
    }
    @keyframes rmLiquidGlowPulse {
        0%, 100% { filter: brightness(1.00) saturate(1.08); }
        50% { filter: brightness(1.18) saturate(1.25); }
    }
    .rm-ai-meter-box {
        margin-top: 12px !important;
        padding: 12px 14px !important;
        border-radius: 14px !important;
        background: linear-gradient(155deg, rgba(11, 14, 22, 0.86) 0%, rgba(6, 8, 13, 0.94) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 8px 24px -10px rgba(0, 0, 0, 0.75) !important;
    }
    .rm-ai-meter-hdr {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        flex-wrap: wrap !important;
        gap: 8px !important;
        margin-bottom: 8px !important;
    }
    .rm-ai-meter-summary {
        font-size: 0.79rem !important;
        color: #CBD5E1 !important;
        line-height: 1.50 !important;
        margin-bottom: 10px !important;
    }
    .rm-liquid-scale-row {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.66rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        color: #94A3B8 !important;
        margin-bottom: 5px !important;
    }
    .rm-liquid-tube {
        position: relative !important;
        width: 100% !important;
        height: 22px !important;
        border-radius: 9999px !important;
        background: rgba(4, 6, 10, 0.92) !important;
        border: 1px solid rgba(255, 255, 255, 0.11) !important;
        box-shadow:
            inset 0 3px 8px rgba(0, 0, 0, 0.85),
            inset 0 -1px 0 rgba(255, 255, 255, 0.06),
            0 0 18px -6px var(--rm-liq-glow, rgba(255, 107, 0, 0.35)) !important;
        overflow: hidden !important;
    }
    .rm-liquid-tube::after {
        content: "" !important;
        position: absolute !important;
        top: 2px !important;
        left: 8px !important;
        right: 8px !important;
        height: 4px !important;
        border-radius: 9999px !important;
        background: linear-gradient(180deg, rgba(255, 255, 255, 0.16) 0%, transparent 100%) !important;
        pointer-events: none !important;
        z-index: 4 !important;
    }
    .rm-liquid-center-tick {
        position: absolute !important;
        left: 50% !important;
        top: 0 !important;
        bottom: 0 !important;
        width: 2px !important;
        transform: translateX(-50%) !important;
        background: rgba(226, 232, 240, 0.38) !important;
        box-shadow: 0 0 8px rgba(226, 232, 240, 0.35) !important;
        z-index: 5 !important;
        pointer-events: none !important;
    }
    .rm-liquid-fill {
        position: absolute !important;
        top: 2px !important;
        bottom: 2px !important;
        border-radius: 9999px !important;
        background: linear-gradient(90deg, var(--rm-liq-c1), var(--rm-liq-c2), var(--rm-liq-c3), var(--rm-liq-c2), var(--rm-liq-c1)) !important;
        background-size: 240% 100% !important;
        box-shadow:
            0 0 16px var(--rm-liq-glow),
            0 0 30px -2px var(--rm-liq-glow),
            inset 0 2px 4px rgba(255, 255, 255, 0.38),
            inset 0 -2px 5px rgba(0, 0, 0, 0.35) !important;
        animation: rmLiquidFlow 3.2s linear infinite, rmLiquidGlowPulse 2.6s ease-in-out infinite !important;
        transition: left 0.55s cubic-bezier(0.16, 1, 0.3, 1), width 0.55s cubic-bezier(0.16, 1, 0.3, 1) !important;
        overflow: hidden !important;
        z-index: 2 !important;
    }
    .rm-liquid-wave {
        position: absolute !important;
        inset: 0 !important;
        background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.38) 45%, rgba(255, 255, 255, 0.55) 50%, rgba(255, 255, 255, 0.38) 55%, transparent 100%) !important;
        width: 45% !important;
        filter: blur(2px) !important;
        animation: rmLiquidWave 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite !important;
        pointer-events: none !important;
    }
    .rm-liquid-bubbles {
        position: absolute !important;
        inset: 0 !important;
        background-image:
            radial-gradient(circle at 20% 60%, rgba(255, 255, 255, 0.55) 0px, transparent 2.5px),
            radial-gradient(circle at 55% 35%, rgba(255, 255, 255, 0.45) 0px, transparent 2px),
            radial-gradient(circle at 80% 70%, rgba(255, 255, 255, 0.50) 0px, transparent 2.2px) !important;
        background-size: 56px 20px, 74px 20px, 44px 20px !important;
        animation: rmLiquidBubbles 4.0s linear infinite !important;
        pointer-events: none !important;
    }
    .rm-liquid-meniscus {
        position: absolute !important;
        top: 1px !important;
        bottom: 1px !important;
        width: 6px !important;
        border-radius: 9999px !important;
        background: rgba(255, 255, 255, 0.82) !important;
        box-shadow: 0 0 12px 2px var(--rm-liq-glow) !important;
        z-index: 3 !important;
    }

    /* ========================================================= */
    /* PROGRESSIVE EDUCATIONAL DRAWERS (LEARN MODE)              */
    /* ========================================================= */
    details.rm-edu-drawer {
        background: rgba(13, 17, 25, 0.72) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(56, 189, 248, 0.20) !important;
        border-radius: 12px !important;
        padding: 0 !important;
        margin: 8px 0 14px 0 !important;
        transition: border-color 0.18s ease, box-shadow 0.18s ease !important;
    }
    details.rm-edu-drawer.rm-edu-compact {
        margin: 6px 0 10px 0 !important;
    }
    details.rm-edu-drawer:hover,
    details.rm-edu-drawer[open] {
        border-color: rgba(56, 189, 248, 0.42) !important;
        box-shadow: 0 8px 24px -8px rgba(0, 0, 0, 0.65), 0 0 14px -4px rgba(56, 189, 248, 0.16) !important;
    }
    details.rm-edu-drawer > summary {
        list-style: none !important;
        cursor: pointer !important;
        padding: 9px 14px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        gap: 10px !important;
        flex-wrap: wrap !important;
        user-select: none !important;
    }
    details.rm-edu-drawer > summary::-webkit-details-marker {
        display: none !important;
    }
    .rm-edu-summary-left {
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }
    .rm-edu-pill {
        background: rgba(56, 189, 248, 0.14) !important;
        color: #38BDF8 !important;
        border: 1px solid rgba(56, 189, 248, 0.35) !important;
        border-radius: 9999px !important;
        font-size: 0.66rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.05em !important;
        padding: 2px 8px !important;
        white-space: nowrap !important;
    }
    .rm-edu-title {
        color: #E2E8F0 !important;
        font-size: 0.79rem !important;
        font-weight: 700 !important;
    }
    .rm-edu-live {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.70rem !important;
        color: #94A3B8 !important;
        font-variant-numeric: tabular-nums !important;
    }
    .rm-edu-body {
        border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
        padding: 12px 14px 13px 14px !important;
    }
    .rm-edu-grid {
        display: grid !important;
        grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
        gap: 10px !important;
    }
    @media (max-width: 820px) {
        .rm-edu-grid {
            grid-template-columns: 1fr !important;
        }
    }
    .rm-edu-tier {
        background: rgba(8, 10, 16, 0.65) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 10px !important;
        padding: 10px 12px !important;
    }
    .rm-edu-tier-tag {
        font-size: 0.66rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 5px !important;
    }
    .rm-edu-tier-tag.is-beg { color: #34D399 !important; }
    .rm-edu-tier-tag.is-int { color: #38BDF8 !important; }
    .rm-edu-tier-tag.is-pro { color: #A78BFA !important; }
    .rm-edu-tier-txt {
        font-size: 0.77rem !important;
        line-height: 1.52 !important;
        color: #CBD5E1 !important;
    }
    .rm-edu-tier-txt b {
        color: #F1F5F9 !important;
    }
    .rm-edu-thumb {
        margin-top: 10px !important;
        background: rgba(255, 107, 0, 0.08) !important;
        border: 1px solid rgba(255, 107, 0, 0.25) !important;
        border-radius: 8px !important;
        padding: 7px 11px !important;
        font-size: 0.75rem !important;
        color: #E2E8F0 !important;
        line-height: 1.45 !important;
    }
    .rm-edu-thumb span {
        color: #FF8533 !important;
        font-weight: 800 !important;
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
    </style>
    """
