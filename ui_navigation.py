"""
Rubberband Man - Institutional Terminal & Mobile Companion Navigation
Unified Floating Obsidian Frosted-Glass Pill Dock & Viewport Density Controller
"""
from __future__ import annotations

import inspect
import streamlit as st

VIEW_TERMINAL = "1–5D Scanner & Options Desk"
VIEW_SCHWAB = "Charles Schwab Practice Desk & Diary"
VIEW_JOURNAL = "Daily Top-5 Recommendation Ledger"

_PAGE_SLUG_TO_VIEW = {
    "terminal": VIEW_TERMINAL,
    "schwab": VIEW_SCHWAB,
    "journal": VIEW_JOURNAL,
}
_VIEW_TO_PAGE_SLUG = {v: k for k, v in _PAGE_SLUG_TO_VIEW.items()}
VIEW_SLUGS = _VIEW_TO_PAGE_SLUG


def _in_multipage_subpage() -> bool:
    """Return True when executing inside a Streamlit pages/* multipage script."""
    for frame in inspect.stack():
        if "/pages/" in frame.filename.replace("\\", "/"):
            return True
    return False


def render_sidebar_grabber() -> None:
    """
    No-op retained for backwards compatibility.
    Native Streamlit `[data-testid="stExpandSidebarButton"]` styled via styles.py handles
    sidebar toggling without body-wide MutationObserver reflows or mobile z-index overlap.
    """
    return None


def sync_workspace_from_query_params() -> None:
    """Restore workspace view and density mode from URL query params on fresh/reconnected sessions."""
    get_current_density_mode()
    qp_page = str(st.query_params.get("page", "") or "").strip().lower()
    if qp_page in _PAGE_SLUG_TO_VIEW and "active_app_view" not in st.session_state:
        st.session_state["active_app_view"] = _PAGE_SLUG_TO_VIEW[qp_page]


def get_current_density_mode() -> str:
    """
    Return 'pro' (Terminal Pro) or 'mobile' (Mobile Companion).
    Preserves selection across session state and `?view=mobile` / `?density=` URL query params.
    """
    qp_view = str(st.query_params.get("view", "") or "").strip().lower()
    qp_density = str(st.query_params.get("density", "") or "").strip().lower()
    qp = qp_view or qp_density

    if qp in ("mobile", "m", "phone", "companion"):
        st.session_state["ui_density_mode"] = "mobile"
    elif qp in ("pro", "desktop", "terminal"):
        st.session_state["ui_density_mode"] = "pro"

    if "ui_density_mode" not in st.session_state:
        st.session_state["ui_density_mode"] = "pro"

    return st.session_state["ui_density_mode"]


def _sync_density_widget_keys(mode: str) -> None:
    lbl = "📱 Mobile Companion" if mode == "mobile" else "🖥️ Terminal Pro"
    for wkey in ("sb_segmented_density_choice", "sb_radio_density_choice"):
        if st.session_state.get(wkey) != lbl:
            try:
                st.session_state[wkey] = lbl
            except Exception:
                # Widget already instantiated earlier in this run; ui_density_mode + query_params will sync on rerun
                pass


def set_density_mode(mode: str) -> None:
    """Update interface density mode, synchronize sidebar widget keys, and update `?view=mobile` query param."""
    if mode not in ("pro", "mobile"):
        return
    st.session_state["ui_density_mode"] = mode
    _sync_density_widget_keys(mode)
    try:
        if mode == "mobile":
            st.query_params["view"] = "mobile"
        else:
            if "view" in st.query_params:
                del st.query_params["view"]
        if "density" in st.query_params:
            del st.query_params["density"]
    except Exception:
        pass


