import numpy as np
import pandas as pd
import pytest

from app.stats import analyze, deseasonalize


def make_series(years=25, trend_per_decade=0.0, ar=0.0, noise=1.0, season=10.0, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2000-01-01", periods=years * 12, freq="MS")
    t = np.arange(len(idx)) / 12
    e = np.zeros(len(idx))
    eps = rng.normal(0, noise, len(idx))
    for k in range(1, len(idx)):
        e[k] = ar * e[k - 1] + eps[k]
    y = 15 + season * np.sin(2 * np.pi * t) + trend_per_decade / 10 * t + e
    return idx, y


def test_deseasonalize_removes_cycle():
    idx, y = make_series(noise=0.01)
    a = deseasonalize(pd.Series(y, index=idx))
    assert a.std() < 0.5  # seasonal amplitude of 10 is gone


def test_recovers_known_trend():
    idx, y = make_series(trend_per_decade=1.0, ar=0.3, noise=0.8)
    r = analyze(idx, y, "°C")
    assert r["mann_kendall"]["significant"]
    lo, hi = r["sen"]["per_decade_ci"]
    assert lo < r["sen"]["per_decade"] < hi
    assert abs(r["sen"]["per_decade"] - 1.0) < 0.3
    assert r["verdict"]["level"] in ("strong", "significant")


def test_no_trend_not_significant():
    idx, y = make_series(trend_per_decade=0.0, ar=0.0, noise=1.0, seed=3)
    r = analyze(idx, y)
    assert r["verdict"]["level"] in ("none", "weak")


def test_autocorrelation_widens_uncertainty():
    idx, y = make_series(trend_per_decade=0.0, ar=0.8, noise=1.0, seed=5)
    r = analyze(idx, y)
    assert r["mann_kendall"]["p_value"] >= r["mann_kendall"]["p_value_unadjusted"]
    assert r["ols"]["n_effective"] < r["n_months"]


def test_short_record_rejected_and_warned():
    idx, y = make_series(years=2)
    with pytest.raises(ValueError):
        analyze(idx, y)
    idx, y = make_series(years=6, trend_per_decade=2.0)
    assert analyze(idx, y)["warnings"]


def test_output_is_json_serialisable():
    import json
    idx, y = make_series(trend_per_decade=0.5)
    json.dumps(analyze(idx, y, "mm/day"))


def test_false_positive_rate_controlled_under_autocorrelation():
    hits = sum(
        analyze(*make_series(trend_per_decade=0.0, ar=0.6, seed=100 + k))["mann_kendall"]["significant"]
        for k in range(80)
    )
    assert hits / 80 < 0.12  # target is 5%; simulations gave 4-5%


def test_verdict_text_reads_naturally():
    idx, y = make_series(trend_per_decade=1.0, ar=0.3, noise=0.8)
    text = analyze(idx, y, "°C")["verdict"]["text"]
    assert "an increasing trend" in text and "a increasing" not in text
    assert "p < 0.001" in text or "p = " in text
    idx, y = make_series(trend_per_decade=-1.0, ar=0.3, noise=0.8)
    assert "a decreasing trend" in analyze(idx, y, "°C")["verdict"]["text"]
