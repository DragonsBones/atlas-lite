# core/recommend.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ----------------------------
# Data structures
# ----------------------------

@dataclass(frozen=True)
class ColProfile:
    name: str
    dtype_group: str  # numeric | datetime | categorical | boolean | id_like | text_like
    n_unique: int
    unique_ratio: float
    missing_ratio: float
    avg_str_len: float
    is_id_like: bool


@dataclass(frozen=True)
class ChartSuggestion:
    chart_type: str  # "bar" | "line" | "scatter" | "pareto" | "xmr"
    confidence: int  # 0..100
    reason: str
    spec: Dict[str, Any]  # suggested encodings/params for your charts.py


# ----------------------------
# Profiling helpers
# ----------------------------

def _safe_nunique(s: pd.Series) -> int:
    try:
        return int(s.nunique(dropna=True))
    except Exception:
        return int(pd.Series(s).nunique(dropna=True))


def _avg_str_len(s: pd.Series, sample_n: int = 200) -> float:
    s_nonnull = s.dropna()
    if len(s_nonnull) == 0:
        return 0.0
    sample = s_nonnull.astype(str).head(sample_n)
    return float(sample.map(len).mean())


def _try_parse_datetime_rate(s: pd.Series, sample_n: int = 250) -> float:
    s_nonnull = s.dropna()
    if len(s_nonnull) == 0:
        return 0.0
    sample = s_nonnull.astype(str).head(sample_n)
    dt = pd.to_datetime(sample, errors="coerce", utc=False, dayfirst=True)
    return float(dt.notna().mean())


def _is_id_like(s: pd.Series, n_unique: int, unique_ratio: float) -> bool:
    # Heuristic: almost everything unique + non-trivial size
    if n_unique >= 30 and unique_ratio >= 0.98:
        return True

    # Numeric IDs often look like integers with high uniqueness
    s_nonnull = s.dropna()
    if len(s_nonnull) >= 30 and pd.api.types.is_numeric_dtype(s_nonnull):
        as_float = pd.to_numeric(s_nonnull, errors="coerce")
        if as_float.notna().mean() > 0.95:
            frac = np.modf(as_float.dropna().to_numpy())[0]
            is_mostly_int = float((np.abs(frac) < 1e-9).mean()) > 0.98
            if is_mostly_int and unique_ratio >= 0.95:
                return True

    return False


def profile_columns(df: pd.DataFrame) -> Dict[str, ColProfile]:
    """
    Profile columns once after load. Use st.cache_data around this in app.py.
    """
    n_rows = len(df)
    profiles: Dict[str, ColProfile] = {}

    for col in df.columns:
        s = df[col]
        missing_ratio = float(s.isna().mean()) if n_rows else 0.0
        s_nonnull = s.dropna()

        n_unique = _safe_nunique(s_nonnull) if len(s_nonnull) else 0
        unique_ratio = float(n_unique / max(len(s_nonnull), 1))

        avg_len = _avg_str_len(s)
        dtype_group = "categorical"

        # Base type detection
        if pd.api.types.is_bool_dtype(s):
            dtype_group = "boolean"
        elif pd.api.types.is_datetime64_any_dtype(s):
            dtype_group = "datetime"
        elif pd.api.types.is_numeric_dtype(s):
            dtype_group = "numeric"
        else:
            # object/mixed: attempt datetime inference
            dt_rate = _try_parse_datetime_rate(s)
            if dt_rate >= 0.80:
                dtype_group = "datetime"
            else:
                dtype_group = "text_like" if avg_len > 25 else "categorical"

        # ID-likeness overrides (except datetime/bool)
        is_id = False
        if dtype_group in ("numeric", "categorical", "text_like"):
            is_id = _is_id_like(s, n_unique=n_unique, unique_ratio=unique_ratio)
            if is_id:
                dtype_group = "id_like"

        profiles[col] = ColProfile(
            name=str(col),
            dtype_group=dtype_group,
            n_unique=n_unique,
            unique_ratio=unique_ratio,
            missing_ratio=missing_ratio,
            avg_str_len=avg_len,
            is_id_like=is_id,
        )

    return profiles


# ----------------------------
# Selection helpers
# ----------------------------

def _best_datetime(cols_dt: List[str], profiles: Dict[str, ColProfile]) -> Optional[str]:
    if not cols_dt:
        return None
    # Prefer higher uniqueness (often true time axis), but not 100% required
    return sorted(cols_dt, key=lambda c: profiles[c].n_unique, reverse=True)[0]


def _best_numeric(cols_num: List[str], profiles: Dict[str, ColProfile]) -> Optional[str]:
    if not cols_num:
        return None
    # Prefer columns with some variation (more unique) and low missing
    return sorted(cols_num, key=lambda c: (profiles[c].missing_ratio, -profiles[c].n_unique))[0]


def _best_category(cols_cat: List[str], profiles: Dict[str, ColProfile]) -> Optional[str]:
    if not cols_cat:
        return None
    # Prefer moderate cardinality ~ 12 (good for bar charts)
    def score(c: str) -> float:
        nu = profiles[c].n_unique
        return abs(nu - 12) + (profiles[c].missing_ratio * 10) + (1 if profiles[c].avg_str_len > 40 else 0)

    return sorted(cols_cat, key=score)[0]


