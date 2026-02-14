import altair as alt
import pandas as pd

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

    # Aggregate
    agg = (
        d.groupby(x_col, as_index=False)[y_col]
        .sum()
    )

    # Convert to % of total if requested
    if as_rate:
        total = agg[y_col].sum()
        if total > 0:
            agg[y_col] = (agg[y_col] / total) * 100

    # Sort and limit
    agg = agg.sort_values(y_col, ascending=not sort_desc).head(top_n)

    # Formatting
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

    bars = base.mark_bar(color="#1f4e79")

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

    chart = (
        chart.properties(height=28 * len(agg) + 40)
        .configure_view(stroke=None)
        .configure_axis(
            labelFontSize=12,
            titleFontSize=12,
            gridOpacity=0.15,
            tickSize=0,
            domain=False,
        )
    )

    return chart