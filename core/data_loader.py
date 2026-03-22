import pandas as pd
import streamlit as st
from pathlib import Path
from typing import Union, IO

SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx"}

# Tokens that, if found anywhere in a normalised column name, suggest PID.
# Normalisation: lowercase, strip spaces / underscores / hyphens / dots
# → covers snake_case, camelCase (via lower()), PascalCase, and concatenated forms.
_PID_TOKENS = {
    # Identity / demographics
    "name", "patient", "nhs", "dob", "birth",
    "email", "address", "postcode", "surname", "forename",
    "firstname", "lastname", "gender", "sex",
    # Workflow / staff identifiers
    "completedby", "createdby", "updatedby", "assignedto",
    "staffname", "employeename", "username", "userid", "staffid",
    "worker", "clinician", "consultant", "referrer", "referral",
}


def detect_pid_columns(df: pd.DataFrame) -> list[str]:
    """
    Scan column names and a sample of cell values for common PID patterns.
    Returns the list of column names that appear to contain personal data.
    Does not raise; safe to call on any DataFrame.
    """
    flagged: list[str] = []
    for col in df.columns:
        # Normalise: lowercase + strip all separators so camelCase, snake_case,
        # PascalCase and concatenated variants all reduce to the same form.
        normalised = col.lower().replace(" ", "").replace("_", "").replace("-", "").replace(".", "")
        if any(token in normalised for token in _PID_TOKENS):
            flagged.append(col)
            continue

        # Value-level scanning for string columns
        if df[col].dtype == object:
            sample = df[col].dropna().head(30).astype(str)

            # Email pattern
            if sample.str.contains(r"@.+\.", regex=True).any():
                flagged.append(col)
            # 10-digit NHS number (with or without spaces/hyphens)
            elif sample.str.replace(r"[\s\-]", "", regex=True).str.fullmatch(r"\d{10}").any():
                flagged.append(col)
            # "Surname Firstname" — two Title-Case words (common export format)
            elif sample.str.match(r"^[A-Z][a-z]+ [A-Z][a-z]+$").any():
                flagged.append(col)
            # Reference number: # followed by one or more digits
            elif sample.str.contains(r"#\d+", regex=True).any():
                flagged.append(col)
    return flagged


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