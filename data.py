from pathlib import Path

import numpy as np
import pandas as pd
from tqdm.auto import tqdm


def _a_share_mask(codes, prefixes):
    return codes.astype("string").str.strip().str.startswith(tuple(prefixes), na=False)


def _allowed_report_periods(
    report_periods,
    *,
    quarterly_reporting_start,
    pre_quarterly_report_months,
):
    quarterly_start = pd.Timestamp(quarterly_reporting_start)
    return report_periods.ge(quarterly_start) | report_periods.dt.month.isin(
        tuple(pre_quarterly_report_months)
    )


def load_or_build(cache_file, builder):
    path = Path(cache_file)
    if path.exists():
        return pd.read_parquet(path)

    data = builder()
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(path, index=False)
    return data


def load_monthly_returns(
    price_file,
    *,
    history_start,
    sample_end,
    stock_prefixes,
    active_trade_values,
    lookback_months,
    chunksize,
    encoding,
):
    columns = [
        "S_INFO_WINDCODE",
        "TRADE_DT",
        "S_DQ_ADJPRECLOSE",
        "S_DQ_ADJCLOSE",
        "S_DQ_TRADESTATUS",
    ]
    history_start = pd.Timestamp(history_start)
    sample_end = pd.Timestamp(sample_end)
    listing_parts = []
    monthly_parts = []

    reader = pd.read_csv(
        price_file,
        usecols=columns,
        dtype="string",
        chunksize=chunksize,
        encoding=encoding,
        low_memory=False,
    )
    for chunk in tqdm(reader, desc="Monthly returns", unit="chunk"):
        stock_id = chunk["S_INFO_WINDCODE"].str.strip()
        dates = pd.to_datetime(chunk["TRADE_DT"].str.strip(), format="%Y%m%d", errors="coerce")
        valid = _a_share_mask(stock_id, stock_prefixes) & dates.notna()

        listing_parts.append(
            pd.DataFrame(
                {"stock_id": stock_id.loc[valid], "listing_date": dates.loc[valid]}
            ).groupby("stock_id", as_index=False)["listing_date"].min()
        )

        in_period = valid & dates.between(history_start, sample_end, inclusive="both")
        if not in_period.any():
            continue

        sample = chunk.loc[in_period, columns].copy()
        sample["stock_id"] = stock_id.loc[in_period]
        sample["date"] = dates.loc[in_period]
        sample["month"] = sample["date"].dt.to_period("M").dt.to_timestamp("M")

        adjusted_close = pd.to_numeric(sample["S_DQ_ADJCLOSE"], errors="coerce")
        adjusted_previous_close = pd.to_numeric(
            sample["S_DQ_ADJPRECLOSE"], errors="coerce"
        )
        sample["daily_growth"] = adjusted_close / adjusted_previous_close
        invalid_growth = ~np.isfinite(sample["daily_growth"]) | sample["daily_growth"].le(0)
        sample.loc[invalid_growth, "daily_growth"] = np.nan
        sample["active_day"] = (
            sample["S_DQ_TRADESTATUS"]
            .str.strip()
            .isin(tuple(active_trade_values))
            .astype("int16")
        )

        monthly_parts.append(
            sample.groupby(["stock_id", "month"], as_index=False).agg(
                monthly_growth=("daily_growth", "prod"),
                return_observations=("daily_growth", "count"),
                active_days=("active_day", "sum"),
            )
        )

    listings = (
        pd.concat(listing_parts, ignore_index=True)
        .groupby("stock_id", as_index=False)["listing_date"]
        .min()
    )
    monthly = (
        pd.concat(monthly_parts, ignore_index=True)
        .groupby(["stock_id", "month"], as_index=False)
        .agg(
            monthly_growth=("monthly_growth", "prod"),
            return_observations=("return_observations", "sum"),
            active_days=("active_days", "sum"),
        )
    )
    monthly["stock_return"] = monthly["monthly_growth"] - 1.0
    monthly.loc[monthly["return_observations"].eq(0), "stock_return"] = np.nan

    all_months = pd.date_range(
        history_start.to_period("M").to_timestamp("M"),
        sample_end.to_period("M").to_timestamp("M"),
        freq="ME",
    )
    complete_index = pd.MultiIndex.from_product(
        [listings["stock_id"].sort_values(), all_months],
        names=["stock_id", "month"],
    )
    monthly = monthly.set_index(["stock_id", "month"]).reindex(complete_index).reset_index()
    monthly["active_days"] = monthly["active_days"].fillna(0).astype("int16")
    monthly["return_observations"] = monthly["return_observations"].fillna(0).astype("int16")
    monthly = monthly.merge(listings, on="stock_id", how="left", validate="many_to_one")
    monthly = monthly.sort_values(["stock_id", "month"]).reset_index(drop=True)
    monthly["active_days_lookback"] = monthly.groupby("stock_id", sort=False)[
        "active_days"
    ].transform(
        lambda days: days.rolling(
            lookback_months, min_periods=lookback_months
        ).sum()
    )
    return monthly.sort_values(["month", "stock_id"]).reset_index(drop=True)


