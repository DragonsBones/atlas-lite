import streamlit as st
from core.data_loader import load_csv
from core.charts import bar_chart

st.set_page_config(page_title="Atlas Lite", layout="wide")

st.title("Atlas Lite")
st.caption("Upload a CSV → choose X and Y → get a clean bar chart.")

uploaded = st.file_uploader("Upload CSV", type=["csv"])

if not uploaded:
    st.info("Upload a CSV to begin.")
    st.stop()

df = load_csv(uploaded)

st.success("File loaded successfully.")
st.write(f"Rows: {len(df):,} | Columns: {len(df.columns):,}")
st.dataframe(df.head(10), use_container_width=True)

numeric_cols = df.select_dtypes(include="number").columns.tolist()
cat_cols = [c for c in df.columns if c not in numeric_cols]

st.divider()
st.subheader("Chart settings")

if not numeric_cols:
    st.error("No numeric columns detected for Y.")
    st.stop()

if not cat_cols:
    st.error("No categorical columns detected for X.")
    st.stop()

x_col = st.selectbox("X (category)", cat_cols)
y_col = st.selectbox("Y (value)", numeric_cols)

top_n = st.slider("Show top N categories", min_value=5, max_value=50, value=25, step=5)
show_labels = st.toggle("Show value labels", value=True)

st.subheader("Bar chart")
st.caption(f"Showing top {top_n} by total {y_col}")
st.altair_chart(bar_chart(df, x_col, y_col, top_n=top_n, show_labels=show_labels), use_container_width=True)
st.caption(f"Source: {uploaded.name}")