import pandas as pd
import streamlit as st
from pathlib import Path
from typing import Union, IO

SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx"}


@st.cache_data(show_spinner=False)
def load_data(uploaded: Union[str, IO]) -> pd.DataFrame:
    """
    Accepts:
    - Streamlit uploaded file object
    - Local file path string (str or Path)

    Supported formats: CSV, TSV, XLSX.
    Raises ValueError with a user-friendly message for unsupported types.
    """

    # If string path (demo dataset)
    if isinstance(uploaded, str):
        path = Path(uploaded)
        suffix = path.suffix.lower()

        if suffix == ".csv":
            return pd.read_csv(path, encoding="utf-8-sig")

        if suffix == ".tsv":
            return pd.read_csv(path, sep="\t", encoding="utf-8-sig")

        if suffix == ".xlsx":
            return pd.read_excel(path, engine="openpyxl")

        raise ValueError(
            f"Unsupported file type '{suffix}'. Please upload a CSV, TSV, or XLSX file."
        )

    # If Streamlit uploaded file
    name = uploaded.name.lower()

    if name.endswith(".csv"):
        return pd.read_csv(uploaded, encoding="utf-8-sig")

    if name.endswith(".tsv"):
        return pd.read_csv(uploaded, sep="\t", encoding="utf-8-sig")

    if name.endswith(".xlsx"):
        return pd.read_excel(uploaded, engine="openpyxl")

    ext = Path(name).suffix or "(no extension)"
    raise ValueError(
        f"Unsupported file type '{ext}'. Please upload a CSV, TSV, or XLSX file."
    )