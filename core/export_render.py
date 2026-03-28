# core/export_render.py
import altair as alt


def chart_to_png_bytes(chart: alt.Chart, scale: float = 1.0) -> bytes:
    import vl_convert as vlc
    spec = chart.to_dict()
    return vlc.vegalite_to_png(spec, scale=scale)


def chart_to_svg_bytes(chart: alt.Chart) -> bytes:
    import vl_convert as vlc
    spec = chart.to_dict()
    return vlc.vegalite_to_svg(spec)