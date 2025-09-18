# bb_log_tool.py
import streamlit as st
from importlib import import_module
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Global page config (do this once; remove set_page_config from sub-pages)
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Blackboard Log Tool", layout="wide", page_icon="🧭")

# Hide Streamlit's built-in multipage sidebar nav (we provide our own)
st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# Sidebar header: logo + navigation + utilities
# ─────────────────────────────────────────────────────────────
logo_url = "https://logos-world.net/wp-content/uploads/2024/09/Anthology-Symbol.png"
st.sidebar.image(logo_url, use_container_width=True)

st.sidebar.header("Navigation")

# Page registry (label -> module path)
PAGES = {
    "Download Logs": "pages.download",
    "Convert Logs": "pages.convert",
    "Build Search DB": "pages.build",
    "Search DB": "pages.search",
}

# Remember last page across reruns (default to Build Search DB)
default_page = st.session_state.get("current_page", "Build Search DB")
page_labels = list(PAGES.keys())
default_index = page_labels.index(default_page) if default_page in page_labels else 0
page_label = st.sidebar.radio("Go to", page_labels, index=default_index, key="nav_radio")

# Persist selected page in session state
st.session_state["current_page"] = page_label

# Sidebar status chips (helpful context when moving between pages)
db_path = st.session_state.get("search_db_path")
if db_path and Path(db_path).exists():
    st.sidebar.success("Search DB ready")
else:
    st.sidebar.info("No Search DB yet")

# Quick utilities for development & demos
with st.sidebar.expander("Utilities"):
    colA, colB = st.columns(2)
    with colA:
        if st.button("Clear cache", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cache cleared", icon="🧹")
    with colB:
        if st.button("Reset session", use_container_width=True):
            # Clear all session state keys
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.cache_data.clear()
            st.rerun()

# ─────────────────────────────────────────────────────────────
# Page routing (lazy import + friendly errors)
# ─────────────────────────────────────────────────────────────
module_name = PAGES[page_label]
try:
    mod = import_module(module_name)
    if hasattr(mod, "run") and callable(mod.run):
        mod.run()
    else:
        st.error(f"Module '{module_name}' is missing a callable run() function.")
except ModuleNotFoundError as e:
    st.error(f"Could not find page module '{module_name}'.\n\n{e}")
except Exception as e:
    # Show full traceback for quick debugging
    st.exception(e)

# ─────────────────────────────────────────────────────────────
# Optional footer
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="opacity: 0.6; font-size: 0.9em; margin-top: 1rem;">
      BB Log Tool — Build & Search. Use the Utilities to clear cache or reset session during development.
    </div>
    """,
    unsafe_allow_html=True,
)
