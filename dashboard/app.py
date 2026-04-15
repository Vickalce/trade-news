from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

from api.core.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
BRANDING_DIR = BASE_DIR / "docs" / "branding" / "logos"
LOGO_DARK_PATH = BRANDING_DIR / "trade-news-logo-primary-dark.svg"
ICON_PATH = BRANDING_DIR / "trade-news-icon-option-2.svg"

page_icon = "TN"
if ICON_PATH.exists():
    page_icon = ICON_PATH.read_bytes()

st.set_page_config(page_title="Trade News", page_icon=page_icon, layout="wide")

engine = create_engine(settings.database_url)


@st.cache_data(ttl=20)
def load_recommendations(symbol_filter: str, min_confidence: int, limit: int) -> pd.DataFrame:
    query = text(
        """
        SELECT
            r.id,
            r.event_id,
            r.symbol,
            r.recommendation,
            r.confidence,
            r.rationale,
            r.invalidation_conditions,
            r.created_at_utc,
            n.headline,
            n.source,
            n.category,
            n.url,
            n.has_been_scored,
            s.final_score,
            s.relevance_score,
            s.reaction_score,
            s.historical_similarity_score,
            s.source_quality_score,
            s.scope_type,
            s.impact_horizon
        FROM recommendations r
        JOIN news_events n ON n.id = r.event_id
        LEFT JOIN event_scores s ON s.event_id = r.event_id
        WHERE (:symbol = '' OR LOWER(r.symbol) LIKE :symbol_like)
          AND r.confidence >= :min_confidence
        ORDER BY r.created_at_utc DESC
        LIMIT :limit
        """
    )
    params = {
        "symbol": symbol_filter.strip().lower(),
        "symbol_like": f"%{symbol_filter.strip().lower()}%",
        "min_confidence": min_confidence,
        "limit": limit,
    }
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params=params)
    if not df.empty:
        df["created_at_utc"] = pd.to_datetime(df["created_at_utc"], errors="coerce", utc=True)
        numeric_columns = [
            "confidence",
            "final_score",
            "relevance_score",
            "reaction_score",
            "historical_similarity_score",
            "source_quality_score",
        ]
        for column in numeric_columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df


@st.cache_data(ttl=20)
def load_alert_rollup(limit: int = 300) -> pd.DataFrame:
    query = text(
        """
        SELECT
            recommendation_id,
            alert_channel,
            priority,
            delivery_status,
            delivered_at_utc
        FROM alert_log
        ORDER BY delivered_at_utc DESC
        LIMIT :limit
        """
    )
    with engine.connect() as conn:
        alerts = pd.read_sql(query, conn, params={"limit": limit})
    if alerts.empty:
        return alerts
    alerts["delivered_at_utc"] = pd.to_datetime(alerts["delivered_at_utc"], errors="coerce", utc=True)
    alerts["channel_status"] = alerts["alert_channel"].fillna("unknown") + ": " + alerts["delivery_status"].fillna("unknown")
    return (
        alerts.groupby("recommendation_id", as_index=False)
        .agg(
            latest_delivery=("delivered_at_utc", "max"),
            priority=("priority", "first"),
            alert_summary=("channel_status", lambda values: " | ".join(dict.fromkeys(values))),
        )
    )


@st.cache_data(ttl=20)
def load_provider_catalog(api_base_url: str, api_key: str) -> tuple[dict | None, str | None]:
    endpoint = f"{api_base_url.rstrip('/')}/providers"
    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key

    try:
        with httpx.Client(timeout=4.0) as client:
            response = client.get(endpoint, headers=headers)
        if response.status_code != 200:
            return None, f"Provider API returned {response.status_code}."
        payload = response.json()
        if not isinstance(payload, dict):
            return None, "Provider API response was not a JSON object."
        return payload, None
    except Exception as exc:
        return None, f"Could not reach provider API: {exc}"


