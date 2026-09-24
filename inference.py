"""Statistics reported in Tables 3 and 5."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import f as f_distribution


def summarize_factors(factors, columns):
    rows = []
    for column in columns:
        series = pd.to_numeric(factors[column], errors="coerce").dropna()
        count = len(series)
        standard_deviation = series.std(ddof=1)
        t_statistic = (
            series.mean() / (standard_deviation / np.sqrt(count))
            if count > 1 and standard_deviation > 0
            else float("nan")
        )
        rows.append(
            {
                "factor": column,
                "months": count,
                "mean_percent": series.mean() * 100,
                "std_percent": standard_deviation * 100,
                "t_statistic": t_statistic,
            }
        )
    return pd.DataFrame(rows)


def factor_regression(data, dependent, explanatory_factors):
    columns = [dependent, *explanatory_factors]
    sample = data[columns].apply(pd.to_numeric, errors="coerce").dropna()
    fit = sm.OLS(sample[dependent], sm.add_constant(sample[list(explanatory_factors)])).fit(
        cov_type="HC0"
    )
    result = {
        "dependent": dependent,
        "months": int(fit.nobs),
        "mean_percent": sample[dependent].mean() * 100,
        "alpha_percent": fit.params["const"] * 100,
        "alpha_t": fit.tvalues["const"],
    }
    for factor in explanatory_factors:
        result[f"loading_{factor}"] = fit.params[factor]
        result[f"t_{factor}"] = fit.tvalues[factor]
    return pd.Series(result)


def grs_test(test_assets, benchmark_factors):
    asset_names = list(test_assets.columns)
    factor_names = list(benchmark_factors.columns)
    sample = pd.concat([test_assets, benchmark_factors], axis=1).dropna()
    assets = sample[asset_names].to_numpy(dtype=float)
    factors = sample[factor_names].to_numpy(dtype=float)
    observations, number_of_assets = assets.shape
    number_of_factors = factors.shape[1]
    if observations <= number_of_assets + number_of_factors:
        raise ValueError("Not enough observations for the GRS test")

    design = np.column_stack([np.ones(observations), factors])
    coefficients = np.linalg.lstsq(design, assets, rcond=None)[0]
    alphas = coefficients[0]
    residuals = assets - design @ coefficients
    residual_covariance = residuals.T @ residuals / (
        observations - number_of_factors - 1
    )
    factor_mean = factors.mean(axis=0)
    centered_factors = factors - factor_mean
    factor_covariance = centered_factors.T @ centered_factors / observations
    factor_covariance = np.atleast_2d(factor_covariance)

    numerator = alphas @ np.linalg.solve(residual_covariance, alphas)
    denominator = 1.0 + factor_mean @ np.linalg.solve(
        factor_covariance, factor_mean
    )
    statistic = (
        observations
        / number_of_assets
        * (observations - number_of_assets - number_of_factors)
        / (observations - number_of_factors - 1)
        * numerator
        / denominator
    )
    degrees_of_freedom_1 = number_of_assets
    degrees_of_freedom_2 = observations - number_of_assets - number_of_factors
    return pd.Series(
        {
            "assets": number_of_assets,
            "months": observations,
            "grs_f": statistic,
            "p_value": f_distribution.sf(
                statistic, degrees_of_freedom_1, degrees_of_freedom_2
            ),
        }
    )
