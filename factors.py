"""Construct CH-3 and FF-3 from the same monthly 2 x 3 portfolio sort."""

import numpy as np
import pandas as pd
from tqdm.auto import tqdm


def weighted_average(values, weights):
    """Renormalize over observed returns; an unobserved portfolio remains missing."""
    valid = values.notna()
    if not valid.any():
        return float("nan")
    return float(np.average(values.loc[valid], weights=weights.loc[valid]))


def construct_size_value_factors(
    panel,
    risk_free,
    *,
    characteristic,
    size_factor_name,
    value_factor_name,
    value_labels,
    microcap_quantile,
    size_quantile,
    value_quantiles,
):
    """Apply one common monthly 2 x 3 sort to EP (CH-3) or BM (FF-3)."""
    low_label, middle_label, high_label = value_labels
    factor_rows = []
    portfolio_rows = []
    diagnostic_rows = []

    for return_month, month_data in tqdm(
        panel.groupby("return_month", sort=True), desc=f"{characteristic} portfolios", unit="month"
    ):
        eligible = month_data.loc[month_data["base_eligible"]].copy()
        microcap_cutoff = eligible["size_me"].quantile(microcap_quantile)
        retained = eligible.loc[eligible["size_me"].gt(microcap_cutoff)].copy()
        market_return = weighted_average(retained["stock_return"], retained["size_me"])

        sortable = retained.dropna(subset=[characteristic]).copy()
        size_break = retained["size_me"].quantile(size_quantile)
        low_break = sortable[characteristic].quantile(value_quantiles[0])
        high_break = sortable[characteristic].quantile(value_quantiles[1])
        sortable["size_group"] = np.where(sortable["size_me"].le(size_break), "S", "B")
        sortable["value_group"] = np.select(
            [sortable[characteristic].le(low_break), sortable[characteristic].ge(high_break)],
            [low_label, high_label],
            default=middle_label,
        )
        sortable["portfolio"] = sortable["size_group"] + sortable["value_group"]

        returns = {
            name: weighted_average(group["stock_return"], group["size_me"])
            for name, group in sortable.groupby("portfolio")
        }
        counts = sortable["portfolio"].value_counts().to_dict()
        required = tuple(
            size + value
            for size in ("S", "B")
            for value in (low_label, middle_label, high_label)
        )
        small = [returns["S" + label] for label in (low_label, middle_label, high_label)]
        big = [returns["B" + label] for label in (low_label, middle_label, high_label)]
        size_factor = np.mean(small) - np.mean(big)
        value_factor = np.mean(
            [returns["S" + high_label], returns["B" + high_label]]
        ) - np.mean([returns["S" + low_label], returns["B" + low_label]])

        factor_rows.append(
            {
                "month": return_month,
                "market_return": market_return,
                size_factor_name: size_factor,
                value_factor_name: value_factor,
            }
        )
        portfolio_rows.append({"month": return_month, **returns})
        diagnostic_rows.append(
            {
                "month": return_month,
                "eligible_before_microcap_filter": len(eligible),
                "eligible_after_microcap_filter": len(retained),
                "eligible_for_six_portfolios": len(sortable),
                "microcap_cutoff": microcap_cutoff,
                "size_break": size_break,
                f"{characteristic.lower()}_30": low_break,
                f"{characteristic.lower()}_70": high_break,
                **{f"n_{name}": counts[name] for name in required},
            }
        )

    factors = pd.DataFrame(factor_rows).merge(
        risk_free, on="month", how="left"
    )
    factors["MKT"] = factors["market_return"] - factors["RF"]
    factor_columns = [
        "month",
        "market_return",
        size_factor_name,
        value_factor_name,
        "RF",
        "annual_deposit_rate_percent",
        "MKT",
    ]
    return (
        factors[factor_columns].sort_values("month").reset_index(drop=True),
        pd.DataFrame(portfolio_rows).sort_values("month").reset_index(drop=True),
        pd.DataFrame(diagnostic_rows).sort_values("month").reset_index(drop=True),
    )


def assign_anomaly_groups(data, characteristic, deciles, positive_only):
    data = data.loc[np.isfinite(data[characteristic])].sort_values("stock_id").copy()
    if positive_only:
        data = data.loc[data[characteristic].gt(0)].copy()
    rank = data[characteristic].rank(method="first")
    data["unconditional_decile"] = np.floor((rank - 1) * deciles / len(data))
    rank_within_size = data.groupby("size_decile")[characteristic].rank(method="first")
    counts = data.groupby("size_decile")[characteristic].transform("size")
    data["neutral_decile"] = np.floor((rank_within_size - 1) * deciles / counts)
    if data["size_decile"].nunique() != deciles or counts.lt(deciles).any():
        data["neutral_decile"] = np.nan
    return data