def load_recent_trading_records(
    price_file,
    *,
    formation_start,
    formation_end,
    stock_prefixes,
    active_trade_values,
    trading_day_window,
    chunksize,
    encoding,
):
    columns = ["S_INFO_WINDCODE", "TRADE_DT", "S_DQ_TRADESTATUS"]
    formation_months = pd.date_range(
        pd.Timestamp(formation_start).to_period("M").to_timestamp("M"),
        pd.Timestamp(formation_end).to_period("M").to_timestamp("M"),
        freq="ME",
    )
    final_formation_month = formation_months.max()
    market_dates = set()

    calendar_reader = pd.read_csv(
        price_file,
        usecols=columns,
        dtype="string",
        chunksize=chunksize,
        encoding=encoding,
        low_memory=False,
    )
    for chunk in tqdm(calendar_reader, desc="Market trading calendar", unit="chunk"):
        stock_id = chunk["S_INFO_WINDCODE"].str.strip()
        dates = pd.to_datetime(
            chunk["TRADE_DT"].str.strip(), format="%Y%m%d", errors="coerce"
        )
        active = chunk["S_DQ_TRADESTATUS"].str.strip().isin(
            tuple(active_trade_values)
        )
        keep = (
            _a_share_mask(stock_id, stock_prefixes)
            & active
            & dates.le(final_formation_month)
        )
        market_dates.update(dates.loc[keep].dropna().tolist())

    market_dates = sorted(market_dates)
    window_rows = []
    for formation_month in formation_months:
        eligible_dates = [date for date in market_dates if date <= formation_month]
        recent_dates = eligible_dates[-trading_day_window:]
        if len(recent_dates) != trading_day_window:
            raise ValueError(
                f"Only {len(recent_dates)} market dates available before {formation_month:%Y-%m-%d}"
            )
        window_rows.extend(
            {"date": date, "month": formation_month} for date in recent_dates
        )
    date_windows = pd.DataFrame(window_rows)
    relevant_dates = set(date_windows["date"])

    count_parts = []
    activity_reader = pd.read_csv(
        price_file,
        usecols=columns,
        dtype="string",
        chunksize=chunksize,
        encoding=encoding,
        low_memory=False,
    )
    for chunk in tqdm(activity_reader, desc="Recent 22-day trading records", unit="chunk"):
        stock_id = chunk["S_INFO_WINDCODE"].str.strip()
        dates = pd.to_datetime(
            chunk["TRADE_DT"].str.strip(), format="%Y%m%d", errors="coerce"
        )
        active = chunk["S_DQ_TRADESTATUS"].str.strip().isin(
            tuple(active_trade_values)
        )
        keep = (
            _a_share_mask(stock_id, stock_prefixes)
            & active
            & dates.isin(relevant_dates)
        )
        if not keep.any():
            continue

        selected = pd.DataFrame(
            {"stock_id": stock_id.loc[keep], "date": dates.loc[keep]}
        ).drop_duplicates()
        selected = selected.merge(date_windows, on="date", how="inner")
        count_parts.append(
            selected.groupby(["stock_id", "month"], as_index=False).size()
        )

    counts = (
        pd.concat(count_parts, ignore_index=True)
        .groupby(["stock_id", "month"], as_index=False)["size"]
        .sum()
        .rename(columns={"size": "active_days_recent_22"})
    )
    counts["active_days_recent_22"] = counts["active_days_recent_22"].astype(
        "int16"
    )
    return counts.sort_values(["month", "stock_id"]).reset_index(drop=True)


