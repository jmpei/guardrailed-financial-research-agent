"""Statistics shared by the evals: per-item trials and a bootstrap interval."""
import random
from collections import defaultdict


def per_item(rows: list[dict], passed) -> dict[str, list[bool]]:
    by_id = defaultdict(list)
    for row in rows:
        by_id[row["id"]].append(passed(row))
    return dict(by_id)


def bootstrap_ci(values: list[float], n_resamples: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% percentile interval of the mean, resampling the values with replacement."""
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(n_resamples))
    return means[int(0.025 * n_resamples)], means[int(0.975 * n_resamples) - 1]
