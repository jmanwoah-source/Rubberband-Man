"""
Rubberband Man - Institutional Terminal & Mobile Companion Navigation
Unified Floating Obsidian Frosted-Glass Pill Dock & Viewport Density Controller
"""
from __future__ import annotations

import inspect
import streamlit as st
import streamlit.components.v1 as components


VIEW_TERMINAL = "1–5D Scanner & Options Desk"
VIEW_SCHWAB = "Charles Schwab Practice Desk & Diary"
VIEW_JOURNAL = "Daily Top-5 Recommendation Ledger"


def _in_multipage_subpage() -> bool:
    """Return True when executing inside a Streamlit pages/* multipage script."""
    for frame in inspect.stack():
        if "/pages/" in frame.filename.replace("\\", "/"):
            return True
    return False


def render_sidebar_grabber() -> None:
    """
    Mount the tactile Obsidian + Hyper-Orange sidebar toggle grabber on window.parent.document
    and keep it locked to the sidebar's live right edge across transitions, resizes, and multipage routes.
    """
    components.html(
        """
        <script>
        (function() {
          const parentWin = window.parent;
          const parentDoc = parentWin.document;

          if (typeof parentWin.__rmGrabberCleanup === "function") {
            try { parentWin.__rmGrabberCleanup(); } catch (e) {}
          }

          const oldGrabber = parentDoc.getElementById("rm-sidebar-sliding-grabber");
          if (oldGrabber) oldGrabber.remove();
          const oldStyle = parentDoc.getElementById("rm-sliding-grabber-style");
          if (oldStyle) oldStyle.remove();

          const style = parentDoc.createElement("style");
          style.id = "rm-sliding-grabber-style";
          style.textContent = `
            #rm-sidebar-sliding-grabber {
              position: fixed;
              top: 42%;
              left: 0px;
              z-index: 2147483647;
              cursor: pointer;
              user-select: none;
              transition: transform 0.15s ease;
            }
            #rm-sidebar-sliding-grabber .grabber-tab {
              display: flex;
              align-items: center;
              justify-content: center;
              width: 20px;
              height: 52px;
              background: rgba(13, 16, 23, 0.88);
              backdrop-filter: blur(16px);
              -webkit-backdrop-filter: blur(16px);
              border: 1px solid rgba(255, 107, 0, 0.50);
              border-left: none;
              border-radius: 0 8px 8px 0;
              box-shadow: 2px 0 12px rgba(0, 0, 0, 0.55), 0 0 12px rgba(255, 107, 0, 0.22);
              transition: width 0.2s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.2s ease, box-shadow 0.2s ease;
              pointer-events: none;
            }
            #rm-sidebar-sliding-grabber:hover .grabber-tab {
              width: 26px;
              border-color: #FF6B00;
              box-shadow: 3px 0 16px rgba(0, 0, 0, 0.75), 0 0 18px rgba(255, 107, 0, 0.45);
            }
            #rm-sidebar-sliding-grabber .grabber-grip {
              display: flex;
              align-items: center;
              justify-content: center;
              gap: 2.5px;
              height: 20px;
              pointer-events: none;
            }
            #rm-sidebar-sliding-grabber .grip-line {
              width: 1.5px;
              height: 15px;
              background: #FF8533;
              border-radius: 9999px;
              opacity: 0.85;
              pointer-events: none;
            }
          `;
          parentDoc.head.appendChild(style);

          const grabber = parentDoc.createElement("div");
          grabber.id = "rm-sidebar-sliding-grabber";
          grabber.setAttribute("role", "button");
          grabber.setAttribute("aria-label", "Toggle Sidebar");
          grabber.title = "Toggle Sidebar";
          grabber.innerHTML = `
            <div class="grabber-tab">
              <div class="grabber-grip">
                <span class="grip-line"></span>
                <span class="grip-line"></span>
                <span class="grip-line"></span>
              </div>
            </div>
          `;
          parentDoc.body.appendChild(grabber);

          function getSidebar() {
            return parentDoc.querySelector('section[data-testid="stSidebar"]');
          }
          function isSidebarOpen(sb) {
            if (!sb) return false;
            const aria = sb.getAttribute("aria-expanded");
            if (aria === "false") return false;
            const rect = sb.getBoundingClientRect();
            return aria === "true" && rect.width > 20;
          }
          function findCollapseBtn() {
            return parentDoc.querySelector('[data-testid="stSidebarCollapseButton"] button')
              || parentDoc.querySelector('[data-testid="stSidebarHeader"] button')
              || parentDoc.querySelector('[data-testid="stSidebarCollapseButton"]');
          }
          function findExpandBtn() {
            return parentDoc.querySelector('[data-testid="stExpandSidebarButton"] button')
              || parentDoc.querySelector('[data-testid="stExpandSidebarButton"]')
              || parentDoc.querySelector('[data-testid="collapsedControl"] button')
              || parentDoc.querySelector('[data-testid="stSidebarCollapsedControl"] button');
          }

          function syncPosition() {
            const sb = getSidebar();
            if (!sb || !isSidebarOpen(sb)) {
              grabber.style.left = "0px";
              return;
            }
            const rect = sb.getBoundingClientRect();
            const leftPx = rect.right > 20 ? Math.round(rect.right - 1) : 0;
            grabber.style.left = leftPx + "px";
          }

          let rafId = null;
          function trackTransition(durationMs = 380) {
            if (rafId !== null) {
              parentWin.cancelAnimationFrame(rafId);
              rafId = null;
            }
            const start = performance.now();
            function tick(now) {
              syncPosition();
              if (now - start < durationMs) {
                rafId = parentWin.requestAnimationFrame(tick);
              } else {
                rafId = null;
                syncPosition();
              }
            }
            rafId = parentWin.requestAnimationFrame(tick);
          }

          let observedSb = null;
          let sbAttrObserver = null;
          let sbResizeObserver = null;

          function attachToSidebar(sb) {
            if (!sb || sb === observedSb) return;
            if (sbAttrObserver) sbAttrObserver.disconnect();
            if (sbResizeObserver) sbResizeObserver.disconnect();
            observedSb = sb;

            sbAttrObserver = new MutationObserver(() => {
              syncPosition();
              trackTransition(380);
            });
            sbAttrObserver.observe(sb, {
              attributes: true,
              attributeFilter: ["aria-expanded", "style", "class"]
            });

            if (typeof ResizeObserver !== "undefined") {
              sbResizeObserver = new ResizeObserver(syncPosition);
              sbResizeObserver.observe(sb);
            }
            sb.addEventListener("transitionend", syncPosition);
            syncPosition();
          }

          const domObserver = new MutationObserver(() => {
            const sb = getSidebar();
            if (sb && sb !== observedSb) {
              attachToSidebar(sb);
            }
            syncPosition();
          });
          domObserver.observe(parentDoc.body, { childList: true, subtree: true });

          const onResize = () => syncPosition();
          parentWin.addEventListener("resize", onResize);

          const onGrabberClick = (e) => {
            e.stopPropagation();
            e.preventDefault();
            const sb = getSidebar();
            const btn = isSidebarOpen(sb) ? findCollapseBtn() : findExpandBtn();
            if (btn) btn.click();
            trackTransition(400);
          };
          grabber.addEventListener("click", onGrabberClick);

          attachToSidebar(getSidebar());
          syncPosition();
          const initTimer = parentWin.setTimeout(syncPosition, 150);

          parentWin.__rmGrabberCleanup = function() {
            if (rafId !== null) parentWin.cancelAnimationFrame(rafId);
            parentWin.clearTimeout(initTimer);
            parentWin.removeEventListener("resize", onResize);
            grabber.removeEventListener("click", onGrabberClick);
            domObserver.disconnect();
            if (sbAttrObserver) sbAttrObserver.disconnect();
            if (sbResizeObserver) sbResizeObserver.disconnect();
            if (observedSb) observedSb.removeEventListener("transitionend", syncPosition);
          };
        })();
        </script>
        """,
        height=0,
        width=0,
    )


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


