"""Unit tests for core/charts.py — chart builders and agg_bar_data helper."""
import pandas as pd
import pytest
import altair as alt

from core.charts import (
    bar_chart, line_chart, scatter_chart, histogram,
    agg_bar_data, agg_pareto_data, pareto_chart,
    agg_xmr_data, xmr_chart,
)
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


# ---------------------------------------------------------------------------
# agg_xmr_data — XmR statistics helper
# ---------------------------------------------------------------------------

@pytest.fixture
def xmr_df():
    """Sequential data with a known outlier at index 5."""
    return pd.DataFrame({
        "x": range(6),
        "y": [10.0, 11.0, 10.0, 10.0, 11.0, 30.0],
    })


@pytest.fixture
def xmr_stable_df():
    """Stable data for checking UCL/LCL formula."""
    return pd.DataFrame({
        "x": range(5),
        "y": [10.0, 12.0, 11.0, 13.0, 9.0],
    })


def test_agg_xmr_data_returns_required_columns(xmr_df):
    result = agg_xmr_data(xmr_df, "x", "y", active_rules=())
    for col in ("_mean", "_ucl", "_lcl", "signal"):
        assert col in result.columns, f"Missing column: {col}"


def test_agg_xmr_ucl_lcl_formula(xmr_stable_df):
    """UCL = mean + 2.66 × mean_mr, LCL = mean - 2.66 × mean_mr."""
    # y = [10, 12, 11, 13, 9]
    # MR = [2, 1, 2, 4] → mean_mr = 2.25
    # mean = 11.0
    expected_mean_mr = (2 + 1 + 2 + 4) / 4   # = 2.25
    expected_mean    = sum([10.0, 12.0, 11.0, 13.0, 9.0]) / 5  # = 11.0
    expected_ucl = expected_mean + 2.66 * expected_mean_mr
    expected_lcl = expected_mean - 2.66 * expected_mean_mr

    result = agg_xmr_data(xmr_stable_df, "x", "y", active_rules=())
    assert abs(result["_ucl"].iloc[0] - expected_ucl) < 0.001
    assert abs(result["_lcl"].iloc[0] - expected_lcl) < 0.001
    assert abs(result["_mean"].iloc[0] - expected_mean) < 0.001


def test_agg_xmr_rule1_detects_outlier(xmr_df):
    """Rule 1: the lone outlier (30.0) must be flagged; others must not."""
    # y = [10, 11, 10, 10, 11, 30]
    # mean ≈ 13.67, mean_mr = 4.4
    # UCL ≈ 25.37 — only 30.0 exceeds it
    result = agg_xmr_data(xmr_df, "x", "y", active_rules=(1,))
    assert result["signal"].iloc[-1] is True or result["signal"].iloc[-1] == True
    assert not result["signal"].iloc[:-1].any()


def test_agg_xmr_rule1_off_no_signals(xmr_df):
    """With no rules active, no signals should be flagged."""
    result = agg_xmr_data(xmr_df, "x", "y", active_rules=())
    assert not result["signal"].any()


def test_agg_xmr_data_raises_on_single_row():
    df = pd.DataFrame({"x": [1], "y": [5.0]})
    with pytest.raises(ValueError, match="at least 2"):
        agg_xmr_data(df, "x", "y")


def test_agg_xmr_demo_data_rule1_signals():
    """Load the actual A&E demo CSV and verify the known Rule 1 signals."""
    import os
    demo_path = os.path.join(os.path.dirname(__file__), "..", "demo_data", "ae_wait_times_demo.csv")
    demo_df = pd.read_csv(demo_path)
    result = agg_xmr_data(demo_df, "Month", "Pct_Within_4hrs", active_rules=(1,))
    signal_months = result.loc[result["signal"], "Month"].tolist()
    # Jan-2024, Dec-2024, Jan-2025 should be below LCL (~66.03)
    for expected in ("Jan-2024", "Dec-2024", "Jan-2025"):
        assert expected in signal_months, f"Expected signal at {expected}, got: {signal_months}"


# ---------------------------------------------------------------------------
# xmr_chart
# ---------------------------------------------------------------------------

def test_xmr_chart_returns_layer_chart(xmr_df):
    chart = xmr_chart(xmr_df, "x", "y", style=MIDAS)
    assert isinstance(chart, alt.LayerChart)


def test_xmr_chart_with_string_x():
    df = pd.DataFrame({
        "month": [f"M{i:02d}" for i in range(1, 13)],
        "val":   [10.0, 12.0, 11.0, 13.0, 9.0, 10.0, 11.0, 12.0, 10.0, 9.0, 11.0, 10.0],
    })
    chart = xmr_chart(df, "month", "val", style=MIDAS)
    assert isinstance(chart, alt.LayerChart)


def test_xmr_chart_with_chart_title(xmr_df):
    chart = xmr_chart(xmr_df, "x", "y", chart_title="Test XmR", style=MIDAS)
    assert isinstance(chart, alt.LayerChart)


def test_xmr_chart_no_rules_active(xmr_df):
    """With all rules off the chart still renders without error."""
    chart = xmr_chart(xmr_df, "x", "y", active_rules=(), style=MIDAS)
    assert isinstance(chart, alt.LayerChart)
