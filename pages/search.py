# pages/search.py
from __future__ import annotations

from pathlib import Path
import streamlit as st
import pandas as pd

from modules.search_utils import query_structured, query_fts


def run():
    st.set_page_config(page_title="BB Logs — Search", layout="wide")
    st.title("BB Logs — Search")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("Select DB & filters")
        # Prefer the DB just built in the Build page, but allow manual override
        default_db = st.session_state.get("search_db_path", "")
        db_path = st.text_input("DuckDB file", value=default_db, placeholder="Path to .duckdb")

        if not db_path or not Path(db_path).exists():
            st.warning("Provide a valid DuckDB file path (build one in the **Build DB** page).")
        else:
            st.success("DB found.")

            st.subheader("Structured search")
            c1, c2, c3 = st.columns(3)
            with c1:
                start_ts = st.text_input("Start timestamp", placeholder="YYYY-MM-DD HH:MM:SS")
            with c2:
                end_ts = st.text_input("End timestamp", placeholder="YYYY-MM-DD HH:MM:SS")
            with c3:
                limit = st.number_input("Max rows", min_value=100, max_value=20000, value=2000, step=100)
            u_e = st.columns(2)
            with u_e[0]:
                user_like = st.text_input("User contains", placeholder="e.g., jkelley")
            with u_e[1]:
                endpoint_like = st.text_input("Endpoint contains", placeholder="e.g., /learn/api/public/v1/")
            run_structured = st.button("Run structured search")

            st.subheader("Free‑text search (FTS)")
            fts_q = st.text_input("Query text", placeholder='e.g., "timeout OR 504"')
            run_fts = st.button("Run FTS search", disabled=(not fts_q))

    with col2:
        st.header("Results")
        results_container = st.empty()

        if db_path and Path(db_path).exists():
            if run_structured:
                with st.spinner("Querying (structured)…"):
                    df = query_structured(
                        db_path,
                        start_ts=start_ts or None,
                        end_ts=end_ts or None,
                        host_in=None,
                        user_like=user_like or None,
                        endpoint_like=endpoint_like or None,
                        include_noisy=False,
                        limit=int(limit),
                    )
                if df.empty:
                    results_container.info("No matches.")
                else:
                    results_container.dataframe(df, use_container_width=True, height=520)

            if run_fts and fts_q:
                with st.spinner("Searching text (FTS)…"):
                    df = query_fts(db_path, fts_q, limit=2000)
                if df.empty:
                    results_container.info("No matches.")
                else:
                    results_container.dataframe(df, use_container_width=True, height=520)
