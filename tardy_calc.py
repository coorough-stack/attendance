import pandas as pd
import re
from typing import Iterable, Tuple, Optional

def compute_tardies(
    df: pd.DataFrame,
    tardy_codes: Iterable[str],
    as_of_date: Optional[pd.Timestamp] = None,
    week_start: str = "Mon",  # "Mon" or "Sun"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (summary_df, detail_df)

    Summary includes:
    - tardy_marks (total across periods)
    - tardy_days (days with >=1 tardy)
    - current_week_tardy_marks / current_week_tardy_days
    - previous_week_tardy_marks / previous_week_tardy_days

    Detail includes one row per tardy mark (student, date, period, code).
    """

    tardy_codes = {str(c).strip() for c in tardy_codes if str(c).strip()}

    per_cols = [c for c in df.columns if re.fullmatch(r"Per\d+", str(c))]
    if not per_cols:
        raise ValueError("No period columns found (expected Per0, Per1, ...).")

    df = df.copy()
    df[per_cols] = df[per_cols].apply(lambda s: s.astype(str).str.strip())

    id_cols = ["Student ID", "Last Name", "First Name"]
    missing = [c for c in id_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Compute per-row tardy counts
    is_tardy = df[per_cols].isin(tardy_codes)
    df["tardy_marks"] = is_tardy.sum(axis=1)
    df["tardy_day_flag"] = df["tardy_marks"] > 0

    # Base summary
    summary = (
        df.groupby(id_cols, dropna=False)
          .agg(
              tardy_marks=("tardy_marks", "sum"),
              tardy_days=("tardy_day_flag", "sum"),
          )
          .reset_index()
    )

    # Weekly add-ons (requires Date)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()

        # Pick as_of_date: default to latest date in the file (more reliable than "today")
        if as_of_date is None:
            max_date = df["Date"].max()
            if pd.isna(max_date):
                raise ValueError("Date column exists but could not be parsed into dates.")
            as_of_date = max_date
        else:
            as_of_date = pd.to_datetime(as_of_date).normalize()

        week_start = week_start.strip().title()
        if week_start not in {"Mon", "Sun"}:
            raise ValueError("week_start must be 'Mon' or 'Sun'.")

        week_start_idx = 0 if week_start == "Mon" else 6  # Monday=0 ... Sunday=6
        delta = (as_of_date.weekday() - week_start_idx) % 7
        current_week_start = as_of_date - pd.Timedelta(days=delta)
        current_week_end = current_week_start + pd.Timedelta(days=7)

        prev_week_start = current_week_start - pd.Timedelta(days=7)
        prev_week_end = current_week_start

        def weekly_agg(mask, prefix: str) -> pd.DataFrame:
            g = (
                df.loc[mask]
                  .groupby(id_cols, dropna=False)
                  .agg(
                      **{
                          f"{prefix}_tardy_marks": ("tardy_marks", "sum"),
                          f"{prefix}_tardy_days": ("tardy_day_flag", "sum"),
                      }
                  )
                  .reset_index()
            )
            return g

        cur_mask = (df["Date"] >= current_week_start) & (df["Date"] < current_week_end)
        prev_mask = (df["Date"] >= prev_week_start) & (df["Date"] < prev_week_end)

        cur = weekly_agg(cur_mask, "current_week")
        prev = weekly_agg(prev_mask, "previous_week")

        summary = summary.merge(cur, on=id_cols, how="left").merge(prev, on=id_cols, how="left")

        # Fill missing with 0 and make ints
        for c in [
            "current_week_tardy_marks", "current_week_tardy_days",
            "previous_week_tardy_marks", "previous_week_tardy_days"
        ]:
            if c in summary.columns:
                summary[c] = summary[c].fillna(0).astype(int)
    else:
        # If no Date column, still return base summary; weekly columns simply won't exist
        pass

    summary = summary.sort_values(["tardy_marks", "tardy_days"], ascending=False)

    # Detail log (one row per tardy mark)
    has_date = "Date" in df.columns
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