def _navigate_to(target_view: str, target_density: str = "pro") -> None:
    """Switch workspace view and/or density mode cleanly without widget state-fight loops."""
    set_density_mode(target_density)
    st.session_state["pending_workspace_view"] = target_view
    st.session_state["active_app_view"] = target_view
    try:
        slug = _VIEW_TO_PAGE_SLUG.get(target_view, "terminal")
        if slug == "terminal":
            if "page" in st.query_params:
                del st.query_params["page"]
        else:
            st.query_params["page"] = slug
    except Exception:
        pass

    if _in_multipage_subpage():
        page_map = {
            VIEW_TERMINAL: "rubberband.py",
            VIEW_SCHWAB: "pages/1_Schwab_Simulator.py",
            VIEW_JOURNAL: "pages/2_Daily_Recommendations.py",
        }
        dest = page_map.get(target_view, "rubberband.py")
        try:
            st.switch_page(dest)
            return
        except Exception:
            pass
    st.rerun()


def render_sidebar_density_control() -> None:
    """Render a frosted obsidian density toggle in the sidebar using an on_change callback."""
    curr_mode = get_current_density_mode()
    mode_options = ["🖥️ Terminal Pro", "📱 Mobile Companion"]
    desired_lbl = mode_options[0] if curr_mode == "pro" else mode_options[1]

    st.markdown(
        "<div class='rm-sb-section-label'>Interface Density</div>",
        unsafe_allow_html=True,
    )

    def _on_sb_seg_change() -> None:
        chosen = st.session_state.get("sb_segmented_density_choice")
        if chosen:
            set_density_mode("mobile" if "Mobile" in str(chosen) else "pro")

    def _on_sb_radio_change() -> None:
        chosen = st.session_state.get("sb_radio_density_choice")
        if chosen:
            set_density_mode("mobile" if "Mobile" in str(chosen) else "pro")

    try:
        if st.session_state.get("sb_segmented_density_choice") != desired_lbl:
            st.session_state["sb_segmented_density_choice"] = desired_lbl
        st.segmented_control(
            "Density Mode",
            options=mode_options,
            key="sb_segmented_density_choice",
            label_visibility="collapsed",
            on_change=_on_sb_seg_change,
        )
    except Exception:
        if st.session_state.get("sb_radio_density_choice") != desired_lbl:
            st.session_state["sb_radio_density_choice"] = desired_lbl
        st.radio(
            "Density Mode",
            options=mode_options,
            key="sb_radio_density_choice",
            label_visibility="collapsed",
            horizontal=True,
            on_change=_on_sb_radio_change,
        )