def construct_anomaly_portfolios(panel, directions, positive_only, deciles):
    rows = []
    for month, universe in tqdm(panel.groupby("return_month"), desc="Anomaly portfolios", unit="month"):
        for characteristic, direction in directions.items():
            if characteristic == "REV":
                continue
            data = assign_anomaly_groups(universe, characteristic, deciles, characteristic in positive_only)
            for name, group_column in [("A", "unconditional_decile"), ("B", "neutral_decile")]:
                if name == "B" and characteristic == "SIZE":
                    continue
                low = data.loc[data[group_column].eq(0)]
                high = data.loc[data[group_column].eq(deciles - 1)]
                low_return = weighted_average(low["stock_return"], low["size_me"])
                high_return = weighted_average(high["stock_return"], high["size_me"])
                rows.append({
                    "month": month, "panel": name, "anomaly": characteristic,
                    "spread": direction * (high_return - low_return),
                    "low_return": low_return, "high_return": high_return,
                    "sort_stocks": len(data), "low_stocks": len(low), "high_stocks": len(high),
                    "low_return_stocks": int(low["stock_return"].notna().sum()),
                    "high_return_stocks": int(high["stock_return"].notna().sum()),
                })
    return pd.DataFrame(rows)


def construct_reversal_portfolios(
    daily, pools, sample_start, sample_end, signal_window, minimum_observations,
    holding_days, deciles,
):
    calendar = pd.DatetimeIndex(daily.loc[daily["active"], "date"].unique(), name="date").sort_values()
    returns = daily.pivot(index="date", columns="stock_id", values="daily_return").reindex(calendar)
    active = daily.pivot(index="date", columns="stock_id", values="active").reindex_like(returns).eq(True)
    reversal = np.expm1(np.log1p(returns.where(active)).rolling(
        signal_window, min_periods=minimum_observations
    ).sum()).shift(1)
    start = calendar.searchsorted(pd.Timestamp(sample_start))
    dates = calendar[start - holding_days + 1:]
    dates = dates[dates <= pd.Timestamp(sample_end)]
    universes = {month: group.set_index("stock_id") for month, group in pools.groupby("return_month")}
    cohorts = {"A": [], "B": []}
    rows = []
    for date in tqdm(dates, desc="Daily reversal", unit="day"):
        month = date.to_period("M").to_timestamp("M")
        universe = universes[month]
        data = universe.copy()
        data["REV"] = reversal.loc[date].reindex(data.index)
        data = assign_anomaly_groups(data.reset_index(), "REV", deciles, False).set_index("stock_id")
        today = returns.loc[date]
        for name, group_column in [("A", "unconditional_decile"), ("B", "neutral_decile")]:
            new_cohort = {}
            for leg, group in [("long", 0), ("short", deciles - 1)]:
                weights = data.loc[data[group_column].eq(group), "size_me"]
                new_cohort[leg] = weights / weights.sum()
            cohorts[name].append(new_cohort)
            if len(cohorts[name]) > holding_days:
                cohorts[name].pop(0)
            leg_returns = {"long": [], "short": []}
            missing_weights = []
            for cohort in cohorts[name]:
                for leg in ["long", "short"]:
                    weights = cohort[leg]
                    stock_returns = today.reindex(weights.index)
                    missing_weights.append(float(weights.loc[stock_returns.isna()].sum()))
                    # Missing quotes carry the last valuation; their weight is reported below.
                    stock_returns = stock_returns.fillna(0)
                    portfolio_return = float(weights @ stock_returns)
                    leg_returns[leg].append(portfolio_return)
                    cohort[leg] = weights * (1 + stock_returns) / (1 + portfolio_return)
            long_return = float(np.mean(leg_returns["long"]))
            short_return = float(np.mean(leg_returns["short"]))
            rows.append({
                "date": date, "month": month, "panel": name,
                "spread": long_return - short_return,
                "long_return": long_return, "short_return": short_return,
                "cohorts": len(cohorts[name]), "missing_quote_weight": np.mean(missing_weights),
            })
    daily_returns = pd.DataFrame(rows)
    daily_returns = daily_returns.loc[daily_returns["date"].between(sample_start, sample_end)].copy()
    daily_returns["growth"] = 1 + daily_returns["spread"]
    monthly = daily_returns.groupby(["month", "panel"], as_index=False).agg(
        growth=("growth", "prod"), trading_days=("date", "size"),
        minimum_cohorts=("cohorts", "min"), missing_quote_weight=("missing_quote_weight", "mean"),
    )
    monthly["spread"] = monthly.pop("growth") - 1
    monthly["anomaly"] = "REV"
    return monthly, daily_returns
