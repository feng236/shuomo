from __future__ import annotations

import numpy as np


def pareto_filter(rows, minimize_cols=(), maximize_cols=()):
    if not rows:
        return []

    def dominates(a, b):
        better_or_equal = True
        strictly_better = False
        for c in minimize_cols:
            better_or_equal &= a[c] <= b[c]
            strictly_better |= a[c] < b[c]
        for c in maximize_cols:
            better_or_equal &= a[c] >= b[c]
            strictly_better |= a[c] > b[c]
        return better_or_equal and strictly_better

    out = []
    for i, r in enumerate(rows):
        if not any(dominates(o, r) for j, o in enumerate(rows) if j != i):
            out.append(r)
    return out


def topsis_rank(rows, benefit_cols, cost_cols, weights=None):
    if not rows:
        return []

    cols = list(benefit_cols) + list(cost_cols)
    X = np.array([[float(r[c]) for c in cols] for r in rows], dtype=float)
    denom = np.sqrt((X**2).sum(axis=0))
    denom[denom == 0] = 1.0
    Xn = X / denom

    if weights is None:
        weights = np.ones(len(cols)) / len(cols)
    weights = np.array(weights, dtype=float)
    if weights.size != len(cols):
        raise ValueError("weights length must match benefit_cols + cost_cols")
    if weights.sum() <= 0:
        raise ValueError("weights must have positive sum")
    weights = weights / weights.sum()

    V = Xn * weights
    ideal_pos = []
    ideal_neg = []
    for j, c in enumerate(cols):
        if c in benefit_cols:
            ideal_pos.append(V[:, j].max())
            ideal_neg.append(V[:, j].min())
        else:
            ideal_pos.append(V[:, j].min())
            ideal_neg.append(V[:, j].max())
    ideal_pos = np.array(ideal_pos)
    ideal_neg = np.array(ideal_neg)
    d_pos = np.sqrt(((V - ideal_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((V - ideal_neg) ** 2).sum(axis=1))
    score = np.divide(d_neg, d_pos + d_neg, out=np.zeros_like(d_neg), where=(d_pos + d_neg) > 0)

    ranked = []
    for r, s in zip(rows, score):
        nr = dict(r)
        nr["topsis_score"] = float(s)
        ranked.append(nr)
    return sorted(ranked, key=lambda x: x["topsis_score"], reverse=True)


def monte_carlo_kmeans_scenario_design(
    wind_base_pu,
    pv_base_pu,
    n_samples=1000,
    n_clusters=8,
    wind_sigma=0.08,
    pv_sigma=0.08,
    random_state=42,
):
    """
    Expand deterministic 24-hour wind/PV profiles into representative stochastic scenarios.

    The generated samples use multiplicative Gaussian forecast error, are clipped to
    [0, 1], and are reduced by k-means into representative profiles with probabilities.
    """
    wind_base = _as_2d_profiles(wind_base_pu)
    pv_base = _as_2d_profiles(pv_base_pu)
    rng = np.random.default_rng(random_state)
    base_pairs = rng.integers(0, wind_base.shape[0] * pv_base.shape[0], size=n_samples)

    samples = np.zeros((n_samples, 48), dtype=float)
    for i, pair in enumerate(base_pairs):
        wi = pair // pv_base.shape[0]
        pi = pair % pv_base.shape[0]
        wind_noise = rng.normal(0.0, wind_sigma, size=24)
        pv_noise = rng.normal(0.0, pv_sigma, size=24)
        samples[i, :24] = np.clip(wind_base[wi] * (1.0 + wind_noise), 0.0, 1.0)
        samples[i, 24:] = np.clip(pv_base[pi] * (1.0 + pv_noise), 0.0, 1.0)

    centroids, labels = _kmeans(samples, n_clusters=n_clusters, rng=rng)
    probs = np.bincount(labels, minlength=n_clusters).astype(float) / float(n_samples)
    order = np.argsort(-probs)
    centroids = centroids[order]
    probs = probs[order]

    return {
        "wind_pu": centroids[:, :24],
        "pv_pu": centroids[:, 24:],
        "probability": probs,
        "n_samples": int(n_samples),
        "n_clusters": int(n_clusters),
    }


def _as_2d_profiles(values):
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 1:
        if arr.size != 24:
            raise ValueError("profile length must be 24")
        return arr.reshape(1, 24)
    if arr.ndim == 2 and arr.shape[0] == 24:
        return arr.T
    if arr.ndim == 2 and arr.shape[1] == 24:
        return arr
    raise ValueError("profiles must be shape (24,), (24, n), or (n, 24)")


def _kmeans(samples, n_clusters, rng, max_iter=100):
    if not 1 <= n_clusters <= samples.shape[0]:
        raise ValueError("n_clusters must be between 1 and n_samples")

    try:
        from scipy.cluster.vq import kmeans2

        centroids, labels = kmeans2(samples, n_clusters, minit="points", iter=max_iter, seed=rng)
        return centroids, labels.astype(int)
    except Exception:
        pass

    indices = rng.choice(samples.shape[0], size=n_clusters, replace=False)
    centroids = samples[indices].copy()
    labels = np.zeros(samples.shape[0], dtype=int)
    for _ in range(max_iter):
        dist = ((samples[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        new_labels = np.argmin(dist, axis=1)
        new_centroids = centroids.copy()
        for k in range(n_clusters):
            members = samples[new_labels == k]
            if len(members) == 0:
                new_centroids[k] = samples[rng.integers(0, samples.shape[0])]
            else:
                new_centroids[k] = members.mean(axis=0)
        if np.array_equal(labels, new_labels) and np.allclose(centroids, new_centroids):
            break
        labels = new_labels
        centroids = new_centroids
    return centroids, labels