def render_top_navigation_strip(current_view: str) -> None:
    """
    Render the floating obsidian frosted-glass pill dock with rich Hyper-Orange active indicator
    linking Terminal, Schwab Simulator, Ticker Journal, and Mobile Companion (`?view=mobile`).
    """
    density = get_current_density_mode()
    is_mobile = (density == "mobile")

    if is_mobile:
        st.markdown(
            """
            <div class="rm-nav-mobile-hdr">
              <div class="rm-nav-brand">
                <span class="rm-nav-brand-dot"></span>
                <span class="rm-nav-brand-text">Rubberband Man</span>
                <span class="rm-nav-tag">MOBILE</span>
              </div>
              <span class="rm-nav-subtag">COMPANION</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_mode, col_view = st.columns([1.15, 1.85], gap="small")
        with col_mode:
            if st.button(
                "🖥️ Terminal",
                key="btn_switch_to_pro_top",
                width="stretch",
                help="Switch to dense multi-column desktop terminal",
            ):
                _navigate_to(current_view, target_density="pro")
        with col_view:
            views_map = {
                VIEW_TERMINAL: "⚡ Terminal Cockpit",
                VIEW_SCHWAB: "📓 Schwab Simulator",
                VIEW_JOURNAL: "📊 Ticker Journal",
            }
            view_keys = list(views_map.keys())
            if st.session_state.get("mobile_workspace_nav_select_top") != current_view:
                st.session_state["mobile_workspace_nav_select_top"] = (
                    current_view if current_view in view_keys else view_keys[0]
                )

            def _on_mobile_top_nav_change() -> None:
                sel_v = st.session_state.get("mobile_workspace_nav_select_top", VIEW_TERMINAL)
                set_density_mode("mobile")
                st.session_state["pending_workspace_view"] = sel_v
                st.session_state["active_app_view"] = sel_v
                try:
                    slug = _VIEW_TO_PAGE_SLUG.get(sel_v, "terminal")
                    if slug == "terminal":
                        if "page" in st.query_params:
                            del st.query_params["page"]
                    else:
                        st.query_params["page"] = slug
                except Exception:
                    pass

            st.selectbox(
                "Workspace Page",
                options=view_keys,
                format_func=lambda k: views_map.get(k, k),
                key="mobile_workspace_nav_select_top",
                label_visibility="collapsed",
                on_change=_on_mobile_top_nav_change,
            )
        return

    nav_items = [
        ("⚡ Terminal", VIEW_TERMINAL, "pro", "btn_nav_dock_terminal", "1–5D Options Terminal Cockpit"),
        ("📓 Schwab Simulator", VIEW_SCHWAB, "pro", "btn_nav_dock_schwab", "Schwab Practice Desk & Order Entry"),
        ("📊 Ticker Journal", VIEW_JOURNAL, "pro", "btn_nav_dock_journal", "Daily Top-5 Recommendation Ledger & Audit"),
        ("📱 Mobile", VIEW_TERMINAL, "mobile", "btn_nav_dock_mobile", "Launch Mobile Companion (?view=mobile)"),
    ]

    with st.container(key="rm_top_nav_dock"):
        c_brand, c_p1, c_p2, c_p3, c_p4 = st.columns([1.65, 1.05, 1.25, 1.15, 0.90], gap="small")
        with c_brand:
            st.markdown(
                """
                <div class="rm-nav-brand-inline">
                  <span class="rm-nav-brand-dot"></span>
                  <span class="rm-nav-brand-text">Rubberband Man</span>
                  <span class="rm-nav-tag">v4.0</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        for col, (label, target_v, target_d, btn_key, help_txt) in zip(
            (c_p1, c_p2, c_p3, c_p4), nav_items
        ):
            is_active = (
                (target_d == "mobile" and is_mobile)
                or (target_d == "pro" and not is_mobile and current_view == target_v)
            )
            with col:
                if st.button(
                    label,
                    key=btn_key,
                    type="primary" if is_active else "secondary",
                    width="stretch",
                    help=help_txt,
                ):
                    if not is_active:
                        _navigate_to(target_v, target_density=target_d)


def render_mobile_bottom_dock(current_view: str) -> None:
    """
    Render the fixed bottom floating obsidian frosted-glass pill dock in Mobile Companion mode.
    Allows 1-thumb switching between Terminal, Schwab Simulator, Ticker Journal, and Desktop Pro.
    """
    if get_current_density_mode() != "mobile":
        return

    st.markdown("<div class='rm-mobile-dock-spacer'></div>", unsafe_allow_html=True)

    with st.container(key="rm_mobile_bottom_dock"):
        dock_c1, dock_c2, dock_c3, dock_c4 = st.columns(4, gap="small")
        with dock_c1:
            is_active = (current_view == VIEW_TERMINAL)
            if st.button(
                "⚡ Scan",
                key="dock_btn_scanner",
                type="primary" if is_active else "secondary",
                width="stretch",
            ):
                if not is_active:
                    _navigate_to(VIEW_TERMINAL, target_density="mobile")
        with dock_c2:
            is_active = (current_view == VIEW_SCHWAB)
            if st.button(
                "📓 Sim",
                key="dock_btn_schwab",
                type="primary" if is_active else "secondary",
                width="stretch",
            ):
                if not is_active:
                    _navigate_to(VIEW_SCHWAB, target_density="mobile")
        with dock_c3:
            is_active = (current_view == VIEW_JOURNAL)
            if st.button(
                "📊 Log",
                key="dock_btn_ledger",
                type="primary" if is_active else "secondary",
                width="stretch",
            ):
                if not is_active:
                    _navigate_to(VIEW_JOURNAL, target_density="mobile")
        with dock_c4:
            if st.button(
                "🖥️ Pro",
                key="dock_btn_pro_mode",
                type="secondary",
                width="stretch",
                help="Switch to Terminal Pro",
            ):
                _navigate_to(current_view, target_density="pro")
