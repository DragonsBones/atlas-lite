# Atlas — Work Log & Roadmap

---

## Completed

- Pareto chart implemented with dual-axis, cumulative % line and 80% threshold reference line
- UI redesigned — Atlas Navy sidebar, Midas/Cicero/Archim style selector, two-column chart + Analyse layout
- Analyse panel moved to right column alongside chart
- Chart type selector moved to sidebar
- PID detection warning implemented — scans column names and cell values for identifiable data patterns
- Renamed Atlas Lite to Atlas throughout codebase
- Paywall wired up via `ATLAS_DEV_EXPORT` env var
- 32 unit tests added, all passing (38 total with Pareto tests)
- Dead code removed (old app.py, transform.py)
- Cicero theme refined to editorial style — warm background `#F4F2EE`, Atlas Navy bars, Teal accent, thin brand bar, no chart border, right-side value axis, horizontal-only gridlines
- Git repository created at DragonsBones/atlas-lite and all work pushed

---

## Known Bugs

- Cumulative % label on Pareto right axis still clipping in Cicero theme — needs 80px right margin fix
- Archim button label still slightly tight in sidebar

---

## Next Sprint Priorities

- Call NHS colleague Monday — validate Pareto usefulness, confirm whether SPC needed before adoption, check Streamlit Cloud accessible on NHS network
- Buy atlaschart.io and minerva-oa.co.uk domains
- Deploy to Streamlit Cloud with custom domain
- Post in Making Data Count NHS Futures workspace once network access confirmed
- Implement SPC chart (XmR) if NHS colleague confirms it is needed
- Wire up real Stripe payment for Export Pack unlock — replace placeholder
- Add NHS email domain verification for free tier access
- Add PID column auto-exclusion option alongside the current warning
- Fix Cumulative % label clipping in Cicero Pareto
- Add sample datasets bundled into app with "Try with sample data" button

---

## AI Explain Feature

**What:** Wire the "Explain" panel in the right column to generate a 1-2 sentence AI insight about the current chart — e.g. "Revenue peaks in Q3, driven by the Healthcare category. Consider investigating seasonal drivers."

**Why:** The placeholder is already in the UI (`st.text_area` + disabled `Explain` button in `app.py`). All inputs needed for a good prompt are available in session state: `chart_type`, `x_col`, `y_col`, `auto_info.reason`, and the aggregated data itself. No infrastructure dependencies — just an API call.

**Pros:**
- Differentiates Atlas from raw charting tools
- Column profiles and chart context make it easy to write a high-signal prompt
- Foundation for the "Explain Pack" upsell tier

**Cons:**
- Requires an Anthropic API key and a secrets management story for deployment
- Needs latency/error handling: streaming preferred, fallback text for rate limits
- Prompt needs iteration to produce genuinely useful insights (not generic descriptions)

**Depends on:** Anthropic API key in deployment environment. Recommend `claude-haiku-4-5-20251001` for low latency and cost. Implement as a separate `core/explain.py` module.

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

---

## Deferred to Studio (v2)

- Authenticated workspaces and saved charts
- React + D3 rebuild
- Database view connections for enterprise
- Word/PowerPoint direct export
