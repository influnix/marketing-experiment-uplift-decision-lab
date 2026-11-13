"""Offline, stdlib-only generation of fixed synthetic aggregates."""

import argparse
from datetime import datetime, timezone
from math import erfc, sqrt
from pathlib import Path
from random import Random

from dashboard.synthetic_contract import (
    ARMS, N, OUTCOMES, POLICIES, SEED, UNITS, content_hash, encode_fixture, metadata,
)

Z95 = 1.959963984540054
# HT weights = policy probability / logging probability.
WEIGHTS = ((3, 0, 0), (0, 3, 0), (0, 0, 3), (1, 1, 1))


def sample_moments():
    """One pass over synthetic draws, retaining only arm counts/sums/squares."""
    rng = Random(SEED)
    counts = [0] * len(ARMS)
    sums = {outcome: [0] * len(ARMS) for outcome in OUTCOMES}
    squares = {outcome: [0] * len(ARMS) for outcome in OUTCOMES}
    definitions = metadata()["outcome_definitions"]
    for _ in range(N):
        arm = rng.randrange(len(ARMS))
        counts[arm] += 1
        u = rng.random()
        conversion = int(u < definitions["conversion"]["probabilities"][arm])
        visit = int(u < definitions["visit"]["probabilities"][arm])
        cents = round(100 * rng.expovariate(1 / definitions["spend"]["buyer_mean_usd"])) if conversion else 0
        for outcome, value in zip(OUTCOMES, (conversion, visit, cents)):
            sums[outcome][arm] += value
            squares[outcome][arm] += value * value
    return counts, sums, squares


def summary(weights, totals, squares, factor):
    score_sum = sum(w * s for w, s in zip(weights, totals))
    score_squared_sum = sum(w * w * s for w, s in zip(weights, squares))
    estimate = score_sum * factor / N
    se = factor * sqrt((N * score_squared_sum - score_sum**2) / (N * N * (N - 1)))
    return estimate, se


def holm(rows, family):
    previous = 0.0
    for i, row in enumerate(sorted(rows, key=lambda r: r["p_value"])):
        previous = max(previous, min(1.0, (len(rows) - i) * row["p_value"]))
        row.update(p_holm=previous, holm_family=family)


def build_payload():
    counts, sums, squares = sample_moments()
    arms = [
        {
            "arm": name, "n": counts[i],
            **{outcome: sums[outcome][i] / counts[i] * (0.01 if outcome == "spend" else 100)
               for outcome in OUTCOMES},
        }
        for i, name in enumerate(ARMS)
    ]
    policies = []
    for outcome in OUTCOMES:
        factor = 0.01 if outcome == "spend" else 100
        for policy, weights in zip(POLICIES, WEIGHTS):
            for kind in ("absolute", "incremental"):
                if kind == "incremental":
                    if policy == "P0":
                        continue
                    # Use same-row score differences to retain the shared-control covariance.
                    weights_for_estimate = tuple(w - b for w, b in zip(weights, WEIGHTS[0]))
                else:
                    weights_for_estimate = weights
                estimate, se = summary(weights_for_estimate, sums[outcome], squares[outcome], factor)
                policies.append({
                    "policy": policy, "outcome": outcome, "kind": kind, "n": N,
                    "unit": UNITS[outcome][kind], "estimate": estimate, "se": se,
                    "low": estimate - Z95 * se, "high": estimate + Z95 * se,
                    "p_value": erfc(abs(estimate / se) / sqrt(2)) if kind == "incremental" else None,
                    "p_holm": None, "holm_family": None,
                })
    contrasts = [r for r in policies if r["kind"] == "incremental"]
    holm([r for r in contrasts if r["outcome"] == "conversion"], "Primary3")
    holm([r for r in contrasts if r["outcome"] != "conversion"], "Secondary6")
    # Preserve cross-platform math reproducibility without rounding tiny p-values to zero.
    for row in arms + policies:
        for key, value in row.items():
            if isinstance(value, float):
                row[key] = float(format(value, ".12g"))
    return {"metadata": metadata(), "arm_results": arms, "policy_results": policies}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New aggregate fixture file")
    args = parser.parse_args()
    payload = build_payload()
    with args.output.open("xb") as output:
        output.write(encode_fixture(payload))
    print(f"content_sha256={content_hash(payload)}")
    print(f"generated_at_utc={datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
