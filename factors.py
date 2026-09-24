"""Construct CH-3 and FF-3 from the same monthly 2 x 3 portfolio sort."""

import numpy as np
import pandas as pd
from tqdm.auto import tqdm


def weighted_average(values, weights):
    valid = values.notna() & weights.notna() & np.isfinite(weights) & weights.gt(0)
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
        if eligible.empty:
            continue

        microcap_cutoff = eligible["size_me"].quantile(microcap_quantile)
        retained = eligible.loc[eligible["size_me"].gt(microcap_cutoff)].copy()
        market_return = weighted_average(retained["stock_return"], retained["size_me"])

        sortable = retained.dropna(subset=[characteristic]).copy()
        size_break = sortable["size_me"].quantile(size_quantile)
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
        if not all(name in returns for name in required):
            continue

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
                **{f"n_{name}": counts.get(name, 0) for name in required},
            }
        )

    factors = pd.DataFrame(factor_rows).merge(
        risk_free, on="month", how="left", validate="one_to_one"
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
