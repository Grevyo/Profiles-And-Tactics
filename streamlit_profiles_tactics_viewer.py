"""Streamlit app for viewing Profiles and Tactics data.

Run:
    streamlit run streamlit_profiles_tactics_viewer.py
"""

from __future__ import annotations

import json
from io import StringIO
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Profiles and Tactics Viewer", layout="wide")


EXAMPLE_DATA: dict[str, Any] = {
    "profiles": [
        {
            "id": "P-001",
            "name": "Balanced Growth",
            "risk_level": "Moderate",
            "description": "Diversified portfolio targeting long-term growth.",
        },
        {
            "id": "P-002",
            "name": "Capital Preservation",
            "risk_level": "Low",
            "description": "Lower volatility allocation with defensive bias.",
        },
    ],
    "tactics": [
        {
            "id": "T-101",
            "name": "Momentum Tilt",
            "category": "Equities",
            "description": "Increase exposure to assets with positive relative strength.",
            "profile_id": "P-001",
        },
        {
            "id": "T-102",
            "name": "Duration Hedge",
            "category": "Fixed Income",
            "description": "Use short-duration positions when rate risk rises.",
            "profile_id": "P-002",
        },
    ],
}


def _normalize_records(records: Any, key_name: str) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    if not isinstance(records, list):
        st.warning(f"`{key_name}` should be a list of objects. Received {type(records).__name__}.")
        return pd.DataFrame()

    try:
        return pd.json_normalize(records)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to read `{key_name}` records: {exc}")
        return pd.DataFrame()


def _load_json_from_upload(uploaded_file: Any) -> dict[str, Any] | None:
    if uploaded_file is None:
        return None

    try:
        raw = uploaded_file.read()
        text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        return json.loads(text)
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON file: {exc}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not read uploaded file: {exc}")
    return None


def _load_json_from_text(text: str) -> dict[str, Any] | None:
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        st.error(f"JSON in text box is invalid: {exc}")
        return None


def _render_table(title: str, df: pd.DataFrame) -> None:
    st.subheader(title)
    if df.empty:
        st.info(f"No data found for {title}.")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)

    csv = df.to_csv(index=False)
    st.download_button(
        label=f"Download {title} CSV",
        data=StringIO(csv).getvalue(),
        file_name=f"{title.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )


def main() -> None:
    st.title("Profiles and Tactics Viewer")
    st.caption(
        "Upload JSON (or paste JSON) with keys `profiles` and `tactics` to explore records."
    )

    with st.sidebar:
        st.header("Data Input")
        uploaded_json = st.file_uploader("Upload JSON file", type=["json"])
        pasted_json = st.text_area(
            "Or paste JSON",
            height=220,
            placeholder='{"profiles": [...], "tactics": [...]}',
        )
        use_example = st.checkbox("Use built-in example data", value=not uploaded_json and not pasted_json)

    data: dict[str, Any] | None = None
    if uploaded_json:
        data = _load_json_from_upload(uploaded_json)
    elif pasted_json.strip():
        data = _load_json_from_text(pasted_json)

    if data is None and use_example:
        data = EXAMPLE_DATA

    if data is None:
        st.warning("No valid data loaded yet. Upload JSON, paste JSON, or enable example data.")
        st.stop()

    profiles_df = _normalize_records(data.get("profiles", []), "profiles")
    tactics_df = _normalize_records(data.get("tactics", []), "tactics")

    tab_profiles, tab_tactics, tab_relation = st.tabs(["Profiles", "Tactics", "Mapping"])

    with tab_profiles:
        _render_table("Profiles", profiles_df)

    with tab_tactics:
        _render_table("Tactics", tactics_df)

    with tab_relation:
        st.subheader("Tactics by Profile")
        if profiles_df.empty or tactics_df.empty:
            st.info("Need both profiles and tactics to show mapping.")
        else:
            left_key = "id" if "id" in profiles_df.columns else profiles_df.columns[0]
            right_key = "profile_id" if "profile_id" in tactics_df.columns else None

            if not right_key:
                st.warning("No `profile_id` column found in tactics data.")
            else:
                merged = tactics_df.merge(
                    profiles_df,
                    how="left",
                    left_on=right_key,
                    right_on=left_key,
                    suffixes=("_tactic", "_profile"),
                )
                st.dataframe(merged, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
