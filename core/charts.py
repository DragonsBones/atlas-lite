import altair as alt
import pandas as pd

from core.themes import AtlasStyle, MIDAS

# Ensure Altair always inlines data as JSON rather than writing temp files.
# Without this, large-ish DataFrames get a URL reference that vl_convert
# cannot resolve on a re-render, causing stale or blank charts.
alt.data_transformers.disable_max_rows()


# ------------------------------------
# Style application
# ------------------------------------

CHART_WIDTH = 560


def agg_bar_data(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    as_rate: bool = False,
    top_n: int = 25,
    sort_desc: bool = True,
) -> pd.DataFrame:
    """Aggregate and slice data for a bar chart. Shared by bar_chart() and export."""
    d = df[[x_col, y_col]].dropna()
    agg = d.groupby(x_col, as_index=False)[y_col].sum()
    if as_rate:
        total = agg[y_col].sum()
        if total > 0:
            agg[y_col] = (agg[y_col] / total) * 100
    # Always take the top-N by value; sort_desc controls display order in the chart
    agg = agg.sort_values(y_col, ascending=False).head(top_n)
    if not sort_desc:
        agg = agg.sort_values(x_col)
    return agg


def agg_xmr_data(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    active_rules: tuple = (1, 2),
) -> pd.DataFrame:
    """Compute XmR statistics and detect SPC signals.

    Returns the input rows (dropna) augmented with:
      _mean, _ucl, _lcl  — process centre and control limits
      signal             — True when any active rule fires on that point
    """
    d = df[[x_col, y_col]].dropna().reset_index(drop=True)
    if len(d) < 2:
        raise ValueError("XmR requires at least 2 data points.")

    values = d[y_col].tolist()
    n = len(values)

    moving_ranges = [abs(values[i] - values[i - 1]) for i in range(1, n)]
    mean_mr  = sum(moving_ranges) / len(moving_ranges)
    mean_val = sum(values) / n
    ucl = mean_val + 2.66 * mean_mr
    lcl = mean_val - 2.66 * mean_mr

    d["_mean"] = mean_val
    d["_ucl"]  = ucl
    d["_lcl"]  = lcl
    d["signal"] = False

    # Rule 1: point outside control limits (3-sigma equivalent)
    if 1 in active_rules:
        d.loc[(d[y_col] > ucl) | (d[y_col] < lcl), "signal"] = True

    # Rule 2: 8 consecutive points on same side of centre line
    if 2 in active_rules:
        for i in range(7, n):
            window = values[i - 7: i + 1]
            if all(v > mean_val for v in window) or all(v < mean_val for v in window):
                for j in range(i - 7, i + 1):
                    d.loc[j, "signal"] = True

    # Rule 3: 6 consecutive points trending strictly up or down
    if 3 in active_rules:
        for i in range(5, n):
            window = values[i - 5: i + 1]
            if (all(window[k] < window[k + 1] for k in range(5)) or
                    all(window[k] > window[k + 1] for k in range(5))):
                for j in range(i - 5, i + 1):
                    d.loc[j, "signal"] = True

    # Rule 4: 2 of 3 consecutive points in outer third (~Zone A, 2σ–3σ from mean)
    if 4 in active_rules:
        half_range   = ucl - mean_val          # = 2.66 × mean_mr
        outer_upper  = mean_val + (2.0 / 3.0) * half_range
        outer_lower  = mean_val - (2.0 / 3.0) * half_range
        for i in range(2, n):
            window = values[i - 2: i + 1]
            if sum(1 for v in window if v > outer_upper or v < outer_lower) >= 2:
                for j in range(i - 2, i + 1):
                    d.loc[j, "signal"] = True

    return d


def agg_pareto_data(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    top_n: int = 25,
) -> pd.DataFrame:
    """Aggregate data for a Pareto chart: sorted desc, with cumulative_pct column."""
    d = df[[x_col, y_col]].dropna()
    if d.empty:
        raise ValueError(f"No data to display after filtering on {x_col} / {y_col}.")
    agg = d.groupby(x_col, as_index=False)[y_col].sum()
    agg = agg.sort_values(y_col, ascending=False).head(top_n).reset_index(drop=True)
    total = agg[y_col].sum()
    agg["cumulative_pct"] = (agg[y_col].cumsum() / total * 100) if total > 0 else 0.0
    return agg


