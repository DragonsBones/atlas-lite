# Atlas Lite — Deferred Work

## AI Explain Feature

**What:** Wire the "Explain" panel in the right sidebar to generate a 1-2 sentence AI insight about the current chart — e.g. "Revenue peaks in Q3, driven by the Healthcare category. Consider investigating seasonal drivers."

**Why:** The placeholder is already in the UI (`st.text_area` + disabled `Explain` button). All the inputs needed for a good prompt are already available in session state: `chart_type`, `x_col`, `y_col`, `auto_info.reason`, and the aggregated data itself. The feature has no infrastructure dependencies — just an API call.

**Pros:**
- Differentiates Atlas Lite from raw charting tools
- The column profiles and chart context make it easy to write a high-signal prompt
- Foundation for the "Explain Pack" upsell tier

**Cons:**
- Requires an Anthropic API key and a secrets management story for deployment
- Needs latency/error handling: streaming preferred, fallback text for rate limits
- Prompt needs iteration to produce genuinely useful insights (not generic descriptions)

**Context:** The right panel already has a disabled `Explain` button and a placeholder text area (`app_v2.py:366-375`). The prompt should include: chart type, x/y columns, the top-N data values from `agg_bar_data()` or equivalent, and the `auto_info.reason` string if available. A Claude API call with `max_tokens=150` is sufficient for a short insight.

**Depends on:** Anthropic API key in deployment environment. Recommend using `claude-haiku-4-5-20251001` for low latency and cost. Implement as a separate `core/explain.py` module.

**Suggested prompt skeleton:**
```
You are a data analyst. Given the chart below, write 1-2 sentences of insight suitable
for a business audience. Be specific about the data pattern. Do not describe what the
chart type is — describe what the data shows.

Chart type: {chart_type}
X axis: {x_col}
Y axis: {y_col}
Top values: {top_rows_as_markdown_table}
```