def build_env_snippet(kind: str, provider_key: str, config_keys: list[str]) -> str:
    lines: list[str] = []

    if kind == "news":
        lines.append(f"NEWS_PROVIDER={provider_key}")
    elif kind == "market_data":
        lines.append(f"MARKET_DATA_PROVIDER={provider_key}")
    elif kind == "execution":
        lines.append(f"BROKER_PROVIDER={provider_key}")

    for key in config_keys:
        env_key = key.upper()
        if env_key == "ALPACA_BASE_URL":
            lines.append("ALPACA_BASE_URL=https://paper-api.alpaca.markets/v2")
        elif env_key == "FINNHUB_BASE_URL":
            lines.append("FINNHUB_BASE_URL=https://finnhub.io/api/v1")
        elif env_key == "FINNHUB_NEWS_CATEGORY":
            lines.append("FINNHUB_NEWS_CATEGORY=general")
        elif env_key == "SCHWAB_OAUTH_AUTHORIZE_URL":
            lines.append("SCHWAB_OAUTH_AUTHORIZE_URL=https://api.schwabapi.com/v1/oauth/authorize")
        elif env_key == "SCHWAB_OAUTH_TOKEN_URL":
            lines.append("SCHWAB_OAUTH_TOKEN_URL=https://api.schwabapi.com/v1/oauth/token")
        else:
            lines.append(f"{env_key}=")

    return "\n".join(lines)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

        :root {
            --brand-navy: #22324a;
            --brand-teal: #1f7a86;
            --brand-mint: #2bd28a;
            --brand-red: #f06a78;
            --ink: #0f1723;
            --ink-soft: #43556e;
            --panel-border: rgba(125, 154, 179, 0.24);
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(43, 210, 138, 0.14), transparent 26%),
                radial-gradient(circle at 88% 10%, rgba(31, 122, 134, 0.18), transparent 24%),
                linear-gradient(160deg, #07111f 0%, #10243b 44%, #18334c 100%);
            color: #eff4fb;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(10, 22, 38, 0.96), rgba(16, 36, 58, 0.92));
            border-right: 1px solid rgba(142, 174, 197, 0.2);
        }

        [data-testid="stSidebar"] * {
            color: #f3f7fc;
            font-family: 'IBM Plex Sans', sans-serif;
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        h1, h2, h3 {
            font-family: 'Space Grotesk', sans-serif;
            letter-spacing: -0.03em;
        }

        p, div, span, label {
            font-family: 'IBM Plex Sans', sans-serif;
        }

        .hero-shell {
            padding: 1.6rem 1.8rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 28px;
            background: linear-gradient(145deg, rgba(12, 27, 44, 0.92), rgba(20, 47, 71, 0.82));
            box-shadow: 0 30px 80px rgba(0, 0, 0, 0.28);
            margin-bottom: 1.1rem;
        }

        .brand-banner {
            margin-bottom: 1rem;
            padding: 0.9rem 1rem;
            border-radius: 20px;
            border: 1px solid rgba(186, 212, 232, 0.22);
            background: linear-gradient(145deg, rgba(12, 28, 44, 0.9), rgba(17, 38, 60, 0.86));
        }

        .brand-note {
            color: rgba(225, 239, 248, 0.78);
            font-size: 0.9rem;
            margin-top: 0.45rem;
            letter-spacing: 0.01em;
        }

        .hero-kicker {
            display: inline-block;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(43, 210, 138, 0.16);
            color: #d6fff0;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 700;
            margin-bottom: 0.9rem;
        }

        .hero-grid {
            display: grid;
            grid-template-columns: 2.2fr 1fr;
            gap: 1rem;
            align-items: end;
        }

        .hero-title {
            font-size: clamp(2.2rem, 4vw, 4.3rem);
            line-height: 0.96;
            margin: 0;
            color: #fbfdff;
        }

        .hero-copy {
            margin-top: 0.9rem;
            max-width: 52rem;
            font-size: 1rem;
            color: rgba(232, 240, 249, 0.76);
        }

        .hero-chip-row {
            display: flex;
            gap: 0.55rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }

        .hero-chip {
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: #f4f7fb;
            font-size: 0.85rem;
        }

        .hero-panel {
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
            border: 1px solid rgba(255,255,255,0.08);
            padding: 1rem;
        }

        .hero-panel-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: rgba(216, 228, 242, 0.62);
            margin-bottom: 0.45rem;
        }

        .hero-panel-value {
            font-size: 2rem;
            font-weight: 700;
            color: #fffdf8;
        }

        .metric-card {
            background: rgba(247, 250, 253, 0.97);
            border: 1px solid var(--panel-border);
            border-radius: 22px;
            padding: 1rem 1.05rem;
            box-shadow: 0 18px 48px rgba(6, 13, 24, 0.16);
            min-height: 8rem;
        }

        .metric-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #6f819a;
            margin-bottom: 0.6rem;
        }

        .metric-value {
            color: var(--ink);
            font-weight: 700;
            font-size: 2rem;
            line-height: 1;
            margin-bottom: 0.35rem;
        }

        .metric-meta {
            color: var(--ink-soft);
            font-size: 0.92rem;
        }

        .section-card {
            background: rgba(247, 250, 253, 0.97);
            border: 1px solid var(--panel-border);
            border-radius: 24px;
            padding: 1.15rem;
            box-shadow: 0 18px 48px rgba(6, 13, 24, 0.16);
            margin-bottom: 1rem;
        }

        .section-title {
            color: var(--ink);
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }

        .section-copy {
            color: var(--ink-soft);
            font-size: 0.95rem;
            margin-bottom: 0.9rem;
        }

        .feed-card {
            background: linear-gradient(180deg, #ffffff, #f5f8fc);
            border: 1px solid var(--panel-border);
            border-radius: 18px;
            padding: 0.95rem;
            margin-bottom: 0.3rem;
        }

        .feed-meta {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            color: #607089;
            font-size: 0.8rem;
            margin-bottom: 0.45rem;
        }

        .feed-symbol {
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            color: #0c1728;
            font-size: 1.2rem;
        }

        .feed-headline {
            color: #203149;
            font-size: 0.95rem;
            margin-top: 0.35rem;
            margin-bottom: 0.65rem;
        }

        .pill-row {
            display: flex;
            gap: 0.45rem;
            flex-wrap: wrap;
        }

        .tone-pill {
            display: inline-block;
            padding: 0.32rem 0.68rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .tone-buy {
            background: rgba(22, 163, 74, 0.12);
            color: #166534;
        }

        .tone-sell {
            background: rgba(220, 38, 38, 0.12);
            color: #991b1b;
        }

        .tone-hold {
            background: rgba(217, 119, 6, 0.14);
            color: #92400e;
        }

        .tone-neutral {
            background: rgba(99, 116, 138, 0.12);
            color: #516072;
        }

        .detail-shell {
            background: linear-gradient(180deg, #ffffff, #f7f9fc);
            border: 1px solid var(--panel-border);
            border-radius: 24px;
            padding: 1.2rem;
        }

        .detail-headline {
            color: #0a1322;
            font-size: 1.55rem;
            line-height: 1.15;
            margin-bottom: 0.7rem;
        }

        .detail-label {
            color: #687a92;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            margin-bottom: 0.3rem;
        }

        .detail-value {
            color: #0d1728;
            font-size: 0.98rem;
            margin-bottom: 0.9rem;
        }

        .score-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.8rem;
            margin-top: 0.8rem;
        }

        .score-box {
            background: #f1f5f9;
            border-radius: 16px;
            padding: 0.9rem;
            border: 1px solid rgba(129, 152, 179, 0.18);
        }

        .score-name {
            font-size: 0.8rem;
            color: #627389;
            margin-bottom: 0.25rem;
        }

        .score-value {
            font-size: 1.4rem;
            color: #0a1425;
            font-weight: 700;
        }

        .empty-shell {
            padding: 2rem 1.4rem;
            border-radius: 24px;
            background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(245,248,252,0.96));
            border: 1px solid var(--panel-border);
            color: #17304f;
        }

        .empty-shell h3 {
            margin-top: 0;
            margin-bottom: 0.65rem;
            color: #08111f;
        }

        @media (max-width: 1100px) {
            .hero-grid,
            .score-grid {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def tone_class(recommendation: str) -> str:
    if recommendation == "buy_candidate":
        return "tone-buy"
    if recommendation == "sell_candidate":
        return "tone-sell"
    if recommendation == "hold":
        return "tone-hold"
    return "tone-neutral"


def format_recommendation(value: str) -> str:
    mapping = {
        "buy_candidate": "Buy Candidate",
        "sell_candidate": "Sell Candidate",
        "hold": "Hold",
    }
    return mapping.get(value, value.replace("_", " ").title())


def metric_text(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "0.0"
    return f"{float(value):.1f}"


def format_timestamp(value: pd.Timestamp | None) -> str:
    if value is None or pd.isna(value):
        return "No timestamp"
    return value.tz_convert(timezone.utc).strftime("%b %d, %Y %H:%M UTC")


def render_metric_card(label: str, value: str, meta: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-meta">{meta}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_feed_card(row: dict[str, object], selected: bool) -> str:
    selected_border = "2px solid #ff7a18" if selected else "1px solid rgba(129, 152, 179, 0.22)"
    return f"""
        <div class="feed-card" style="border:{selected_border};">
            <div class="feed-meta">
                <span>{row.get('source') or 'Unknown source'}</span>
                <span>{format_timestamp(row.get('created_at_utc'))}</span>
            </div>
            <div class="feed-symbol">{row.get('symbol')}</div>
            <div class="feed-headline">{row.get('headline')}</div>
            <div class="pill-row">
                <span class="tone-pill {tone_class(str(row.get('recommendation')))}">{format_recommendation(str(row.get('recommendation')))}</span>
                <span class="tone-pill tone-neutral">Confidence {metric_text(row.get('confidence'))}</span>
                <span class="tone-pill tone-neutral">Score {metric_text(row.get('final_score'))}</span>
            </div>
        </div>
    """


def render_empty_state() -> None:
    st.markdown(
        """
        <div class="empty-shell">
            <h3>Trade News is ready. It just needs live flow.</h3>
            <p>The interface is set up as a command center: signal feed on the left, explanation panel on the right, and paper-execution metrics across the top.</p>
            <p>To populate it, run the pipeline in order:</p>
            <p><strong>1.</strong> POST /pipeline/ingest<br><strong>2.</strong> POST /pipeline/run<br><strong>3.</strong> Refresh this page</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


inject_styles()

with st.sidebar:
    if ICON_PATH.exists():
        st.image(str(ICON_PATH), width=82)
    st.markdown("## Trade News")
    st.caption("Signal console for explainable news-driven trading")
    symbol_filter = st.text_input("Filter symbol", value="", placeholder="AAPL, NVDA, XLE")
    min_confidence = st.slider("Minimum confidence", min_value=0, max_value=100, value=40)
    row_limit = st.slider("Signals to load", min_value=10, max_value=200, value=60, step=10)
    provider_api_base_url = st.text_input("Provider API base URL", value="http://localhost:8000")
    refresh = st.button("Refresh feed", use_container_width=True)
    st.divider()
    st.markdown("### Launch mode")
    st.markdown("- Manual decision support first")
    st.markdown("- Paper trading before live execution")
    st.markdown("- Schwab auth pending approval")

    st.divider()
    st.markdown("### Provider settings")
    provider_catalog, provider_catalog_error = load_provider_catalog(provider_api_base_url, settings.api_key)
    if provider_catalog_error:
        st.caption(provider_catalog_error)
        st.caption("Start the FastAPI server to load provider metadata from /providers.")
    else:
        selected = provider_catalog.get("selected", {})
        providers_by_kind = provider_catalog.get("providers", {})

        for kind, label in (("news", "News"), ("market_data", "Market Data"), ("execution", "Execution")):
            selected_key = str(selected.get(kind) or "unset")
            options = providers_by_kind.get(kind) or []

            selected_entry = None
            for option in options:
                if str(option.get("key", "")).lower() == selected_key.lower():
                    selected_entry = option
                    break

            configured_text = "configured"
            if selected_entry is not None and not bool(selected_entry.get("configured")):
                configured_text = "needs credentials"

            st.markdown(f"**{label}:** {selected_key}")
            st.caption(f"{len(options)} options | selected provider is {configured_text}")

        with st.expander("Supported providers", expanded=False):
            for kind, label in (("news", "News"), ("market_data", "Market Data"), ("execution", "Execution")):
                st.markdown(f"**{label}**")
                for option in providers_by_kind.get(kind) or []:
                    key = option.get("key", "unknown")
                    configured = "configured" if option.get("configured") else "missing credentials"
                    auth_type = option.get("capabilities", {}).get("auth_type", "unknown")
                    st.markdown(f"- {key} | {configured} | auth: {auth_type}")

        with st.expander("Setup helper", expanded=False):
            kind_options = {
                "News": "news",
                "Market Data": "market_data",
                "Execution": "execution",
            }
            selected_kind_label = st.selectbox("Provider type", options=list(kind_options.keys()), key="setup_kind")
            selected_kind = kind_options[selected_kind_label]

            options_for_kind = providers_by_kind.get(selected_kind) or []
            if not options_for_kind:
                st.caption("No providers found for the selected type.")
            else:
                option_labels = [str(item.get("key") or "unknown") for item in options_for_kind]
                default_key = str(selected.get(selected_kind) or option_labels[0])
                default_index = option_labels.index(default_key) if default_key in option_labels else 0
                chosen_key = st.selectbox("Provider", options=option_labels, index=default_index, key="setup_provider")

                chosen_entry = next(item for item in options_for_kind if str(item.get("key")) == chosen_key)
                config_keys = [str(value) for value in (chosen_entry.get("config_keys") or [])]
                env_snippet = build_env_snippet(selected_kind, chosen_key, config_keys)

                st.caption("Copy these lines into your .env file")
                st.code(env_snippet, language="bash")

                if config_keys:
                    st.caption("Required credential keys")
                    st.markdown("\n".join([f"- {key.upper()}" for key in config_keys]))
                else:
                    st.caption("No extra credentials required for this provider.")

if refresh:
    st.cache_data.clear()
    st.rerun()

recommendations = load_recommendations(symbol_filter, min_confidence, row_limit)
alerts = load_alert_rollup()
if not recommendations.empty and not alerts.empty:
    recommendations = recommendations.merge(alerts, how="left", left_on="id", right_on="recommendation_id")

latest_timestamp = "No signals yet"
if not recommendations.empty:
    latest_timestamp = format_timestamp(recommendations["created_at_utc"].max())

st.markdown('<div class="brand-banner">', unsafe_allow_html=True)
if LOGO_DARK_PATH.exists():
    st.image(str(LOGO_DARK_PATH), use_container_width=True)
else:
    st.markdown("### Trade News")
st.markdown(
    '<div class="brand-note">Option 2 identity applied: TN monogram, market-candle motif, and matching dashboard palette.</div>',
    unsafe_allow_html=True,
)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="hero-shell">
        <div class="hero-kicker">News-to-signal launch view</div>
        <div class="hero-grid">
            <div>
                <h1 class="hero-title">Trade News</h1>
                <div class="hero-copy">A live command center for turning breaking headlines into explainable trade ideas, with signal confidence, reason tracing, and paper-execution guardrails in one screen.</div>
                <div class="hero-chip-row">
                    <span class="hero-chip">Live signal feed</span>
                    <span class="hero-chip">Explainable rationale</span>
                    <span class="hero-chip">Paper-trading workflow</span>
                </div>
            </div>
            <div class="hero-panel">
                <div class="hero-panel-label">Latest signal timestamp</div>
                <div class="hero-panel-value">{latest_timestamp}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_columns = st.columns(4)
if recommendations.empty:
    metrics = [
        ("Signals loaded", "0", "Run the ingestion and scoring pipeline"),
        ("Average confidence", "0.0", "Will update as recommendations arrive"),
        ("High-priority ideas", "0", "No active signals"),
        ("Unique symbols", "0", "Watchlist will appear here"),
    ]
else:
    high_priority_count = int((recommendations["confidence"] >= 75).sum())
    unique_symbols = int(recommendations["symbol"].nunique())
    metrics = [
        ("Signals loaded", str(len(recommendations)), f"Filtered at {min_confidence}+ confidence"),
        ("Average confidence", f"{recommendations['confidence'].mean():.1f}", "Across current signal feed"),
        ("High-priority ideas", str(high_priority_count), "Confidence at or above 75"),
        ("Unique symbols", str(unique_symbols), "Distinct names in the current stream"),
    ]

for column, metric in zip(metric_columns, metrics):
    with column:
        render_metric_card(*metric)

if recommendations.empty:
    render_empty_state()
else:
    if "selected_recommendation_id" not in st.session_state:
        st.session_state.selected_recommendation_id = int(recommendations.iloc[0]["id"])

    available_ids = recommendations["id"].astype(int).tolist()
    if st.session_state.selected_recommendation_id not in available_ids:
        st.session_state.selected_recommendation_id = available_ids[0]

    left_column, right_column = st.columns([1.1, 1.2], gap="large")

    with left_column:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Signal Feed</div>
                <div class="section-copy">Scan the newest recommendations, then drill into one for the full reasoning chain.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for row in recommendations.to_dict(orient="records"):
            recommendation_id = int(row["id"])
            selected = st.session_state.selected_recommendation_id == recommendation_id
            st.markdown(render_feed_card(row, selected), unsafe_allow_html=True)
            button_label = "Open detail" if not selected else "Selected"
            if st.button(button_label, key=f"select_{recommendation_id}", use_container_width=True):
                st.session_state.selected_recommendation_id = recommendation_id
                st.rerun()

    selected = recommendations.loc[recommendations["id"] == st.session_state.selected_recommendation_id].iloc[0]
    alert_summary = selected.get("alert_summary") or "No alert delivery logged yet"
    with right_column:
        st.markdown(
            f"""
            <div class="detail-shell">
                <div class="pill-row" style="margin-bottom:0.9rem;">
                    <span class="tone-pill {tone_class(selected['recommendation'])}">{format_recommendation(selected['recommendation'])}</span>
                    <span class="tone-pill tone-neutral">{selected['symbol']}</span>
                    <span class="tone-pill tone-neutral">Confidence {selected['confidence']:.1f}</span>
                </div>
                <div class="detail-headline">{selected['headline']}</div>
                <div class="detail-label">Why this fired</div>
                <div class="detail-value">{selected['rationale']}</div>
                <div class="detail-label">Invalidation</div>
                <div class="detail-value">{selected['invalidation_conditions'] or 'No explicit invalidation recorded yet.'}</div>
                <div class="score-grid">
                    <div class="score-box"><div class="score-name">Final score</div><div class="score-value">{metric_text(selected['final_score'])}</div></div>
                    <div class="score-box"><div class="score-name">Reaction score</div><div class="score-value">{metric_text(selected['reaction_score'])}</div></div>
                    <div class="score-box"><div class="score-name">Relevance score</div><div class="score-value">{metric_text(selected['relevance_score'])}</div></div>
                    <div class="score-box"><div class="score-name">Source quality</div><div class="score-value">{metric_text(selected['source_quality_score'])}</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        meta_columns = st.columns(3)
        meta_columns[0].metric("Scope", str(selected.get("scope_type") or "unknown").title())
        meta_columns[1].metric("Horizon", str(selected.get("impact_horizon") or "unknown").title())
        meta_columns[2].metric("Category", str(selected.get("category") or "other").title())

        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Execution Readiness</div>
                <div class="section-copy">This panel is designed for paper trading first. It gives the operator enough detail to decide whether a recommendation deserves review, preview, or suppression.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        detail_columns = st.columns(2)
        with detail_columns[0]:
            st.markdown(f"**Source:** {selected['source'] or 'Unknown'}")
            st.markdown(f"**Generated:** {format_timestamp(selected['created_at_utc'])}")
            st.markdown(f"**Event scored:** {'Yes' if bool(selected['has_been_scored']) else 'No'}")
            if selected.get("url"):
                st.markdown(f"**Headline URL:** {selected['url']}")
        with detail_columns[1]:
            st.markdown(f"**Alert delivery:** {alert_summary}")
            st.markdown(f"**Priority:** {selected.get('priority') or 'Not logged'}")
            latest_delivery = selected.get("latest_delivery")
            if pd.notna(latest_delivery):
                st.markdown(f"**Last alert:** {format_timestamp(latest_delivery)}")
            else:
                st.markdown("**Last alert:** No delivery record")

        display_table = recommendations[
            [
                "symbol",
                "recommendation",
                "confidence",
                "final_score",
                "source",
                "category",
                "created_at_utc",
            ]
        ].copy()
        display_table["recommendation"] = display_table["recommendation"].map(format_recommendation)
        display_table["created_at_utc"] = display_table["created_at_utc"].dt.strftime("%Y-%m-%d %H:%M UTC")

        with st.expander("Full signal table", expanded=False):
            st.dataframe(display_table, use_container_width=True, hide_index=True)

st.caption(
    f"Rendered at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Database: {settings.database_url}"
)
