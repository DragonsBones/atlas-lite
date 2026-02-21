import altair as alt
import pandas as pd

# ------------------------------------
# Shared styling config
# ------------------------------------

def _base_config(chart: alt.Chart) -> alt.Chart:
    return (
        chart
        .configure_view(stroke=None)
        .configure_axis(
            labelFontSize=12,
            titleFontSize=12,
            gridOpacity=0.15,
            tickSize=0,
            domain=False,
        )
    )

# ------------------------------------
# Bar Chart
# ------------------------------------

def bar_chart(
    df,
    x_col,
    y_col,
    top_n=25,
    show_labels=True,
    sort_desc=True,
    as_rate=False
) -> alt.Chart:

    d = df[[x_col, y_col]].dropna()

    agg = d.groupby(x_col, as_index=False)[y_col].sum()

    if as_rate:
        total = agg[y_col].sum()
        if total > 0:
            agg[y_col] = (agg[y_col] / total) * 100

    agg = agg.sort_values(y_col, ascending=not sort_desc).head(top_n)

    value_format = ".1f" if as_rate else ",.0f"

    base = alt.Chart(agg).encode(
        y=alt.Y(f"{x_col}:N", sort="-x", title=None),
        x=alt.X(
            f"{y_col}:Q",
            title=None,
            axis=alt.Axis(format=value_format),
        ),
        tooltip=[
            alt.Tooltip(f"{x_col}:N", title=x_col),
            alt.Tooltip(f"{y_col}:Q", title=y_col, format=value_format),
        ],
    )

    bars = base.mark_bar(color="#1f4e79", size=18)

    chart = bars

    if show_labels:
        labels = base.mark_text(
            align="left",
            baseline="middle",
            dx=3,
        ).encode(
            text=alt.Text(f"{y_col}:Q", format=value_format)
        )
        chart = alt.layer(bars, labels)

    row_height = 20
    max_height = 440
    calculated_height = row_height * len(agg) + 40
    chart_height = min(calculated_height, max_height)

    chart = chart.properties(height=chart_height)

    return _base_config(chart)

# ------------------------------------
# Line Chart
# ------------------------------------

def line_chart(df, x_col, y_col) -> alt.Chart:
    d = df[[x_col, y_col]].dropna()

    # Attempt datetime parsing
    if d[x_col].dtype == "object":
        d = d.copy()
        parsed = pd.to_datetime(d[x_col], errors="coerce")
        if parsed.notna().mean() > 0.7:  # at least 70% parseable
            d[x_col] = parsed
            x_type = "T"
        else:
            x_type = "Q" if pd.api.types.is_numeric_dtype(d[x_col]) else "N"
    elif pd.api.types.is_datetime64_any_dtype(d[x_col]):
        x_type = "T"
    elif pd.api.types.is_numeric_dtype(d[x_col]):
        x_type = "Q"
    else:
        x_type = "N"

    chart = (
        alt.Chart(d)
        .mark_line(color="#1f4e79", strokeWidth=2)
        .encode(
            x=alt.X(f"{x_col}:{x_type}", title=None),
            y=alt.Y(f"{y_col}:Q", title=None),
            tooltip=[x_col, y_col],
        )
        .properties(height=420)
    )

    return _base_config(chart)
# ------------------------------------
# Scatter Chart
# ------------------------------------

def scatter_chart(df, x_col, y_col) -> alt.Chart:
    d = df[[x_col, y_col]].dropna()

    chart = (
        alt.Chart(d)
        .mark_circle(size=70, opacity=0.7, color="#1f4e79")
        .encode(
            x=alt.X(f"{x_col}:Q", title=None),
            y=alt.Y(f"{y_col}:Q", title=None),
            tooltip=[x_col, y_col],
        )
        .properties(height=420)
    )

    return _base_config(chart)

# ------------------------------------
# Histogram
# ------------------------------------

def histogram(df, x_col, bins=30) -> alt.Chart:
    d = df[[x_col]].dropna()

    chart = (
        alt.Chart(d)
        .mark_bar(color="#1f4e79")
        .encode(
            x=alt.X(f"{x_col}:Q", bin=alt.Bin(maxbins=bins), title=None),
            y=alt.Y("count():Q", title=None),
            tooltip=[alt.Tooltip("count():Q", title="Count")],
        )
        .properties(height=420)
    )

    return _base_config(chart)