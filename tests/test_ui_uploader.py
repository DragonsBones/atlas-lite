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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
