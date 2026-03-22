"""Unit tests for core/charts.py — chart builders and agg_bar_data helper."""
import pandas as pd
import pytest
import altair as alt

from core.charts import bar_chart, line_chart, scatter_chart, histogram, agg_bar_data, agg_pareto_data, pareto_chart
from core.themes import MIDAS

# Bar charts return LayerChart when show_labels=True, Chart otherwise.
# Both are valid Altair outputs — check for any Altair chart type.
_ALTAIR_CHART_TYPES = (alt.Chart, alt.LayerChart)


# ---------------------------------------------------------------------------
# agg_bar_data — shared aggregation helper
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_df():
    return pd.DataFrame({
        "cat": list("ABCDE"),
        "val": [50, 30, 40, 10, 20],
    })


def test_agg_bar_data_returns_top_n(simple_df):
    result = agg_bar_data(simple_df, "cat", "val", top_n=3)
    assert len(result) == 3


def test_agg_bar_data_top_n_are_highest_values(simple_df):
    result = agg_bar_data(simple_df, "cat", "val", top_n=3)
    assert result["val"].min() >= 30  # bottom two (10, 20) excluded


def test_agg_bar_data_as_rate_sums_to_100(simple_df):
    result = agg_bar_data(simple_df, "cat", "val", as_rate=True, top_n=10)
    assert abs(result["val"].sum() - 100.0) < 0.01


def test_agg_bar_data_as_rate_false_does_not_normalize(simple_df):
    result = agg_bar_data(simple_df, "cat", "val", as_rate=False, top_n=10)
    assert result["val"].sum() == 150  # raw sum


def test_agg_bar_data_empty_after_dropna():
    df = pd.DataFrame({"cat": [None, None], "val": [None, None]})
    result = agg_bar_data(df, "cat", "val")
    assert result.empty


def test_agg_bar_data_sort_desc_false(simple_df):
    result = agg_bar_data(simple_df, "cat", "val", sort_desc=False, top_n=5)
    # When sort_desc=False, DataFrame should be sorted alphabetically by x_col
    assert list(result["cat"]) == sorted(result["cat"].tolist())


# ---------------------------------------------------------------------------
# bar_chart
# ---------------------------------------------------------------------------

def test_bar_chart_horizontal_returns_chart(simple_df):
    chart = bar_chart(simple_df, "cat", "val", orient="h", style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


def test_bar_chart_vertical_returns_chart(simple_df):
    chart = bar_chart(simple_df, "cat", "val", orient="v", style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


def test_bar_chart_raises_on_empty_data():
    df = pd.DataFrame({"cat": [None], "val": [None]})
    with pytest.raises(ValueError, match="No data to display"):
        bar_chart(df, "cat", "val")


def test_bar_chart_with_labels(simple_df):
    chart = bar_chart(simple_df, "cat", "val", show_labels=True, style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


def test_bar_chart_as_rate(simple_df):
    chart = bar_chart(simple_df, "cat", "val", as_rate=True, style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


def test_bar_chart_with_title(simple_df):
    chart = bar_chart(simple_df, "cat", "val", chart_title="My Chart", style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


# ---------------------------------------------------------------------------
# line_chart
# ---------------------------------------------------------------------------

def test_line_chart_numeric_x():
    df = pd.DataFrame({"x": range(10), "y": range(10)})
    chart = line_chart(df, "x", "y", style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


def test_line_chart_datetime_x():
    df = pd.DataFrame({
        "dt": pd.date_range("2023-01-01", periods=12, freq="ME"),
        "val": range(12),
    })
    chart = line_chart(df, "dt", "val", style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


# ---------------------------------------------------------------------------
# scatter_chart
# ---------------------------------------------------------------------------

def test_scatter_chart_returns_chart():
    df = pd.DataFrame({"x": range(20), "y": range(20, 40)})
    chart = scatter_chart(df, "x", "y", style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


def test_scatter_chart_raises_on_same_column():
    df = pd.DataFrame({"x": range(10)})
    with pytest.raises(ValueError, match="different columns"):
        scatter_chart(df, "x", "x")


def test_scatter_chart_raises_on_non_numeric_x():
    df = pd.DataFrame({"cat": list("ABCDE"), "val": range(5)})
    with pytest.raises(TypeError, match="numeric"):
        scatter_chart(df, "cat", "val")


# ---------------------------------------------------------------------------
# histogram
# ---------------------------------------------------------------------------

def test_histogram_returns_chart():
    df = pd.DataFrame({"val": range(100)})
    chart = histogram(df, "val", style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


def test_histogram_with_custom_bins():
    df = pd.DataFrame({"val": range(100)})
    chart = histogram(df, "val", bins=10, style=MIDAS)
    assert isinstance(chart, _ALTAIR_CHART_TYPES)


# ---------------------------------------------------------------------------
# agg_pareto_data
# ---------------------------------------------------------------------------

def test_agg_pareto_data_adds_cumulative_pct(simple_df):
    result = agg_pareto_data(simple_df, "cat", "val")
    assert "cumulative_pct" in result.columns


def test_agg_pareto_data_cumulative_pct_reaches_100(simple_df):
    result = agg_pareto_data(simple_df, "cat", "val")
    assert abs(result["cumulative_pct"].iloc[-1] - 100.0) < 0.01


def test_agg_pareto_data_top_n_respected(simple_df):
    result = agg_pareto_data(simple_df, "cat", "val", top_n=3)
    assert len(result) == 3


def test_agg_pareto_data_empty_raises():
    df = pd.DataFrame({"cat": [None, None], "val": [None, None]})
    with pytest.raises(ValueError):
        agg_pareto_data(df, "cat", "val")


# ---------------------------------------------------------------------------
# pareto_chart
# ---------------------------------------------------------------------------

def test_pareto_chart_returns_layer_chart(simple_df):
    chart = pareto_chart(simple_df, "cat", "val", style=MIDAS)
    assert isinstance(chart, alt.LayerChart)


def test_pareto_chart_handles_threshold_param(simple_df):
    chart = pareto_chart(simple_df, "cat", "val", threshold=90.0, style=MIDAS)
    assert isinstance(chart, alt.LayerChart)
