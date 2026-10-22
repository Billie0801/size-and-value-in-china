"""Statistics reported in Tables 3-8."""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import f as f_distribution


def summarize_factors(factors, columns):
    rows = []
    for column in columns:
        series = factors[column].dropna()
        count = len(series)
        standard_deviation = series.std(ddof=1)
        t_statistic = series.mean() / (standard_deviation / np.sqrt(count))
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
    sample = data[columns].dropna()
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


def rolling_factor_r_squared(stock_returns, factors, explanatory_factors, window, minimum_observations):
    returns = stock_returns.reindex(factors.index)
    design = np.column_stack([np.ones(len(factors)), factors[list(explanatory_factors)].to_numpy()])
    values = returns.to_numpy(dtype=float)
    total_r_squared = np.zeros(values.shape[1])
    windows = np.zeros(values.shape[1], dtype=int)
    for end in range(window, len(returns) + 1):
        x = design[end - window:end]
        y = values[end - window:end]
        valid = np.isfinite(y)
        count = valid.sum(axis=0)
        usable = count >= minimum_observations
        mask = valid[:, usable]
        observed = np.where(mask, y[:, usable], 0)
        cross_products = (x[:, :, None] * x[:, None, :]).reshape(window, -1)
        xx = (mask.T @ cross_products).reshape(-1, design.shape[1], design.shape[1])
        xy = observed.T @ x
        coefficients = np.linalg.solve(xx, xy[:, :, None])[:, :, 0]
        yy = np.square(observed).sum(axis=0)
        total_variation = yy - observed.sum(axis=0) ** 2 / count[usable]
        residual_variation = yy - (coefficients * xy).sum(axis=1)
        r_squared = (total_variation - residual_variation) / total_variation
        positions = np.flatnonzero(usable)
        total_r_squared[positions] += r_squared
        windows[positions] += 1
    return pd.DataFrame({
        "stock_id": returns.columns,
        "mean_r_squared": pd.Series(total_r_squared) / windows,
        "rolling_windows": windows,
    })
