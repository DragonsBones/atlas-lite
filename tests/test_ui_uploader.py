"""
QA: new file uploader UI — Upload toggle + Reset to demo.
Streamlit 1.41.1 AppTest (no file_uploader widget support).
File upload is simulated by pre-seeding session state.
"""
import pytest
import pandas as pd
from streamlit.testing.v1 import AppTest

APP = "C:/Users/Virj/atlas-lite/app.py"

def ss(at, key, default=None):
    """Safe session_state access."""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


# ── 1: Cold start ─────────────────────────────────────────────────────────────

def test_cold_start_demo_caption():
    """Demo caption visible on cold start."""
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    captions = [c.value for c in at.sidebar.caption]
    assert any("Demo" in c for c in captions), f"Expected demo caption. Got: {captions}"


def test_cold_start_upload_button_visible():
    """'Upload your own data' button is always visible."""
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    labels = [b.label for b in at.sidebar.button]
    assert "Upload your own data" in labels, f"Upload button not found. Buttons: {labels}"


def test_cold_start_no_file_uploader():
    """File uploader hidden by default (show_uploader=False)."""
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert ss(at, "show_uploader", False) is False


def test_cold_start_no_reset_button():
    """Reset button not shown in demo state."""
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    labels = [b.label for b in at.sidebar.button]
    assert not any("Reset" in l for l in labels), f"Reset button should be hidden. Buttons: {labels}"


# ── 2: Upload button toggle ───────────────────────────────────────────────────

def test_upload_button_sets_show_uploader_true():
    """Clicking Upload sets show_uploader=True."""
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.button(key="btn_show_uploader").click().run()
    assert not at.exception
    assert ss(at, "show_uploader") is True


def test_upload_button_double_click_hides():
    """Two clicks toggles show_uploader back to False."""
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.sidebar.button(key="btn_show_uploader").click().run()
    at.sidebar.button(key="btn_show_uploader").click().run()
    assert not at.exception
    assert ss(at, "show_uploader") is False


# ── 3: Simulated uploaded state ───────────────────────────────────────────────

def _make_uploaded_state():
    """Return AppTest with a user-uploaded DataFrame pre-seeded."""
    df = pd.DataFrame({"Category": ["A", "B"], "Value": [10, 20]})
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["df"] = df
    at.session_state["user_uploaded"] = True
    at.session_state["x_col"] = "Category"
    at.session_state["y_col"] = "Value"
    at.session_state["chart_type_ui"] = "Bar"
    at.session_state["chart_title_override"] = ""
    return at.run()


def test_uploaded_state_shows_row_count_caption():
    """After upload, caption shows row/column count."""
    at = _make_uploaded_state()
    assert not at.exception
    captions = [c.value for c in at.sidebar.caption]
    assert any("rows" in c for c in captions), f"Expected row count. Got: {captions}"


def test_uploaded_state_shows_reset_button():
    """Reset button appears when user data is loaded."""
    at = _make_uploaded_state()
    assert not at.exception
    labels = [b.label for b in at.sidebar.button]
    assert any("Reset" in l for l in labels), f"Reset button missing. Buttons: {labels}"


# ── 4: Reset button restores demo state ──────────────────────────────────────

def test_reset_restores_chart_type():
    at = _make_uploaded_state()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    assert ss(at, "chart_type_ui") == "Pareto"


def test_reset_restores_style():
    at = _make_uploaded_state()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    assert ss(at, "style_name") == "cicero"


def test_reset_restores_x_col():
    at = _make_uploaded_state()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    assert ss(at, "x_col") == "Department"


def test_reset_restores_y_col():
    at = _make_uploaded_state()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    assert ss(at, "y_col") == "Spending_GBP_Billions"


def test_reset_restores_chart_title():
    at = _make_uploaded_state()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    assert ss(at, "chart_title_override") == "UK Government Spending 2024/25 (\u00a3bn)"


def test_reset_clears_user_uploaded_flag():
    at = _make_uploaded_state()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    assert ss(at, "user_uploaded") is False


def test_reset_clears_auto_suggestions():
    """Stale auto_suggestions from old dataset must be cleared."""
    at = _make_uploaded_state()
    at.session_state["auto_suggestions"] = ["stale_suggestion"]
    at = at.run()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    result = ss(at, "auto_suggestions")
    assert result == [] or result is None, f"auto_suggestions not cleared: {result}"


def test_reset_clears_auto_info():
    """Stale auto_info must be cleared."""
    at = _make_uploaded_state()
    at.session_state["auto_info"] = object()
    at = at.run()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    assert ss(at, "auto_info") is None


def test_reset_hides_reset_button_after():
    """After reset, the Reset button disappears (user_uploaded=False)."""
    at = _make_uploaded_state()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    labels = [b.label for b in at.sidebar.button]
    assert not any("Reset" in l for l in labels), f"Reset button still visible: {labels}"


