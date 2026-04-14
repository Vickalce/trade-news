from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from api.core.config import settings

st.set_page_config(page_title="Trade News Operator", layout="wide")
st.title("Trade News Operator Dashboard")
st.caption("Live events, recommendations, and audit data")

engine = create_engine(settings.database_url)

with st.sidebar:
    st.header("Filters")
    symbol_filter = st.text_input("Symbol contains", value="")
    min_conf = st.slider("Minimum confidence", min_value=0, max_value=100, value=0)
    refresh = st.button("Refresh")

if refresh:
    st.rerun()

query = """
SELECT r.id, r.symbol, r.recommendation, r.confidence, r.rationale, r.created_at_utc, n.headline
FROM recommendations r
JOIN news_events n ON n.id = r.event_id
WHERE (:symbol = '' OR r.symbol ILIKE :symbol_like)
  AND r.confidence >= :min_conf
ORDER BY r.created_at_utc DESC
LIMIT 200
"""

params = {
    "symbol": symbol_filter.strip(),
    "symbol_like": f"%{symbol_filter.strip()}%",
    "min_conf": min_conf,
}

with engine.connect() as conn:
    df = pd.read_sql(text(query), conn, params=params)

st.subheader("Recommendations")
if df.empty:
    st.info("No recommendations yet. Run POST /pipeline/ingest then POST /pipeline/run.")
else:
    df["created_at_utc"] = pd.to_datetime(df["created_at_utc"])
    st.dataframe(df, use_container_width=True)

st.subheader("Summary")
if not df.empty:
    cols = st.columns(3)
    cols[0].metric("Rows", len(df))
    cols[1].metric("Average confidence", round(float(df["confidence"].mean()), 2))
    cols[2].metric("Last update", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"))