# ------------------------------------
# Pareto Chart
# ------------------------------------

def pareto_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    top_n: int = 25,
    threshold: float = 80.0,
    style: AtlasStyle = MIDAS,
    chart_title: str = "",
) -> alt.LayerChart:
    """Dual-axis Pareto: bars (left axis) + cumulative % line (right axis) + threshold rule."""
    agg = agg_pareto_data(df, x_col, y_col, top_n=top_n)

    primary = style.data_palette[0]
    accent = style.accent
    x_order = agg[x_col].tolist()

    base = alt.Chart(agg).encode(
        x=alt.X(
            f"{x_col}:N",
            sort=x_order,
            title=None,
            axis=alt.Axis(labelAngle=-30),
            scale=alt.Scale(paddingInner=0.30),
        )
    )

    bars = base.mark_bar(color=primary, cornerRadiusEnd=style.bar_corner_radius).encode(
        y=alt.Y(
            f"{y_col}:Q",
            title="",
            axis=alt.Axis(format=",.0f", tickCount=5),
        ),
        tooltip=[
            alt.Tooltip(f"{x_col}:N", title=x_col),
            alt.Tooltip(f"{y_col}:Q", title=y_col, format=",.0f"),
            alt.Tooltip("cumulative_pct:Q", title="Cumulative %", format=".1f"),
        ],
    )

    line = base.mark_line(
        color=accent,
        strokeWidth=style.line_width,
        point=alt.OverlayMarkDef(color=accent, size=40),
    ).encode(
        y=alt.Y(
            "cumulative_pct:Q",
            title="Cumulative %",
            axis=alt.Axis(format=".0f", tickCount=5, titleColor=accent),
            scale=alt.Scale(domain=[0, 100]),
        ),
    )

    threshold_rule = (
        alt.Chart(pd.DataFrame({"y": [threshold]}))
        .mark_rule(color=accent, strokeDash=[4, 4], strokeWidth=1.5, opacity=0.7)
        .encode(y=alt.Y("y:Q", scale=alt.Scale(domain=[0, 100])))
    )

    props = {
        "width": CHART_WIDTH,
        "height": 300,  # +40 to give the rotated right-axis title room
        # Top-level padding overrides config.padding — extra top space prevents
        # the "Cumulative %" axis title being clipped at the canvas edge.
        # style.padding_right accommodates right-axis labels (80px for Cicero).
        "padding": {"left": style.padding_left, "right": style.padding_right, "top": 50, "bottom": 16},
    }
    if chart_title:
        props["title"] = alt.TitleParams(text=chart_title)

    chart = (
        alt.layer(bars, line, threshold_rule)
        .resolve_scale(y="independent")
        .properties(**props)
    )

    return _apply_style(chart, style)


