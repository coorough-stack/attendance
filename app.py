import streamlit as st
import pandas as pd
import datetime as dt
from tardy_calc import compute_tardies

st.set_page_config(page_title="Tardy Counter", layout="wide")

st.title("Student Tardy Counter")
st.caption("Upload an attendance CSV, pick which code(s) count as tardy, then download summary + detail.")

uploaded = st.file_uploader("Upload attendance CSV", type=["csv"])

default_codes = ["T"]  # change if your district uses something else
tardy_codes = st.multiselect("Which code(s) count as a tardy?", options=[
    "A","D","E","H","I","J","L","S","T","U","V","X"
], default=default_codes)

week_start = st.selectbox("Week starts on:", ["Mon", "Sun"], index=0)

as_of_mode = st.radio(
    "Weekly counts reference date:",
    ["Use latest date in uploaded file (recommended)", "Use today", "Pick a date"],
    horizontal=True
)

picked_date = None
if as_of_mode == "Pick a date":
    picked_date = st.date_input("As-of date", value=dt.date.today())


count_button = st.button("Compute Tardies", type="primary", disabled=uploaded is None)

if uploaded and count_button:
    try:
        df = pd.read_csv(uploaded)

        as_of_date = None
        if as_of_mode == "Use today":
            as_of_date = dt.date.today()
        elif as_of_mode == "Pick a date":
            as_of_date = picked_date
        # else: None means "use latest date in file"
        
        summary_df, detail_df = compute_tardies(df, tardy_codes, as_of_date=as_of_date, week_start=week_start)


        st.success(f"Done. Students: {summary_df.shape[0]:,} | Tardy marks: {summary_df['tardy_marks'].sum():,}")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Summary (per student)")
            st.dataframe(summary_df, use_container_width=True, height=420)
            st.download_(
                "Download summary CSV",
                data=summary_df.to_csv(index=False).encode("utf-8"),
                file_name="tardy_summary.csv",
                mime="text/csv",
            )

        with col2:
            st.subheader("Detail (one row per tardy mark)")
            st.dataframe(detail_df, use_container_width=True, height=420)
            st.download_button(
                "Download detail CSV",
                data=detail_df.to_csv(index=False).encode("utf-8"),
                file_name="tardy_detail.csv",
                mime="text/csv",
            )

        with st.expander("Preview raw columns"):
            st.write(df.columns.tolist())

    except Exception as e:
        st.error(f"Error: {e}")
        st.info("Common issues: missing columns (Student ID/Last Name/First Name), or no Per# columns found.")