def set_density_mode(mode: str) -> None:
    """Update interface density mode and synchronize `?view=mobile` URL query param."""
    if mode not in ("pro", "mobile"):
        return
    st.session_state["ui_density_mode"] = mode
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
    """Switch workspace view and/or density mode cleanly across app.py and pages/*."""
    set_density_mode(target_density)
    st.session_state["pending_workspace_view"] = target_view
    st.session_state["active_app_view"] = target_view

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
    """Render a frosted obsidian density toggle in the sidebar."""
    curr_mode = get_current_density_mode()
    mode_options = ["🖥️ Terminal Pro", "📱 Mobile Companion"]
    curr_idx = 0 if curr_mode == "pro" else 1

    st.markdown(
        "<div class='rm-sb-section-label'>Interface Density</div>",
        unsafe_allow_html=True,
    )

    try:
        chosen = st.segmented_control(
            "Density Mode",
            options=mode_options,
            default=mode_options[curr_idx],
            key="sb_segmented_density_choice",
            label_visibility="collapsed",
        )
        if chosen:
            new_mode = "mobile" if "Mobile" in chosen else "pro"
            if new_mode != curr_mode:
                set_density_mode(new_mode)
                st.rerun()
    except Exception:
        chosen = st.radio(
            "Density Mode",
            options=mode_options,
            index=curr_idx,
            key="sb_radio_density_choice",
            label_visibility="collapsed",
            horizontal=True,
        )
        new_mode = "mobile" if "Mobile" in chosen else "pro"
        if new_mode != curr_mode:
            set_density_mode(new_mode)
            st.rerun()


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
            curr_idx = view_keys.index(current_view) if current_view in view_keys else 0
            sel = st.selectbox(
                "Workspace Page",
                options=view_keys,
                index=curr_idx,
                format_func=lambda k: views_map.get(k, k),
                key="mobile_workspace_nav_select_top",
                label_visibility="collapsed",
            )
            if sel != current_view:
                _navigate_to(sel, target_density="mobile")
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
                "⚡ Term",
                key="dock_btn_scanner",
                type="primary" if is_active else "secondary",
                width="stretch",
            ):
                if not is_active:
                    _navigate_to(VIEW_TERMINAL, target_density="mobile")
        with dock_c2:
            is_active = (current_view == VIEW_SCHWAB)
            if st.button(
                "📓 Schwab",
                key="dock_btn_schwab",
                type="primary" if is_active else "secondary",
                width="stretch",
            ):
                if not is_active:
                    _navigate_to(VIEW_SCHWAB, target_density="mobile")
        with dock_c3:
            is_active = (current_view == VIEW_JOURNAL)
            if st.button(
                "📊 Journal",
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