# ── 5: XmR chart ─────────────────────────────────────────────────────────────

def _make_xmr_state():
    """Return AppTest with A&E demo pre-seeded so XmR renders immediately."""
    import os
    demo_path = os.path.join(os.path.dirname(__file__), "..", "demo_data", "ae_wait_times_demo.csv")
    ae_df = pd.read_csv(demo_path)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["df"]                   = ae_df
    at.session_state["user_uploaded"]         = False
    at.session_state["xmr_demo_active"]       = True
    at.session_state["x_col"]                = "Month"
    at.session_state["y_col"]                = "Pct_Within_4hrs"
    at.session_state["chart_type_ui"]         = "XmR (SPC)"
    at.session_state["chart_title_override"]  = "A&E 4-Hour Wait Performance (XmR)"
    at.session_state["xmr_rule_1"]            = True
    at.session_state["xmr_rule_2"]            = True
    at.session_state["xmr_rule_3"]            = False
    at.session_state["xmr_rule_4"]            = False
    return at.run()


def test_xmr_chart_renders_without_error():
    """XmR chart renders with A&E demo data and no unhandled exceptions."""
    at = _make_xmr_state()
    assert not at.exception


def test_xmr_chart_type_is_xmr():
    """chart_type_ui should remain XmR after render."""
    at = _make_xmr_state()
    assert not at.exception
    assert ss(at, "chart_type_ui") == "XmR (SPC)"


def test_xmr_demo_caption_shown():
    """Demo caption should mention A&E when xmr_demo_active."""
    at = _make_xmr_state()
    assert not at.exception
    captions = [c.value for c in at.sidebar.caption]
    assert any("A&E" in c for c in captions), f"Expected A&E caption. Got: {captions}"


def test_xmr_spc_rules_toggles_visible():
    """SPC rules toggles should be visible in sidebar when XmR is selected."""
    at = _make_xmr_state()
    assert not at.exception
    toggle_labels = [t.label for t in at.sidebar.toggle]
    assert any("Rule 1" in lbl for lbl in toggle_labels), (
        f"Rule 1 toggle missing. Found: {toggle_labels}"
    )


def test_reset_from_xmr_uploaded_restores_pareto():
    """Reset from XmR with user-uploaded data restores Pareto chart type."""
    ae_df = pd.DataFrame({"Month": ["Jan", "Feb"], "Pct": [70.0, 72.0]})
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["df"]              = ae_df
    at.session_state["user_uploaded"]   = True
    at.session_state["x_col"]           = "Month"
    at.session_state["y_col"]           = "Pct"
    at.session_state["chart_type_ui"]   = "XmR (SPC)"
    at.session_state["xmr_demo_active"] = False
    at = at.run()
    at.sidebar.button(key="btn_reset_demo").click().run()
    assert not at.exception
    assert ss(at, "chart_type_ui") == "Pareto"


# ── 6: Histogram → other chart type (y_col=None regression) ──────────────────

def _histogram_stale_state(target_chart_type: str):
    """
    Simulate the exact session state left after a user was on Histogram
    and has just switched the radio to `target_chart_type`.

    Histogram sets y_col=None in session state.  If the guard is absent
    that None propagates into every chart builder and causes a KeyError.
    """
    df = pd.read_csv("C:/Users/Virj/atlas-lite/demo_data/uk_gov_spending_2024_25.csv")
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["df"]                  = df
    at.session_state["user_uploaded"]       = False
    at.session_state["chart_type_ui"]       = target_chart_type
    at.session_state["x_col"]              = "Department"
    at.session_state["y_col"]              = None   # stale None left by Histogram
    at.session_state["chart_title_override"] = ""
    return at.run()


@pytest.mark.parametrize("target", ["Bar", "Line", "Pareto", "XmR (SPC)"])
def test_switch_from_histogram_no_error(target):
    """Switching away from Histogram (y_col=None) must not raise for any chart type."""
    at = _histogram_stale_state(target)
    assert not at.exception, (
        f"Exception when switching to {target} with stale y_col=None: {at.exception}"
    )


def test_switch_from_histogram_to_scatter_no_error():
    """Scatter has its own normalisation; confirm it also survives the stale state."""
    df = pd.read_csv("C:/Users/Virj/atlas-lite/demo_data/uk_gov_spending_2024_25.csv")
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["df"]            = df
    at.session_state["user_uploaded"] = False
    at.session_state["chart_type_ui"] = "Scatter"
    at.session_state["x_col"]        = "Department"
    at.session_state["y_col"]        = None   # stale None left by Histogram
    at.session_state["chart_title_override"] = ""
    at = at.run()
    assert not at.exception


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
