import logging
from importlib import import_module
from pathlib import Path
from typing import Dict

import streamlit as st

# Configure lightweight logging for debugging / runtime diagnostics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bb_log_tool")

# ─────────────────────────────────────────────────────────────
# Constants / Configuration
# ─────────────────────────────────────────────────────────────
APP_TITLE = "Blackboard Log Tool"
PAGE_ICON = "🧭"
DEFAULT_LAYOUT = "wide"
DEFAULT_LOGO_URL = "https://logos-world.net/wp-content/uploads/2024/09/Anthology-Symbol.png"
# Explicit page registry only (no discovery)
PAGES: Dict[str, str] = {
    "Download Logs": "pages.download",
    "Convert Logs": "pages.convert",
    "Analyze Logs": "pages.analyze",
}

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def safe_set_page_config():
    """
    Set Streamlit page config once. Avoid error if called multiple times.
    """
    try:
        st.set_page_config(page_title=APP_TITLE, layout=DEFAULT_LAYOUT, page_icon=PAGE_ICON)
    except Exception as e:
        # Streamlit raises an error if set_page_config is called after the first run.
        # Log and continue — not fatal.
        logger.debug("set_page_config call skipped (already set): %s", e)


# ─────────────────────────────────────────────────────────────
# App layout and navigation
# ─────────────────────────────────────────────────────────────
def main() -> None:
    safe_set_page_config()

    # Hide Streamlit's built-in multipage nav (we provide our own)
    st.markdown(
        """
        <style>
            [data-testid="stSidebarNav"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar header: logo + navigation + utilities
    logo_url = DEFAULT_LOGO_URL
    # Provide an accessible caption so screen-readers have context
    st.sidebar.image(logo_url, caption="Anthology / Blackboard logo", use_container_width=True)
    st.sidebar.header("Navigation")

    # Use explicit pages mapping only (no auto-discovery)
    pages = PAGES

    # Initialize session state from query params if provided (deep-linking)
    # NOTE: replaced deprecated experimental_get_query_params with st.query_params
    query_params = st.query_params
    initial_page = query_params.get("page", [None])[0] if query_params else None

    default_page = st.session_state.get("current_page", initial_page or list(pages.keys())[0])
    if default_page not in pages:
        default_page = list(pages.keys())[0]

    # Sidebar radio for navigation
    page_labels = list(pages.keys())
    default_index = page_labels.index(default_page) if default_page in page_labels else 0
    page_label = st.sidebar.radio("Go to", page_labels, index=default_index, key="nav_radio")

    # Persist selected page in session state and sync to query params for deep linking / sharing
    if st.session_state.get("current_page") != page_label:
        st.session_state["current_page"] = page_label
        try:
            st.experimental_set_query_params(page=page_label)
        except Exception:
            # Not critical; query params are optional
            logger.debug("Could not set query params for page selection")

    # Developer utilities
    with st.sidebar.expander("Utilities"):
        colA, colB = st.columns(2)
        with colA:
            if st.button("Clear cache"):
                try:
                    st.cache_data.clear()
                except Exception as e:
                    logger.exception("Failed to clear cache: %s", e)
                    st.error(f"Failed to clear cache: {e}")
                else:
                    # Streamlit's newer versions support st.toast; fallback to success if not
                    try:
                        st.toast("Cache cleared", icon="🗑")
                    except Exception:
                        st.success("Cache cleared")
        with colB:
            if st.button("Reset session"):
                # Clear session state safely and trigger a rerun.
                # Avoid deleting Streamlit internals by copying keys first.
                keys = list(st.session_state.keys())
                for k in keys:
                    try:
                        del st.session_state[k]
                    except Exception:
                        logger.debug("Could not delete session key: %s", k)
                try:
                    st.cache_data.clear()
                except Exception:
                    logger.debug("Could not clear cache during session reset")
                st.experimental_rerun()

    # Page routing (lazy import + friendly errors)
    module_name = pages[page_label]
    try:
        mod = import_module(module_name)
        run_fn = getattr(mod, "run", None)
        if callable(run_fn):
            run_fn()
        else:
            st.error(f"Module '{module_name}' is missing a callable run() function.")
            logger.error("Module %s missing run()", module_name)
    except ModuleNotFoundError as e:
        st.error(f"Could not find page module '{module_name}'.\n\n{e}")
        # Provide helpful diagnostics: show configured pages
        st.markdown("**Configured page modules:**")
        for label, modpath in pages.items():
            st.markdown(f"- {label}: `{modpath}`")
        logger.exception("ModuleNotFoundError importing %s", module_name)
    except Exception as e:
        # Show exception in Streamlit and log the full traceback
        st.exception(e)
        logger.exception("Unexpected exception while running page %s", module_name)

    # Optional footer
    st.markdown(
        """
        BB Log Tool — Use the Utilities to clear cache or reset session during development.
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()