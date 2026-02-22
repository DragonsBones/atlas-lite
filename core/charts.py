import altair as alt
import pandas as pd

from core.themes import AtlasStyle, MIDAS


# ------------------------------------
# Style application
# ------------------------------------

CHART_WIDTH = 560

def _apply_style(chart: alt.Chart, style: AtlasStyle) -> alt.Chart:
    lbl_color = style.axis_label_color or style.text_secondary
    ttl_color = style.axis_title_color or style.text_secondary
    x_lbl = style.axis_x_label_color or lbl_color
    y_lbl = style.axis_y_label_color or lbl_color
    return (
        chart
        .configure(
            padding={"left": 24, "right": 72, "top": 20, "bottom": 16},
            background=style.bg_page,
        )
        .configure_view(stroke=None, fill=style.bg_page)
        .configure_axis(
            labelFontSize=11,
            titleFontSize=11,
            labelColor=lbl_color,
            titleColor=ttl_color,
            gridColor=style.gridline_color,
            gridOpacity=style.grid_opacity,
            gridWidth=style.grid_stroke_width,
            tickSize=0,
            domain=style.axis_domain,
            labelLimit=220,
        )
        .configure_axisX(labelColor=x_lbl, titleColor=ttl_color, labelFontSize=10)
        .configure_axisY(labelColor=y_lbl, labelFontSize=11)
        .configure_title(
            fontSize=13,
            fontWeight=700,
            color=style.text_primary,
            subtitleFontSize=10,
            subtitleColor=style.text_secondary,
            subtitleFontWeight=400,
            anchor="start",
            offset=12,
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
    as_rate=False,
    style: AtlasStyle = MIDAS,
    chart_title: str = "",
) -> alt.Chart:

    d = df[[x_col, y_col]].dropna()

    agg = d.groupby(x_col, as_index=False)[y_col].sum()

    if as_rate:
        total = agg[y_col].sum()
        if total > 0:
            agg[y_col] = (agg[y_col] / total) * 100

    # Always take the top-N highest-value rows; sort_desc only controls display order
    agg = agg.sort_values(y_col, ascending=False).head(top_n)

    value_format = ".1f" if as_rate else ",.0f"
    x_axis_title = "% of total" if as_rate else None
    primary = style.data_palette[0]
    x_max = agg[y_col].max() * 1.05  # 5% headroom so longest bar never touches boundary
    # sort_desc=True  → bars ordered by value descending (highest at top)
    # sort_desc=False → bars ordered alphabetically (A→Z / 0→9)
    y_sort = "-x" if sort_desc else "ascending"

    base = alt.Chart(agg).encode(
        y=alt.Y(f"{x_col}:N", sort=y_sort, title=None, scale=alt.Scale(paddingInner=0.40)),
        x=alt.X(
            f"{y_col}:Q",
            title=x_axis_title,
            axis=alt.Axis(format=value_format, tickCount=5),
            scale=alt.Scale(domain=[0, x_max]),
        ),
        tooltip=[
            alt.Tooltip(f"{x_col}:N", title=x_col),
            alt.Tooltip(f"{y_col}:Q", title=y_col, format=value_format),
        ],
    )

    bars = base.mark_bar(
        color=primary,
        size=10,
        cornerRadiusEnd=style.bar_corner_radius,
    )

    chart = bars

    if show_labels:
        labels = base.mark_text(
            align="left",
            baseline="middle",
            dx=5,
            fontSize=11,
            color=style.text_primary,
        ).encode(
            text=alt.Text(f"{y_col}:Q", format=value_format)
        )
        chart = alt.layer(bars, labels)

    row_height = 30
    max_height = 480
    calculated_height = row_height * len(agg) + 40
    chart_height = min(calculated_height, max_height)

    props = {"width": CHART_WIDTH, "height": chart_height}
    if chart_title:
        props["title"] = alt.TitleParams(text=chart_title)
    chart = chart.properties(**props)

    return _apply_style(chart, style)


# ------------------------------------
# Line Chart
# ------------------------------------

def line_chart(df, x_col, y_col, style: AtlasStyle = MIDAS, chart_title: str = "") -> alt.Chart:
    d = df[[x_col, y_col]].dropna()

    # Attempt datetime parsing
    if d[x_col].dtype == "object":
        d = d.copy()
        parsed = pd.to_datetime(d[x_col], errors="coerce")
        if parsed.notna().mean() > 0.7:
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

    props = {"width": CHART_WIDTH, "height": 300}
    if chart_title:
        props["title"] = alt.TitleParams(text=chart_title)
    chart = (
        alt.Chart(d)
        .mark_line(color=style.data_palette[0], strokeWidth=style.line_width)
        .encode(
            x=alt.X(f"{x_col}:{x_type}", title=None),
            y=alt.Y(f"{y_col}:Q", title=None),
            tooltip=[x_col, y_col],
        )
        .properties(**props)
    )

    return _apply_style(chart, style)


# ------------------------------------
# Scatter Chart
# ------------------------------------

def scatter_chart(df, x_col, y_col, style: AtlasStyle = MIDAS, chart_title: str = "") -> alt.Chart:
    if x_col == y_col:
        raise ValueError("Scatter requires X and Y to be different columns.")

    if not pd.api.types.is_numeric_dtype(df[x_col]):
        raise TypeError(f"Scatter X must be numeric. '{x_col}' is {df[x_col].dtype}.")

    if not pd.api.types.is_numeric_dtype(df[y_col]):
        raise TypeError(f"Scatter Y must be numeric. '{y_col}' is {df[y_col].dtype}.")

    d = df[[x_col, y_col]].dropna()

    props = {"width": CHART_WIDTH, "height": 300}
    if chart_title:
        props["title"] = alt.TitleParams(text=chart_title)
    chart = (
        alt.Chart(d)
        .mark_circle(size=style.point_size, opacity=0.7, color=style.data_palette[0])
        .encode(
            x=alt.X(f"{x_col}:Q", title=None),
            y=alt.Y(f"{y_col}:Q", title=None),
            tooltip=[x_col, y_col],
        )
        .properties(**props)
    )

    return _apply_style(chart, style)


# ------------------------------------
# Histogram
# ------------------------------------

def histogram(df, x_col, bins=30, style: AtlasStyle = MIDAS, chart_title: str = "") -> alt.Chart:
    d = df[[x_col]].dropna()

    props = {"width": CHART_WIDTH, "height": 300}
    if chart_title:
        props["title"] = alt.TitleParams(text=chart_title)
    chart = (
        alt.Chart(d)
        .mark_bar(color=style.data_palette[0])
        .encode(
            x=alt.X(f"{x_col}:Q", bin=alt.Bin(maxbins=bins), title=None),
            y=alt.Y("count():Q", title=None),
            tooltip=[alt.Tooltip("count():Q", title="Count")],
        )
        .properties(**props)
    )

    return _apply_style(chart, style)