def load_month_end_characteristics(
    market_file,
    *,
    formation_start,
    formation_end,
    stock_prefixes,
    total_share_multiplier,
    chunksize,
    encoding,
):
    columns = [
        "S_INFO_WINDCODE",
        "TRADE_DT",
        "S_DQ_CLOSE_TODAY",
        "TOT_SHR_TODAY",
    ]
    start = pd.Timestamp(formation_start)
    end = pd.Timestamp(formation_end)
    parts = []

    reader = pd.read_csv(
        market_file,
        usecols=columns,
        dtype="string",
        chunksize=chunksize,
        encoding=encoding,
        low_memory=False,
    )
    for chunk in tqdm(reader, desc="Month-end characteristics", unit="chunk"):
        stock_id = chunk["S_INFO_WINDCODE"].str.strip()
        dates = pd.to_datetime(chunk["TRADE_DT"].str.strip(), format="%Y%m%d", errors="coerce")
        keep = _a_share_mask(stock_id, stock_prefixes) & dates.between(
            start, end, inclusive="both"
        )
        if not keep.any():
            continue

        selected = chunk.loc[keep, columns].copy()
        selected["stock_id"] = stock_id.loc[keep]
        selected["date"] = dates.loc[keep]
        selected["month"] = selected["date"].dt.to_period("M").dt.to_timestamp("M")
        parts.append(
            selected.sort_values("date").drop_duplicates(
                ["stock_id", "month"], keep="last"
            )
        )

    month_end = (
        pd.concat(parts, ignore_index=True)
        .sort_values("date")
        .drop_duplicates(["stock_id", "month"], keep="last")
        .reset_index(drop=True)
    )
    numeric_columns = ["S_DQ_CLOSE_TODAY", "TOT_SHR_TODAY"]
    for column in numeric_columns:
        month_end[column] = pd.to_numeric(month_end[column], errors="coerce")

    month_end["size_me"] = (
        month_end["S_DQ_CLOSE_TODAY"]
        * month_end["TOT_SHR_TODAY"]
        * total_share_multiplier
    )
    month_end["valuation_me"] = month_end["size_me"]
    return month_end[
        ["stock_id", "month", "date", *numeric_columns, "size_me", "valuation_me"]
    ]


def load_point_in_time_earnings(
    income_file,
    *,
    report_start,
    available_end,
    stock_prefixes,
    statement_types,
    chunksize,
    encoding,
):
    columns = [
        "S_INFO_WINDCODE",
        "ACTUAL_ANN_DT",
        "ANN_DT",
        "REPORT_PERIOD",
        "STATEMENT_TYPE",
        "NET_PROFIT_AFTER_DED_NR_LP",
        "NET_PROFIT_EXCL_MIN_INT_INC",
    ]
    report_start = pd.Timestamp(report_start)
    available_end = pd.Timestamp(available_end)
    parts = []

    reader = pd.read_csv(
        income_file,
        usecols=columns,
        dtype="string",
        chunksize=chunksize,
        encoding=encoding,
        low_memory=False,
    )
    for chunk in tqdm(reader, desc="Point-in-time earnings", unit="chunk"):
        stock_id = chunk["S_INFO_WINDCODE"].str.strip()
        statement_type = chunk["STATEMENT_TYPE"].str.strip()
        actual_date = pd.to_datetime(
            chunk["ACTUAL_ANN_DT"].str.strip(), format="%Y%m%d", errors="coerce"
        )
        announced_date = pd.to_datetime(
            chunk["ANN_DT"].str.strip(), format="%Y%m%d", errors="coerce"
        )
        available_date = actual_date.fillna(announced_date)
        report_period = pd.to_datetime(
            chunk["REPORT_PERIOD"].str.strip(), format="%Y%m%d", errors="coerce"
        )
        keep = (
            _a_share_mask(stock_id, stock_prefixes)
            & statement_type.isin(tuple(statement_types))
            & report_period.ge(report_start)
            & available_date.le(available_end)
        )
        if not keep.any():
            continue

        selected = pd.DataFrame(
            {
                "stock_id": stock_id.loc[keep],
                "available_date": available_date.loc[keep],
                "report_period": report_period.loc[keep],
                "statement_type": statement_type.loc[keep],
                "deducted_profit": pd.to_numeric(
                    chunk.loc[keep, "NET_PROFIT_AFTER_DED_NR_LP"], errors="coerce"
                ),
                "fallback_profit": pd.to_numeric(
                    chunk.loc[keep, "NET_PROFIT_EXCL_MIN_INT_INC"], errors="coerce"
                ),
            }
        )
        parts.append(selected)

    earnings = pd.concat(parts, ignore_index=True)
    priority = {statement_type: rank for rank, statement_type in enumerate(statement_types)}
    earnings["statement_priority"] = earnings["statement_type"].map(priority)
    best_priority = earnings.groupby(["stock_id", "report_period"])[
        "statement_priority"
    ].transform("min")
    earnings = earnings.loc[earnings["statement_priority"].eq(best_priority)].copy()

    # This fallback is part of the current numerical replication and is reported in the notebook.
    earnings["earnings"] = earnings["deducted_profit"].fillna(
        earnings["fallback_profit"]
    )
    earnings = (
        earnings.sort_values(["available_date", "report_period", "statement_priority"])
        .drop_duplicates(["stock_id", "report_period", "available_date"], keep="last")
        .reset_index(drop=True)
    )
    return earnings[
        [
            "stock_id",
            "available_date",
            "report_period",
            "statement_type",
            "earnings",
            "deducted_profit",
            "fallback_profit",
        ]
    ]


