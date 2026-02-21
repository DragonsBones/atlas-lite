import pandas as pd
import streamlit as st
from pathlib import Path
from typing import Union, IO

@st.cache_data(show_spinner=False)
def load_data(uploaded: Union[str, IO]) -> pd.DataFrame:
    """
    Accepts:
    - Streamlit uploaded file object
    - Local file path string
    """

    # If string path (demo dataset)
    if isinstance(uploaded, str):
        path = Path(uploaded)
        suffix = path.suffix.lower()

        if suffix == ".csv":
            return pd.read_csv(path, encoding="utf-8-sig")

        if suffix == ".xlsx":
            return pd.read_excel(path, engine="openpyxl")

        raise ValueError("Unsupported file type.")

    # If Streamlit uploaded file
    name = uploaded.name.lower()

    if name.endswith(".csv"):
        return pd.read_csv(uploaded, encoding="utf-8-sig")

    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded, engine="openpyxl")

    raise ValueError("Unsupported file type.")