def _pick_time_grain(dt_series: pd.Series) -> Optional[str]:
    """
    Returns: "day" | "week" | "month" | "quarter" | "year" | None
    """
    s = dt_series.dropna()
    if len(s) < 2:
        return None
    dt = pd.to_datetime(s, errors="coerce", utc=False, dayfirst=True).dropna()
    if len(dt) < 2:
        return None

    span_days = (dt.max() - dt.min()).days
    if span_days <= 45:
        return "day"
    if span_days <= 180:
        return "week"
    if span_days <= 900:
        return "month"
    if span_days <= 2200:
        return "quarter"
    return "year"


# ----------------------------
# Chart scoring
# ----------------------------

def _clamp_0_100(x: int) -> int:
    return int(max(0, min(100, x)))


def recommend_charts(
    df: pd.DataFrame,
    profiles: Dict[str, ColProfile],
    user_x: Optional[str] = None,
    user_y: Optional[str] = None,
) -> List[ChartSuggestion]:
    """
    Returns top 3 suggestions with spec dicts you can feed into charts.py.
    user_x/user_y are optional current selections from the UI (if any).
    """

    cols = list(df.columns)

    cols_num = [c for c in cols if profiles[c].dtype_group == "numeric"]
    cols_dt = [c for c in cols if profiles[c].dtype_group == "datetime"]
    cols_cat = [c for c in cols if profiles[c].dtype_group == "categorical"]
    cols_id = [c for c in cols if profiles[c].dtype_group == "id_like"]

    # Remove obviously bad axes candidates
    num_no_id = [c for c in cols_num if c not in cols_id]

    best_dt = _best_datetime(cols_dt, profiles)
    best_num = _best_numeric(num_no_id, profiles)
    best_cat = _best_category(cols_cat, profiles)

    # If user chose x/y and they're sensible, prefer them
    if user_x in cols and profiles[user_x].dtype_group != "id_like":
        if profiles[user_x].dtype_group == "datetime":
            best_dt = user_x
        elif profiles[user_x].dtype_group == "categorical":
            best_cat = user_x
        elif profiles[user_x].dtype_group == "numeric":
            best_num = user_x

    if user_y in cols and profiles[user_y].dtype_group == "numeric" and profiles[user_y].dtype_group != "id_like":
        best_num = user_y

    suggestions: List[ChartSuggestion] = []

    n_rows = len(df)

    # ---- LINE (time series)
    if best_dt and best_num:
        conf = 60
        if profiles[best_dt].n_unique >= min(max(10, n_rows // 10), 200):
            conf += 15
        if profiles[best_dt].n_unique < 4:
            conf -= 25
        if profiles[best_num].missing_ratio > 0.2:
            conf -= 10

        grain = _pick_time_grain(df[best_dt])
        suggestions.append(
            ChartSuggestion(
                chart_type="line",
                confidence=_clamp_0_100(conf),
                reason=f"Looks like a time series: {best_dt} against {best_num}.",
                spec={
                    "x": best_dt,
                    "y": best_num,
                    "agg": "sum",
                    "time_grain": grain,  # optional; ignore if you don’t support yet
                },
            )
        )

    # ---- BAR (category comparison)
    if best_cat and best_num:
        conf = 55
        nu = profiles[best_cat].n_unique
        if 2 <= nu <= 25:
            conf += 20
        elif nu > 50:
            conf -= 20

        if profiles[best_cat].avg_str_len > 40:
            conf -= 10

        suggestions.append(
            ChartSuggestion(
                chart_type="bar",
                confidence=_clamp_0_100(conf),
                reason=f"Good for comparing categories: {best_cat} by {best_num}.",
                spec={
                    "x": best_cat,
                    "y": best_num,
                    "agg": "sum",
                    "top_n": 25,
                    "sort_desc": True,
                },
            )
        )

    # ---- SCATTER (relationship)
    if len(num_no_id) >= 2:
        # Prefer user_x/user_y if both numeric and not id-like
        x = user_x if (user_x in num_no_id) else num_no_id[0]
        y = user_y if (user_y in num_no_id and user_y != x) else (num_no_id[1] if num_no_id[1] != x else num_no_id[0])

        conf = 65
        if n_rows >= 50:
            conf += 10
        if n_rows > 50000:
            conf -= 10  # may be heavy, but still valid

        suggestions.append(
            ChartSuggestion(
                chart_type="scatter",
                confidence=_clamp_0_100(conf),
                reason=f"Useful for relationships: {x} versus {y}.",
                spec={
                    "x": x,
                    "y": y,
                },
            )
        )

    # If nothing triggered, fall back gently
    if not suggestions:
        return [
            ChartSuggestion(
                chart_type="bar",
                confidence=35,
                reason="I couldn’t confidently infer a chart from the data. Pick an X and Y to improve suggestions.",
                spec={},
            )
        ]

    # Sort by confidence, return top 3
    suggestions = sorted(suggestions, key=lambda s: s.confidence, reverse=True)
    return suggestions[:3]