def load_point_in_time_book_equity(
    balance_sheet_file,
    *,
    report_start,
    available_end,
    stock_prefixes,
    statement_types,
    chunksize,
    encoding,
):
    columns = [
        "S_INFO_WINDCODE",
        "ACTUAL_ANN_DT",
        "ANN_DT",
        "REPORT_PERIOD",
        "STATEMENT_TYPE",
        "TOT_SHRHLDR_EQY_EXCL_MIN_INT",
    ]
    report_start = pd.Timestamp(report_start)
    available_end = pd.Timestamp(available_end)
    parts = []

    reader = pd.read_csv(
        balance_sheet_file,
        usecols=columns,
        dtype="string",
        chunksize=chunksize,
        encoding=encoding,
        low_memory=False,
    )
    for chunk in tqdm(reader, desc="Point-in-time book equity", unit="chunk"):
        stock_id = chunk["S_INFO_WINDCODE"].str.strip()
        statement_type = chunk["STATEMENT_TYPE"].str.strip()
        actual_date = pd.to_datetime(
            chunk["ACTUAL_ANN_DT"].str.strip(), format="%Y%m%d", errors="coerce"
        )
        announced_date = pd.to_datetime(
            chunk["ANN_DT"].str.strip(), format="%Y%m%d", errors="coerce"
        )
        available_date = actual_date.fillna(announced_date)
        report_period = pd.to_datetime(
            chunk["REPORT_PERIOD"].str.strip(), format="%Y%m%d", errors="coerce"
        )
        keep = (
            _a_share_mask(stock_id, stock_prefixes)
            & statement_type.isin(tuple(statement_types))
            & report_period.ge(report_start)
            & available_date.le(available_end)
        )
        if not keep.any():
            continue

        parts.append(
            pd.DataFrame(
                {
                    "stock_id": stock_id.loc[keep],
                    "book_available_date": available_date.loc[keep],
                    "book_report_period": report_period.loc[keep],
                    "book_statement_type": statement_type.loc[keep],
                    "book_equity": pd.to_numeric(
                        chunk.loc[keep, "TOT_SHRHLDR_EQY_EXCL_MIN_INT"],
                        errors="coerce",
                    ),
                }
            )
        )

    book_equity = pd.concat(parts, ignore_index=True)
    priority = {
        statement_type: rank for rank, statement_type in enumerate(statement_types)
    }
    book_equity["statement_priority"] = book_equity[
        "book_statement_type"
    ].map(priority)
    best_priority = book_equity.groupby(["stock_id", "book_report_period"])[
        "statement_priority"
    ].transform("min")
    book_equity = book_equity.loc[
        book_equity["statement_priority"].eq(best_priority)
    ].copy()
    book_equity = (
        book_equity.sort_values(
            ["book_available_date", "book_report_period", "statement_priority"]
        )
        .drop_duplicates(
            ["stock_id", "book_report_period", "book_available_date"], keep="last"
        )
        .reset_index(drop=True)
    )
    return book_equity[
        [
            "stock_id",
            "book_available_date",
            "book_report_period",
            "book_statement_type",
            "book_equity",
        ]
    ]


