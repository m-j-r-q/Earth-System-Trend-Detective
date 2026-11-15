"""Trend statistics for monthly Earth-science time series.

Pipeline:
  1. Remove the seasonal cycle (subtract each calendar month's long-term mean).
  2. Fit a linear trend (OLS) with an autocorrelation-corrected confidence interval.
  3. Run a Mann-Kendall test with autocorrelation-corrected variance and compute
     Sen's slope with a confidence interval.
  4. Turn the numbers into a plain-language verdict.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy import stats

MIN_YEARS_WARN = 10


def deseasonalize(s: pd.Series) -> pd.Series:
    """Anomalies relative to the long-term mean of each calendar month."""
    climatology = s.groupby(s.index.month).transform("mean")
    return s - climatology


def decimal_years(index: pd.DatetimeIndex) -> np.ndarray:
    return (index.year + (index.dayofyear - 0.5) / 365.25).to_numpy(dtype=float)


def _lag1(x: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) == 0:
        return 0.0
    return float(np.corrcoef(x[:-1], x[1:])[0, 1])


def _ols(t: np.ndarray, y: np.ndarray, alpha: float) -> dict:
    """OLS slope; standard error inflated for lag-1 autocorrelation of residuals
    by shrinking the sample size to n_eff = n(1-r)/(1+r)."""
    fit = stats.linregress(t, y)
    resid = y - (fit.intercept + fit.slope * t)
    r1 = max(_lag1(resid), 0.0)
    n = len(y)
    n_eff = max(n * (1 - r1) / (1 + r1), 3.5)
    dof = n_eff - 2
    se = fit.stderr * np.sqrt((n - 2) / dof)
    tcrit = stats.t.ppf(1 - alpha / 2, dof)
    p = 2 * stats.t.sf(abs(fit.slope / se), dof) if se > 0 else 1.0
    return {
        "slope_per_year": float(fit.slope),
        "intercept": float(fit.intercept),
        "ci_low": float(fit.slope - tcrit * se),
        "ci_high": float(fit.slope + tcrit * se),
        "p_value": float(p),
        "r_squared": float(fit.rvalue**2),
        "lag1_autocorr": float(r1),
        "n_effective": float(n_eff),
    }


def _modified_mk(t: np.ndarray, y: np.ndarray, sen_slope: float, alpha: float) -> dict:
    """Mann-Kendall test with the variance of S corrected for autocorrelation.

    Detrend with Sen's slope, rank the residuals, and estimate their lag-1
    autocorrelation r. The variance of S is multiplied by (1 + r) / (1 - r),
    the same sample-size shrinkage used for the OLS trend. The factor is floored
    at 1, so autocorrelation can only make the test more conservative.

    In simulations (25 years monthly, AR(1) noise 0 to 0.6) this keeps the
    false-positive rate near 5%. The Hamed-Rao multi-lag version was too liberal
    (about 16%) at strong autocorrelation, and its variance can go negative.
    """
    base = mk.original_test(y, alpha=alpha)
    ranks = stats.rankdata(y - sen_slope * t)
    r = ranks - ranks.mean()
    r1 = float(np.sum(r[:-1] * r[1:]) / np.sum(r * r))
    factor = 1.0 if r1 <= 0 else (1 + r1) / (1 - min(r1, 0.95))
    var_s = float(base.var_s) * factor
    s = float(base.s)
    z = 0.0 if s == 0 else (s - np.sign(s)) / np.sqrt(var_s)
    return {"p": float(2 * stats.norm.sf(abs(z))), "z": float(z), "tau": float(base.Tau),
            "var_s": var_s, "p_unadjusted": float(base.p), "variance_factor": float(factor)}


def _sen(t: np.ndarray, y: np.ndarray, var_s: float, alpha: float) -> dict:
    """Sen's slope (median of all pairwise slopes) with the Gilbert/Sen
    confidence interval, using the (autocorrelation-adjusted) variance of S."""
    i, j = np.triu_indices(len(y), k=1)
    dt = t[j] - t[i]
    slopes = np.sort((y[j] - y[i]) / dt)
    n_pairs = len(slopes)
    c = stats.norm.ppf(1 - alpha / 2) * np.sqrt(var_s)
    lo = int(np.clip(np.floor((n_pairs - c) / 2), 0, n_pairs - 1))
    hi = int(np.clip(np.ceil((n_pairs + c) / 2), 0, n_pairs - 1))
    slope = float(np.median(slopes))
    return {
        "slope_per_year": slope,
        "intercept": float(np.median(y - slope * t)),
        "ci_low": float(slopes[lo]),
        "ci_high": float(slopes[hi]),
    }


def _fmt_p(p: float) -> str:
    return "p < 0.001" if p < 0.001 else f"p = {p:.3f}"


def _verdict(direction: str, p: float, per_decade: float, unit: str,
             years: float, agree: bool, alpha: float) -> dict:
    if p < 0.01:
        level, phrase = "strong", "strong evidence of"
    elif p < alpha:
        level, phrase = "significant", "statistically significant evidence of"
    elif p < 0.10:
        level, phrase = "weak", "weak, not quite significant, evidence of"
    else:
        level, phrase = "none", "no statistically significant"

    if level == "none":
        text = (f"No statistically significant trend ({_fmt_p(p)}). The data are "
                f"consistent with random variation over these {years:.0f} years; "
                "a longer record might change that.")
    else:
        word = "an increasing" if direction == "up" else "a decreasing"
        text = (f"There is {phrase} {word} trend of about {abs(per_decade):.3g} "
                f"{unit} per decade ({_fmt_p(p)}).")
    if not agree and level != "none":
        text += " Note: the two methods disagree somewhat, so treat the result with care."
    return {"level": level, "text": text}


def analyze(index: pd.DatetimeIndex, values, unit: str = "", alpha: float = 0.05) -> dict:
    """Full trend analysis of one monthly series. Returns a JSON-serialisable dict."""
    s = pd.Series(np.asarray(values, dtype=float), index=pd.DatetimeIndex(index)).sort_index()
    s = s.dropna()
    if len(s) < 36:
        raise ValueError("Need at least 3 years (36 monthly values) for trend analysis.")

    anom = deseasonalize(s)
    t = decimal_years(anom.index)
    y = anom.to_numpy()
    years = float(t[-1] - t[0])

    ols = _ols(t, y, alpha)
    i, j = np.triu_indices(len(y), k=1)
    raw_sen = float(np.median((y[j] - y[i]) / (t[j] - t[i])))
    mkr = _modified_mk(t, y, raw_sen, alpha)
    sen = _sen(t, y, mkr["var_s"], alpha)

    direction = "up" if sen["slope_per_year"] > 0 else "down"
    ols_dir = "up" if ols["slope_per_year"] > 0 else "down"
    agree = (direction == ols_dir) and ((ols["p_value"] < alpha) == (mkr["p"] < alpha))
    per_decade = sen["slope_per_year"] * 10

    return {
        "n_months": int(len(s)),
        "span_years": years,
        "start": str(s.index[0].date()),
        "end": str(s.index[-1].date()),
        "unit": unit,
        "alpha": alpha,
        "warnings": ([f"Record is shorter than {MIN_YEARS_WARN} years; trends may reflect natural variability."]
                     if years < MIN_YEARS_WARN else []),
        "mean": float(s.mean()),
        "ols": ols,
        "mann_kendall": {
            "p_value": mkr["p"],
            "z": mkr["z"],
            "tau": mkr["tau"],
            "p_value_unadjusted": mkr["p_unadjusted"],
            "variance_factor": mkr["variance_factor"],
            "significant": bool(mkr["p"] < alpha),
            "direction": direction,
        },
        "sen": {**sen,
                "per_decade": per_decade,
                "per_decade_ci": [sen["ci_low"] * 10, sen["ci_high"] * 10],
                "total_change": sen["slope_per_year"] * years},
        "percent_per_decade": (per_decade / abs(s.mean()) * 100) if s.mean() != 0 else None,
        "verdict": _verdict(direction, mkr["p"], per_decade, unit, years, agree, alpha),
        "series": {
            "dates": [d.strftime("%Y-%m-%d") for d in s.index],
            "values": s.round(5).tolist(),
            "anomalies": anom.round(5).tolist(),
            "trend_line": (sen["intercept"] + sen["slope_per_year"] * t).round(5).tolist(),
        },
    }
