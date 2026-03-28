"""Unit tests for core/recommend.py — column profiler and chart recommender."""
import pandas as pd
import pytest

from core.recommend import profile_columns, recommend_charts, ColProfile


# ---------------------------------------------------------------------------
# profile_columns
# ---------------------------------------------------------------------------

def test_profile_numeric_column():
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5]})
    profiles = profile_columns(df)
    assert profiles["val"].dtype_group == "numeric"


def test_profile_categorical_column():
    df = pd.DataFrame({"cat": ["A", "B", "C", "A", "B"]})
    profiles = profile_columns(df)
    assert profiles["cat"].dtype_group == "categorical"


def test_profile_datetime_column():
    df = pd.DataFrame({"dt": pd.date_range("2023-01-01", periods=10, freq="D")})
    profiles = profile_columns(df)
    assert profiles["dt"].dtype_group == "datetime"


def test_profile_id_like_column():
    df = pd.DataFrame({"id": range(100)})
    profiles = profile_columns(df)
    assert profiles["id"].dtype_group == "id_like"


def test_profile_missing_ratio():
    df = pd.DataFrame({"x": [1, None, 3, None, 5]})
    profiles = profile_columns(df)
    assert abs(profiles["x"].missing_ratio - 0.4) < 0.01


# ---------------------------------------------------------------------------
# recommend_charts
# ---------------------------------------------------------------------------

def test_bar_suggested_for_cat_and_numeric():
    df = pd.DataFrame({"cat": list("ABCDE"), "val": [10, 20, 30, 40, 50]})
    profiles = profile_columns(df)
    result = recommend_charts(df, profiles)
    assert result[0].chart_type == "bar"
    assert result[0].spec["x"] == "cat"
    assert result[0].spec["y"] == "val"


def test_line_suggested_for_datetime_and_numeric():
    df = pd.DataFrame({
        "dt": pd.date_range("2023-01-01", periods=20, freq="ME"),
        "val": range(20),
    })
    profiles = profile_columns(df)
    result = recommend_charts(df, profiles)
    assert result[0].chart_type == "line"


def test_numeric_only_falls_back_to_bar():
    # Single numeric column: no categorical/datetime/second-numeric available,
    # so no scoring rule fires and the fallback bar suggestion is returned.
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5, 1, 2, 3, 4, 5] * 10})
    profiles = profile_columns(df)
    result = recommend_charts(df, profiles)
    assert result[0].chart_type == "bar"


def test_scatter_eligible_with_two_numeric_cols():
    # Use repeated values so columns aren't flagged as id_like
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5] * 10,
        "y": [10, 20, 30, 40, 50] * 10,
    })
    profiles = profile_columns(df)
    result = recommend_charts(df, profiles)
    chart_types = [s.chart_type for s in result]
    assert "scatter" in chart_types


def test_returns_at_least_one_suggestion():
    """recommend_charts must never return an empty list."""
    df = pd.DataFrame({"only_text": ["hello", "world"]})
    profiles = profile_columns(df)
    result = recommend_charts(df, profiles)
    assert len(result) >= 1


def test_confidence_in_range():
    df = pd.DataFrame({"cat": list("ABCDE"), "val": [1, 2, 3, 4, 5]})
    profiles = profile_columns(df)
    for s in recommend_charts(df, profiles):
        assert 0 <= s.confidence <= 100


def test_returns_at_most_three_suggestions():
    df = pd.DataFrame({
        "cat": list("ABCDE") * 4,
        "dt": pd.date_range("2023-01-01", periods=20, freq="D"),
        "val1": range(20),
        "val2": range(20, 40),
    })
    profiles = profile_columns(df)
    result = recommend_charts(df, profiles)
    assert len(result) <= 3


def test_user_x_preference_respected():
    df = pd.DataFrame({
        "cat_a": list("ABCDE") * 4,
        "cat_b": list("VWXYZ") * 4,
        "val": range(20),
    })
    profiles = profile_columns(df)
    result = recommend_charts(df, profiles, user_x="cat_b")
    assert result[0].spec.get("x") == "cat_b"
