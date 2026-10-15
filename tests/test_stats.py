from gfra.stats import bootstrap_ci


def test_bootstrap_ci():
    assert bootstrap_ci([1.0] * 10) == (1.0, 1.0)
    lo, hi = bootstrap_ci([0.0] * 5 + [1.0] * 5)
    assert lo < 0.5 < hi
    assert bootstrap_ci([0.0] * 5 + [1.0] * 5) == (lo, hi)
