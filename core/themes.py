from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AtlasStyle:
    name: str
    display_name: str
    bg_page: str
    text_primary: str
    text_secondary: str
    gridline_color: str
    grid_opacity: float
    accent: str
    data_palette: List[str]
    bar_corner_radius: int
    line_width: float
    point_size: int
    axis_domain: bool
    # Optional per-style overrides (fall back to text_secondary when empty)
    grid_stroke_width: float = 0.7
    axis_label_color: str = ""   # shared fallback for both axes
    axis_title_color: str = ""
    axis_x_label_color: str = ""  # x-axis (numeric tick) labels — often more muted
    axis_y_label_color: str = ""  # y-axis (category) labels — slightly bolder


# ── Midas ────────────────────────────────────────────────────
# Premium, calm, executive-neutral. Markets briefing aesthetic.
MIDAS = AtlasStyle(
    name="midas",
    display_name="Midas",
    bg_page="#F4EFE6",
    text_primary="#1A1A1A",
    text_secondary="#7A7060",       # warm grey — kept for non-axis uses
    gridline_color="#E3DED6",       # barely-there parchment gridlines
    grid_opacity=0.17,              # FT-level: structural ghost, not visual noise
    accent="#B38B00",
    data_palette=["#2C3E6B", "#4C5A73", "#8C96A6", "#B38B00", "#D8CFC0"],
    bar_corner_radius=2,
    line_width=2.0,
    point_size=70,
    axis_domain=False,
    grid_stroke_width=0.5,
    axis_label_color="#555555",     # shared fallback
    axis_title_color="#2A2A2A",
    axis_x_label_color="#7A7A7A",   # numeric tick labels — most muted element
    axis_y_label_color="#4A4A4A",   # category names — readable but not bold
)

# ── Cicero ───────────────────────────────────────────────────
# Boardroom briefing, argument-led. Economist-like restraint.
CICERO = AtlasStyle(
    name="cicero",
    display_name="Cicero",
    bg_page="#FFFFFF",
    text_primary="#111111",
    text_secondary="#555555",
    gridline_color="#EFEFEF",
    grid_opacity=0.6,
    accent="#C00000",
    data_palette=["#111111", "#BFBFBF", "#E0E0E0", "#C00000", "#888888"],
    bar_corner_radius=0,
    line_width=2.5,
    point_size=65,
    axis_domain=False,
)

# ── Archimedes ───────────────────────────────────────────────
# Academic/technical reporting. Neutral, method-first, captioned.
ARCHIMEDES = AtlasStyle(
    name="archimedes",
    display_name="Archimedes",
    bg_page="#FFFFFF",
    text_primary="#000000",
    text_secondary="#4A4A4A",
    gridline_color="#E6E6E6",
    grid_opacity=0.9,
    accent="#3E5F8A",
    data_palette=["#1F3A5F", "#3E5F8A", "#6C8EBF", "#A6BDD8", "#DCE6F2"],
    bar_corner_radius=0,
    line_width=2.0,
    point_size=60,
    axis_domain=True,
)


STYLES: dict[str, AtlasStyle] = {
    s.name: s for s in [MIDAS, CICERO, ARCHIMEDES]
}


def get_style(name: str) -> AtlasStyle:
    return STYLES.get(name, MIDAS)
