import pandas as pd
import re
from typing import Iterable, Tuple

def compute_tardies(
    df: pd.DataFrame,
    tardy_codes: Iterable[str],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (summary_df, detail_df)
    - summary: tardy_marks (total across periods), tardy_days (days with >=1 tardy)
    - detail: one row per tardy mark (student, date, period, code)
    """
    tardy_codes = {str(c).strip() for c in tardy_codes if str(c).strip()}

    # detect Per0..Per9 (or any PerN)
    per_cols = [c for c in df.columns if re.fullmatch(r"Per\d+", str(c))]
    if not per_cols:
        raise ValueError("No period columns found (expected columns like Per0, Per1, ...).")

    # make sure period codes are strings
    df = df.copy()
    df[per_cols] = df[per_cols].apply(lambda s: s.astype(str).str.strip())

    # count tardy marks across periods per row
    is_tardy = df[per_cols].isin(tardy_codes)
    df["tardy_marks"] = is_tardy.sum(axis=1)
    df["tardy_day_flag"] = df["tardy_marks"] > 0

    # expected id columns
    id_cols = ["Student ID", "Last Name", "First Name"]
    missing = [c for c in id_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Date is optional but strongly preferred
    has_date = "Date" in df.columns

    # summary per student
    summary = (
        df.groupby(id_cols, dropna=False)
          .agg(
              tardy_marks=("tardy_marks", "sum"),
              tardy_days=("tardy_day_flag", "sum"),
          )
          .reset_index()
          .sort_values(["tardy_marks", "tardy_days"], ascending=False)
    )

    # detail log
    detail_id_vars = id_cols + (["Date"] if has_date else [])
    detail = df[detail_id_vars + per_cols].melt(
        id_vars=detail_id_vars,
        value_vars=per_cols,
        var_name="Period",
        value_name="Code",
    )
    detail = detail[detail["Code"].isin(tardy_codes)].sort_values(
        ["Last Name", "First Name"] + (["Date"] if has_date else []) + ["Period"]
    )

    return summary, detail