def xmr_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    active_rules: tuple = (1, 2),
    style: AtlasStyle = MIDAS,
    chart_title: str = "",
) -> alt.LayerChart:
    """XmR (Individuals & Moving Range) SPC chart.

    Layers: individual-values line · normal points · signal points (teal) ·
    centre line (navy) · UCL/LCL dashed rules (muted red).
    """
    plot_data = agg_xmr_data(df, x_col, y_col, active_rules=active_rules)
    mean_val = float(plot_data["_mean"].iloc[0])
    ucl      = float(plot_data["_ucl"].iloc[0])
    lcl      = float(plot_data["_lcl"].iloc[0])

    # ── X-axis type detection ───────────────────────────────────────────────
    if pd.api.types.is_datetime64_any_dtype(plot_data[x_col]):
        x_type, x_sort = "T", None
    elif pd.api.types.is_numeric_dtype(plot_data[x_col]):
        x_type, x_sort = "Q", None
    else:
        parsed = pd.to_datetime(plot_data[x_col], errors="coerce")
        if parsed.notna().mean() > 0.7:
            plot_data = plot_data.copy()
            plot_data[x_col] = parsed
            x_type, x_sort = "T", None
        else:
            x_type = "O"
            x_sort = plot_data[x_col].tolist()   # preserve row order

    # ── Colours ─────────────────────────────────────────────────────────────
    signal_color = "#1CA7A6"          # Intelligent Teal
    line_color   = style.data_palette[0]
    cl_color     = "#1F2F46"          # Atlas Navy
    limit_color  = "#C0504D"          # Muted red

    # ── Encodings ───────────────────────────────────────────────────────────
    def _x(sort=None) -> alt.X:
        kw: dict = {"title": None, "axis": alt.Axis(labelAngle=-30)}
        if sort is not None:
            kw["sort"]  = sort
            kw["scale"] = alt.Scale(domain=sort)
        return alt.X(f"{x_col}:{x_type}", **kw)

    y_enc = alt.Y(
        f"{y_col}:Q",
        title=None,
        axis=alt.Axis(orient=style.y_axis_orient, format=".1f", tickCount=5),
    )
    main_tip = [
        alt.Tooltip(f"{x_col}:{x_type}", title=x_col),
        alt.Tooltip(f"{y_col}:Q", title=y_col, format=".2f"),
    ]

    # ── Chart layers ────────────────────────────────────────────────────────
    values_line = (
        alt.Chart(plot_data)
        .mark_line(color=line_color, strokeWidth=style.line_width)
        .encode(x=_x(x_sort), y=y_enc, tooltip=main_tip)
    )

    norm_df = plot_data[~plot_data["signal"]].copy()
    norm_points = (
        alt.Chart(norm_df)
        .mark_point(color=line_color, size=50, filled=True)
        .encode(x=_x(x_sort), y=y_enc, tooltip=main_tip)
    )

    def _hrule(y_val: float, color: str, dash=None, label: str = "") -> alt.Chart:
        rule_df = pd.DataFrame({"y": [y_val], "label": [label]})
        mark_kw: dict = {"color": color, "strokeWidth": 1.5}
        if dash:
            mark_kw["strokeDash"] = dash
        return (
            alt.Chart(rule_df)
            .mark_rule(**mark_kw)
            .encode(y=alt.Y("y:Q"), tooltip=[alt.Tooltip("label:N", title="")])
        )

    cl_rule  = _hrule(mean_val, cl_color,    label=f"Mean: {mean_val:.2f}")
    ucl_rule = _hrule(ucl,      limit_color, dash=[6, 4], label=f"UCL: {ucl:.2f}")
    lcl_rule = _hrule(lcl,      limit_color, dash=[6, 4], label=f"LCL: {lcl:.2f}")

    layers: list = [values_line, cl_rule, ucl_rule, lcl_rule]

    if not norm_df.empty:
        layers.append(norm_points)

    sig_df = plot_data[plot_data["signal"]].copy()
    if not sig_df.empty:
        sig_tip = main_tip + [
            alt.Tooltip("_ucl:Q", title="UCL", format=".2f"),
            alt.Tooltip("_lcl:Q", title="LCL", format=".2f"),
        ]
        sig_points = (
            alt.Chart(sig_df)
            .mark_point(color=signal_color, size=130, filled=True)
            .encode(x=_x(x_sort), y=y_enc, tooltip=sig_tip)
        )
        layers.append(sig_points)

    props: dict = {"width": CHART_WIDTH, "height": 280}
    if chart_title:
        props["title"] = alt.TitleParams(text=chart_title)

    chart = alt.layer(*layers).properties(**props)
    return _apply_style(chart, style)


