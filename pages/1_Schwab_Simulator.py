import os
import streamlit as st
from PIL import Image
import styles
import diary_views

try:
    import ui_navigation
except Exception:
    ui_navigation = None

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ICON_PATH = os.path.join(_APP_ROOT, "spline_pointer.png")

try:
    _page_icon_img = Image.open(_ICON_PATH) if os.path.exists(_ICON_PATH) else None
except Exception:
    _page_icon_img = None

st.set_page_config(
    page_title="Charles Schwab Practice Desk & Diary | Rubberband Man",
    page_icon=_page_icon_img,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Handle cross-page workspace routing triggered by ui_navigation top strip or mobile dock
_pending_view = st.session_state.pop("pending_workspace_view", None)
if _pending_view == "1–5D Scanner & Options Desk":
    st.session_state["active_app_view"] = _pending_view
    st.switch_page("rubberband.py")
elif _pending_view == "Daily Top-5 Recommendation Ledger":
    st.session_state["active_app_view"] = _pending_view
    st.switch_page("pages/2_Daily_Recommendations.py")

# Inject Obsidian Frosted-Glass + Hyper-Orange CSS
st.markdown(styles.get_custom_css(), unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div style="background: rgba(15, 18, 26, 0.72); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 10px 12px; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
        <span style="font-size: 1.05rem; font-weight: 800; color: #F1F5F9; letter-spacing: -0.02em;">Rubberband Man</span>
        <span style="background: rgba(255, 107, 0, 0.16); color: #FF8533; font-size: 0.66rem; font-weight: 800; padding: 2px 8px; border-radius: 9999px; border: 1px solid rgba(255, 107, 0, 0.42); letter-spacing: 0.04em;">SCHWAB DESK</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("← Back to 1–5D Scanner Desk", key="btn_back_to_scanner", width="stretch", type="primary"):
        st.session_state["active_app_view"] = "1–5D Scanner & Options Desk"
        st.session_state["radio_app_workspace_view"] = "1–5D Scanner & Options Desk"
        st.switch_page("rubberband.py")

    if st.button("📊 Daily Top-5 Ledger", key="btn_jump_ledger_from_schwab_sb", width="stretch"):
        st.session_state["active_app_view"] = "Daily Top-5 Recommendation Ledger"
        st.switch_page("pages/2_Daily_Recommendations.py")

    if ui_navigation is not None:
        ui_navigation.render_sidebar_density_control()

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

# Render Full Dedicated Charles Schwab Options Practice Desk & Mental Diary
diary_views.render_schwab_practice_diary_page()
