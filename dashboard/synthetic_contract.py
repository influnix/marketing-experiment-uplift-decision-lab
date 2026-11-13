"""Fixed Day 14 fixture schema and local aggregate loader."""

import hashlib
import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).with_name("synthetic_fixture.json")
FIXTURE_ID = "day14-email-lab-synthetic-v1"
EXPECTED_CONTENT_SHA256 = "4508bd68cd83907a835642075e14fb20c5c11c5ded794358e18397c6a5e38ba0"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "python-mt19937-cent-v1"
SEED = 20261109
N = 12909
ARMS = ("No E-Mail", "Mens E-Mail", "Womens E-Mail")
POLICIES = {
    "P0": "No E-Mail All",
    "P1": "Mens E-Mail All",
    "P2": "Womens E-Mail All",
    "P3": "Uniform Random",
}
PROBABILITIES = ((1, 0, 0), (0, 1, 0), (0, 0, 1), (1 / 3,) * 3)
OUTCOMES = ("conversion", "visit", "spend")
UNITS = {
    "conversion": {"absolute": "%", "incremental": "pp"},
    "visit": {"absolute": "%", "incremental": "pp"},
    "spend": {"absolute": "USD/customer", "incremental": "USD/customer"},
}


def metadata():
    return {
        "fixture_id": FIXTURE_ID,
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "seed": SEED,
        "n": N,
        "source_origin": "SYNTHETIC",
        "arms": list(ARMS),
        "logging_propensity": [1 / 3] * 3,
        "policy_definitions": {
            key: {"label": label, "action_probabilities": list(weights)}
            for (key, label), weights in zip(POLICIES.items(), PROBABILITIES)
        },
        "outcome_definitions": {
            "conversion": {"type": "binary", "probabilities": [0.10, 0.16, 0.13]},
            "visit": {"type": "binary", "probabilities": [0.20, 0.26, 0.23],
                      "shared_uniform_with_conversion": True},
            "spend": {"type": "USD", "nonbuyer": 0, "buyer_distribution": "exponential",
                      "buyer_mean_usd": 50, "resolution_usd": 0.01},
        },
        "unit_definitions": UNITS,
    }


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def content_hash(payload):
    return hashlib.sha256(canonical(payload)).hexdigest()


def encode_fixture(payload):
    return json.dumps(
        {"payload": payload, "content_sha256": content_hash(payload)},
        indent=2, sort_keys=True, allow_nan=False,
    ).encode("ascii") + b"\n"


def load_fixture():
    """Load the single bundled fixture. No caller-supplied path or data source."""
    document = json.loads(FIXTURE_PATH.read_bytes())
    payload = document["payload"]
    if (payload["metadata"] != metadata()
            or document["content_sha256"] != EXPECTED_CONTENT_SHA256
            or content_hash(payload) != EXPECTED_CONTENT_SHA256):
        raise ValueError("Day 14 synthetic fixture contract mismatch")
    return payload