def add_point_in_time_book_equity(
    panel,
    book_equity,
    *,
    quarterly_reporting_start,
    pre_quarterly_report_months,
):
    formation_keys = panel[["stock_id", "formation_month"]].sort_values(
        ["formation_month", "stock_id"]
    )
    allowed = _allowed_report_periods(
        book_equity["book_report_period"],
        quarterly_reporting_start=quarterly_reporting_start,
        pre_quarterly_report_months=pre_quarterly_report_months,
    )
    available = book_equity.loc[allowed].dropna(
        subset=["book_available_date"]
    ).sort_values(["book_available_date", "stock_id", "book_report_period"])
    matched = pd.merge_asof(
        formation_keys,
        available,
        left_on="formation_month",
        right_on="book_available_date",
        by="stock_id",
        direction="backward",
        allow_exact_matches=True,
    )
    return (
        panel.merge(
            matched,
            on=["stock_id", "formation_month"],
            how="left",
            validate="one_to_one",
        )
        .sort_values(["return_month", "stock_id"])
        .reset_index(drop=True)
    )


def load_monthly_risk_free(
    rate_file,
    *,
    annual_rate_divisor,
    periods_per_year,
):
    raw = pd.read_excel(rate_file, dtype={"Trdmnt": "string"})
    month = pd.to_datetime(raw["Trdmnt"], format="%Y-%m", errors="coerce")
    annual_rate = pd.to_numeric(raw["Interest"], errors="coerce")
    rates = pd.DataFrame(
        {
            "month": month.dt.to_period("M").dt.to_timestamp("M"),
            "annual_deposit_rate_percent": annual_rate,
        }
    ).dropna()
    rates["RF"] = (
        1.0 + rates["annual_deposit_rate_percent"] / annual_rate_divisor
    ) ** (1.0 / periods_per_year) - 1.0
    return rates.sort_values("month").reset_index(drop=True)


def build_monthly_panel(
    monthly_returns,
    month_end_characteristics,
    earnings,
    recent_trading_records,
    *,
    sample_start,
    sample_end,
    minimum_listing_months,
    minimum_active_days_lookback,
    minimum_active_days_recent_window,
    quarterly_reporting_start,
    pre_quarterly_report_months,
):
    start_month = pd.Timestamp(sample_start).to_period("M").to_timestamp("M")
    end_month = pd.Timestamp(sample_end).to_period("M").to_timestamp("M")

    formation = monthly_returns[
        ["stock_id", "month", "listing_date", "active_days_lookback"]
    ].rename(columns={"month": "formation_month"})
    formation = formation.merge(
        month_end_characteristics.rename(columns={"month": "formation_month"}),
        on=["stock_id", "formation_month"],
        how="left",
        validate="one_to_one",
    )
    formation = formation.merge(
        recent_trading_records.rename(columns={"month": "formation_month"}),
        on=["stock_id", "formation_month"],
        how="left",
        validate="one_to_one",
    )
    formation["active_days_recent_22"] = formation[
        "active_days_recent_22"
    ].fillna(0).astype("int16")
    formation["return_month"] = formation["formation_month"] + pd.offsets.MonthEnd(1)
    formation = formation.loc[
        formation["return_month"].between(start_month, end_month)
    ].copy()
    formation["passes_listing_age_filter"] = formation["formation_month"].ge(
        formation["listing_date"] + pd.DateOffset(months=minimum_listing_months)
    )

    formation["passes_trading_filter"] = formation["active_days_lookback"].ge(
        minimum_active_days_lookback
    ) & formation["active_days_recent_22"].ge(minimum_active_days_recent_window)

    returns = monthly_returns[["stock_id", "month", "stock_return"]].rename(
        columns={"month": "return_month"}
    )
    panel = formation.merge(
        returns,
        on=["stock_id", "return_month"],
        how="left",
        validate="one_to_one",
    )

    formation_keys = panel[["stock_id", "formation_month"]].sort_values(
        ["formation_month", "stock_id"]
    )
    allowed = _allowed_report_periods(
        earnings["report_period"],
        quarterly_reporting_start=quarterly_reporting_start,
        pre_quarterly_report_months=pre_quarterly_report_months,
    )
    earnings = earnings.loc[allowed].dropna(subset=["available_date"]).sort_values(
        ["available_date", "stock_id", "report_period"]
    )
    matched = pd.merge_asof(
        formation_keys,
        earnings,
        left_on="formation_month",
        right_on="available_date",
        by="stock_id",
        direction="backward",
        allow_exact_matches=True,
    )[
        ["stock_id", "formation_month", "available_date", "report_period", "earnings"]
    ]
    panel = panel.merge(
        matched,
        on=["stock_id", "formation_month"],
        how="left",
        validate="one_to_one",
    )
    return panel.sort_values(["return_month", "stock_id"]).reset_index(drop=True)
