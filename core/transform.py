from __future__ import annotations
import pandas as pd

PREFERRED_METRIC_NAMES = [
    "completed", "count", "total", "volume", "value", "amount", "number"
]

AVOID_NUMERIC_NAMES = [
    "week", "year", "month", "day", "id"
]

PREFERRED_DIM_NAMES = [
    "specialty", "service", "category", "type", "group"
]

AVOID_DIM_NAMES = [
    "name", "completedby", "person", "staff", "user"
]

def pick_default_y(numeric_cols: list[str]) -> str:
    if not numeric_cols:
        return ""

    # Prefer obvious metric column names
    lower = {c: c.lower() for c in numeric_cols}
    for key in PREFERRED_METRIC_NAMES:
        for c in numeric_cols:
            if key in lower[c] and not any(bad in lower[c] for bad in AVOID_NUMERIC_NAMES):
                return c

    # Otherwise: choose last numeric as a stable-ish fallback
    return numeric_cols[-1]

def pick_default_x(df: pd.DataFrame, cat_cols: list[str], y_col: str) -> str:
    if not cat_cols:
        return ""

    # Score each categorical col: prefer "Specialty"-like, avoid high-cardinality names, avoid staff-name fields
    best = None
    best_score = float("-inf")

    for c in cat_cols:
        cl = c.lower()
        nunique = df[c].nunique(dropna=True)

        # prefer moderate cardinality (good bar charts)
        if nunique <= 1:
            continue

        score = 0.0

        # Prefer “dimension” names (Specialty etc.)
        if any(k in cl for k in PREFERRED_DIM_NAMES):
            score += 5

        # Avoid person-name-like columns (CompletedBy will often be huge)
        if any(k in cl for k in AVOID_DIM_NAMES):
            score -= 4

        # Cardinality shaping: sweet spot 3–40
        if 3 <= nunique <= 40:
            score += 4
        elif 41 <= nunique <= 80:
            score += 1
        elif nunique > 80:
            score -= 3

        # Slightly prefer earlier columns (stable UX when data changes)
        score += max(0, 2 - (cat_cols.index(c) * 0.1))

        if score > best_score:
            best_score = score
            best = c

    return best or cat_cols[0]