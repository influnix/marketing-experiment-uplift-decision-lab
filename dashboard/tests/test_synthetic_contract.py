import json
import math
from statistics import NormalDist

import pytest

from dashboard import synthetic_contract as contract
from dashboard.synthetic_data import build_payload, sample_moments


def test_fixture_reproduces_frozen_bytes():
    stored = contract.FIXTURE_PATH.read_bytes()
    assert stored == contract.encode_fixture(build_payload())
    assert stored == contract.encode_fixture(build_payload())
    payload = contract.load_fixture()
    assert set(payload) == {"metadata", "arm_results", "policy_results"}
    assert payload["metadata"]["source_origin"] == "SYNTHETIC"
    assert payload["metadata"]["fixture_id"] == "day14-email-lab-synthetic-v1"
    assert payload["metadata"]["seed"] == 20261109
    assert [r["n"] for r in payload["arm_results"]] == [r["n"] for r in build_payload()["arm_results"]]


@pytest.mark.parametrize("change", ("digest", "origin"))
def test_fixture_rejects_contract_mismatch(tmp_path, monkeypatch, change):
    target = tmp_path / "fixture.json"
    stored = json.loads(contract.FIXTURE_PATH.read_bytes())
    if change == "digest":
        stored["payload"]["arm_results"][0]["n"] = 1
    else:
        stored["payload"]["metadata"]["source_origin"] = "UNVERIFIED"
        stored["content_sha256"] = contract.content_hash(stored["payload"])
    target.write_text(json.dumps(stored), encoding="ascii")
    monkeypatch.setattr(contract, "FIXTURE_PATH", target)
    with pytest.raises(ValueError, match="fixture contract mismatch"):
        contract.load_fixture()


def test_fixed_design_and_arm_summary():
    payload = contract.load_fixture()
    meta = payload["metadata"]
    assert meta["arms"] == ["No E-Mail", "Mens E-Mail", "Womens E-Mail"]
    assert meta["logging_propensity"] == [1 / 3] * 3
    assert [meta["policy_definitions"][p]["action_probabilities"] for p in ("P0", "P1", "P2", "P3")] == [
        [1, 0, 0], [0, 1, 0], [0, 0, 1], [1 / 3] * 3,
    ]
    counts, sums, _ = sample_moments()
    assert sum(counts) == meta["n"] == 12909
    for i, row in enumerate(payload["arm_results"]):
        assert row["n"] == counts[i]
        assert 0 <= row["conversion"] <= row["visit"] <= 100
        assert row["conversion"] == pytest.approx(100 * sums["conversion"][i] / counts[i])
        assert row["visit"] == pytest.approx(100 * sums["visit"][i] / counts[i])
        assert row["spend"] == pytest.approx(sums["spend"][i] / (100 * counts[i]))


@pytest.mark.parametrize("outcome", ("conversion", "visit", "spend"))
def test_ht_and_paired_ci_against_arm_moments(outcome):
    payload = contract.load_fixture()
    meta = payload["metadata"]
    _, sums, squares = sample_moments()
    n = meta["n"]
    scale = 0.01 if outcome == "spend" else 100
    rows = [r for r in payload["policy_results"] if r["outcome"] == outcome]
    assert len({(r["policy"], r["kind"]) for r in rows}) == len(rows) == 7
    for row in rows:
        q = meta["policy_definitions"][row["policy"]]["action_probabilities"]
        weights = [prob / propensity for prob, propensity in zip(q, meta["logging_propensity"])]
        if row["kind"] == "incremental":
            weights[0] -= 3
        estimate = sum(w * y * scale for w, y in zip(weights, sums[outcome])) / n
        second_moment = sum(w**2 * y2 * scale**2 for w, y2 in zip(weights, squares[outcome])) / n
        se = math.sqrt((second_moment - estimate**2) / (n - 1))
        assert row["n"] == n
        assert row["estimate"] == pytest.approx(estimate)
        assert row["se"] == pytest.approx(se)
        assert row["low"] == pytest.approx(estimate - NormalDist().inv_cdf(.975) * se)
        assert row["high"] == pytest.approx(estimate + NormalDist().inv_cdf(.975) * se)
        if row["kind"] == "incremental":
            assert row["p_value"] == pytest.approx(2 * NormalDist().cdf(-abs(estimate / se)),
                                                  rel=1e-5, abs=1e-15)
        else:
            assert row["p_value"] is row["p_holm"] is None
    absolute = [r["estimate"] for r in rows if r["kind"] == "absolute"]
    assert absolute[3] == pytest.approx(sum(absolute[:3]) / 3)


def test_holm_uses_two_complete_families():
    rows = [r for r in contract.load_fixture()["policy_results"] if r["kind"] == "incremental"]
    for family, size in (("Primary3", 3), ("Secondary6", 6)):
        group = sorted((r for r in rows if r["holm_family"] == family), key=lambda r: r["p_value"])
        assert len(group) == size
        assert {r["outcome"] for r in group} == ({"conversion"} if size == 3 else {"visit", "spend"})
        for i, row in enumerate(group):
            expected = min(1.0, max((size - j) * group[j]["p_value"] for j in range(i + 1)))
            assert row["p_holm"] == pytest.approx(expected, rel=1e-10, abs=0)
