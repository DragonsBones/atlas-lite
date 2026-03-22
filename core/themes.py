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
    # Editorial features
    brand_mark_color: str = ""    # coloured stripe at top of PNG (Cicero identity mark)
    y_axis_orient: str = "left"   # "right" for editorial/Economist-style value axis
    disable_x_grid: bool = False  # horizontal-only gridlines when True
    x_baseline: bool = False      # thin domain line on x-axis (baseline at y=0)
    x_baseline_color: str = "#BBBAB5"
    x_baseline_width: float = 0.5
    padding_left: int = 24        # chart canvas left padding
    padding_right: int = 72       # chart canvas right padding (also used in Pareto)
    title_font_size: int = 13     # chart title font size
    subtitle_font_size: int = 10  # chart subtitle font size


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
    axis_x_label_color="#919191",   # numeric tick labels — most muted element
    axis_y_label_color="#4A4A4A",   # category names — readable but not bold
)

# ── Cicero ───────────────────────────────────────────────────
# Editorially inspired — Atlas's own identity, not an Economist copy.
# Warm off-white · Atlas Navy primary · Intelligent Teal accent.
# Right-side value axis, horizontal-only ghost gridlines, identity brand mark.
CICERO = AtlasStyle(
    name="cicero",
    display_name="Cicero",
    bg_page="#F4F2EE",
    text_primary="#111111",
    text_secondary="#6B6B6B",
    gridline_color="#E8E6E0",    # barely-visible horizontal guides
    grid_opacity=1.0,            # let the light colour do the work
    accent="#1CA7A6",
    data_palette=["#1F2F46", "#1CA7A6", "#4A7BA7", "#C9913D", "#7A3B46"],
    bar_corner_radius=0,
    line_width=2.5,
    point_size=65,
    axis_domain=False,           # no axis domain lines globally …
    grid_stroke_width=0.3,       # fine horizontal guides
    axis_label_color="#555555",
    axis_title_color="#111111",
    brand_mark_color="#1CA7A6",
    y_axis_orient="right",
    disable_x_grid=True,
    x_baseline=True,             # … except a thin baseline on the x-axis
    x_baseline_color="#BBBAB5",
    x_baseline_width=0.5,
    padding_left=40,             # generous breathing room
    padding_right=80,            # space for right-axis labels + Pareto title
    title_font_size=15,
    subtitle_font_size=12,
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
