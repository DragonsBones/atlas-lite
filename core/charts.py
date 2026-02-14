import altair as alt
import pandas as pd

def bar_chart(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    top_n: int = 25,
    show_labels: bool = True
) -> alt.Chart:
    d = df[[x_col, y_col]].dropna()

    agg = (
        d.groupby(x_col, as_index=False)[y_col]
        .sum()
        .sort_values(y_col, ascending=False)
        .head(top_n)
    )

    base = alt.Chart(agg).encode(
        y=alt.Y(f"{x_col}:N", sort="-x", title=None),
        x=alt.X(
            f"{y_col}:Q",
            title=None,
            axis=alt.Axis(format=",.0f")  # 1,000 not 1000
        ),
        tooltip=[
            alt.Tooltip(f"{x_col}:N", title=x_col),
            alt.Tooltip(f"{y_col}:Q", title=y_col, format=",.0f"),
        ],
    )

    bars = base.mark_bar()

    chart = bars

    if show_labels:
        labels = base.mark_text(
            align="left",
            baseline="middle",
            dx=3
        ).encode(
            text=alt.Text(f"{y_col}:Q", format=",.0f")
        )
        chart = alt.layer(bars, labels)

    chart = (
        chart.properties(height=24 * len(agg) + 30)
        .configure_view(stroke=None)
        .configure_axis(
            labelFontSize=12,
            titleFontSize=12,
            gridOpacity=0.2,
            tickSize=3,
        )
        .configure_legend(labelFontSize=12, titleFontSize=12)
    )

    return chart