def _apply_style(chart: alt.Chart, style: AtlasStyle) -> alt.Chart:
    lbl_color = style.axis_label_color or style.text_secondary
    ttl_color = style.axis_title_color or style.text_secondary
    x_lbl = style.axis_x_label_color or lbl_color
    y_lbl = style.axis_y_label_color or lbl_color

    # Build per-axis X kwargs — accumulate only what differs from the global axis config
    axisX_kw: dict = dict(labelColor=x_lbl, titleColor=ttl_color, labelFontSize=10)
    if style.disable_x_grid:
        axisX_kw["grid"] = False
    if style.x_baseline:
        # Re-enable domain line on x-axis only (overrides global domain=False)
        axisX_kw["domain"] = True
        axisX_kw["domainColor"] = style.x_baseline_color
        axisX_kw["domainWidth"] = style.x_baseline_width

    return (
        chart
        .configure(
            padding={
                "left": style.padding_left,
                "right": style.padding_right,
                "top": 20,
                "bottom": 16,
            },
            background=style.bg_page,
        )
        .configure_view(stroke=None, strokeWidth=0, fill=style.bg_page)
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
        .configure_axisX(**axisX_kw)
        .configure_axisY(labelColor=y_lbl, labelFontSize=11)
        .configure_title(
            fontSize=style.title_font_size,
            fontWeight=700,
            color=style.text_primary,
            subtitleFontSize=style.subtitle_font_size,
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
    orient: str = "h",
    style: AtlasStyle = MIDAS,
    chart_title: str = "",
) -> alt.Chart:

    agg = agg_bar_data(df, x_col, y_col, as_rate=as_rate, top_n=top_n, sort_desc=sort_desc)

    if agg.empty:
        raise ValueError(f"No data to display after filtering on {x_col} / {y_col}.")

    value_format = ".1f" if as_rate else ",.0f"
    x_axis_title = "% of total" if as_rate else None
    primary = style.data_palette[0]
    x_max = agg[y_col].max() * 1.05

    if orient == "v":
        # Vertical column chart — categories on X, values on Y
        x_sort = "-y" if sort_desc else "ascending"
        _y_orient = style.y_axis_orient
        base = alt.Chart(agg).encode(
            x=alt.X(
                f"{x_col}:N",
                sort=x_sort,
                title=None,
                axis=alt.Axis(labelAngle=-30),
                scale=alt.Scale(paddingInner=0.30),
            ),
            y=alt.Y(
                f"{y_col}:Q",
                title=x_axis_title,
                axis=alt.Axis(format=value_format, tickCount=5, orient=_y_orient),
                scale=alt.Scale(domain=[0, x_max]),
            ),
            tooltip=[
                alt.Tooltip(f"{x_col}:N", title=x_col),
                alt.Tooltip(f"{y_col}:Q", title=y_col, format=value_format),
            ],
        )
        bars = base.mark_bar(color=primary, cornerRadiusEnd=style.bar_corner_radius)
        chart = bars
        if show_labels:
            labels = base.mark_text(
                align="center",
                baseline="bottom",
                dy=-4,
                fontSize=11,
                color=style.text_primary,
            ).encode(text=alt.Text(f"{y_col}:Q", format=value_format))
            chart = alt.layer(bars, labels)

        props = {"width": CHART_WIDTH, "height": 260}

    else:
        # Horizontal bar chart (default) — categories on Y, values on X
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
        bars = base.mark_bar(color=primary, size=10, cornerRadiusEnd=style.bar_corner_radius)
        chart = bars
        if show_labels:
            labels = base.mark_text(
                align="left",
                baseline="middle",
                dx=5,
                fontSize=11,
                color=style.text_primary,
            ).encode(text=alt.Text(f"{y_col}:Q", format=value_format))
            chart = alt.layer(bars, labels)

        row_height = 22
        max_height = 320
        chart_height = min(row_height * len(agg) + 40, max_height)
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

    props = {"width": CHART_WIDTH, "height": 260}
    if chart_title:
        props["title"] = alt.TitleParams(text=chart_title)
    chart = (
        alt.Chart(d)
        .mark_line(color=style.data_palette[0], strokeWidth=style.line_width)
        .encode(
            x=alt.X(f"{x_col}:{x_type}", title=None),
            y=alt.Y(f"{y_col}:Q", title=None, axis=alt.Axis(orient=style.y_axis_orient)),
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

    props = {"width": CHART_WIDTH, "height": 260}
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

    props = {"width": CHART_WIDTH, "height": 260}
    if chart_title:
        props["title"] = alt.TitleParams(text=chart_title)
    chart = (
        alt.Chart(d)
        .mark_bar(color=style.data_palette[0])
        .encode(
            x=alt.X(f"{x_col}:Q", bin=alt.Bin(maxbins=bins), title=None),
            y=alt.Y("count():Q", title=None, axis=alt.Axis(orient=style.y_axis_orient)),
            tooltip=[alt.Tooltip("count():Q", title="Count")],
        )
        .properties(**props)
    )

    return _apply_style(chart, style)
