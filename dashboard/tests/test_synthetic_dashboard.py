import ast
import json
from pathlib import Path
import tomllib

import pyarrow.ipc
import pytest
import streamlit
from streamlit.testing.v1 import AppTest

from dashboard.synthetic_contract import FIXTURE_ID, load_fixture

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "dashboard/app.py"


@pytest.fixture
def view():
    return AppTest.from_file(str(APP), default_timeout=20).run()


def test_initial_view_and_input_surface(view):
    assert not view.exception
    assert [t.label for t in view.tabs] == [
        "Overview", "Synthetic Experiment", "Synthetic Policy Evaluation", "Methodology & Limitations",
    ]
    assert "SYNTHETIC" in view.info[0].value
    assert all(any("SYNTHETIC" in c.value for c in tab.caption) or tab.info for tab in view.tabs)
    assert FIXTURE_ID in view.tabs[0].caption[0].value
    assert {m.label: m.value for m in view.metric} == {"합성 표본": "12,909", "무작위 배정군": "3", "고정 정책": "4"}
    text = " ".join(m.value for m in view.markdown)
    assert "NOT_EVALUATED" in text and "INCONCLUSIVE" in text and "METHOD_NOT_VALIDATED" in text
    assert "ROI" not in text
    assert {w.key for w in view.radio} == {"experiment_outcome", "policy_outcome"}
    for control in ("file_uploader", "text_input", "selectbox", "download_button", "button", "form", "chat_input"):
        assert not view.get(control)
    assert streamlit.get_option("browser.gatherUsageStats") is False


def chart_payload(chart):
    # AppTest exposes the serialized chart proto, not the browser-rendered chart.
    spec = json.loads(chart.proto.spec)
    assert "data" not in spec  # All points are embedded locally as Arrow IPC bytes.
    return spec, pyarrow.ipc.open_stream(chart.proto.data.data).read_all().to_pylist()


@pytest.mark.parametrize(("outcome", "absolute_unit", "delta_unit"), [
    ("conversion", "%", "pp"), ("visit", "%", "pp"), ("spend", "USD/customer", "USD/customer"),
])
def test_app_tables_and_chart_payload(view, outcome, absolute_unit, delta_unit):
    view.radio(key="experiment_outcome").set_value(outcome)
    view.radio(key="policy_outcome").set_value(outcome)
    view.run()
    assert not view.exception
    fixture = load_fixture()
    arm_table, values, deltas = (e.value for e in view.table)
    arm_chart, policy_chart = view.get("vega_lite_chart")
    arm_spec, arm_data = chart_payload(arm_chart)
    policy_spec, policy_data = chart_payload(policy_chart)
    assert arm_spec["encoding"]["x"]["title"].endswith(f"({absolute_unit})")
    assert policy_spec["layer"][1]["encoding"]["x"]["title"] == f"P0 대비 차이 ({delta_unit})"
    for arm, plotted in zip(fixture["arm_results"], arm_data, strict=True):
        assert arm_table.loc[arm["arm"], "표본"] == arm["n"]
        for key, title in (("conversion", "Conversion (%)"), ("visit", "Visit (%)"), ("spend", "Spend (USD/customer)")):
            assert arm_table.loc[arm["arm"], title] == f"{arm[key]:.3f}"
        assert plotted["arm"] == arm["arm"]
        assert plotted["estimate"] == round(arm[outcome], 3)
    policy_meta = fixture["metadata"]["policy_definitions"]
    family = "Primary3" if outcome == "conversion" else "Secondary6"
    for row in (r for r in fixture["policy_results"] if r["outcome"] == outcome):
        policy = row["policy"]
        expected_ci = f"[{row['low']:.3f}, {row['high']:.3f}]"
        if row["kind"] == "absolute":
            label = f"{policy} · {policy_meta[policy]['label']}"
            assert values.loc[label, f"가치 ({absolute_unit})"] == f"{row['estimate']:.3f}"
            assert values.loc[label, f"95% CI ({absolute_unit})"] == expected_ci
        else:
            assert deltas.loc[policy, f"P0 대비 차이 ({delta_unit})"] == f"{row['estimate']:.3f}"
            assert deltas.loc[policy, f"95% CI ({delta_unit})"] == expected_ci
            assert deltas.loc[policy, "Raw p"] == f"{row['p_value']:.3g}"
            assert deltas.loc[policy, f"Holm p ({family})"] == f"{row['p_holm']:.3g}"
            plot = next(r for r in policy_data if r["policy"] == policy)
            assert [plot[k] for k in ("low", "estimate", "high")] == [
                round(row[k], 3) for k in ("low", "estimate", "high")
            ]


def test_static_dependencies_and_documented_entry_points():
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    imports = {name.name for node in ast.walk(tree) if isinstance(node, ast.Import) for name in node.names}
    imports |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports == {"pandas", "streamlit", "dashboard.synthetic_contract"}
    config = tomllib.loads((ROOT / ".streamlit/config.toml").read_text(encoding="utf-8"))
    assert config["browser"]["gatherUsageStats"] is False
    assert config["secrets"]["files"] == []
    assert config["server"]["address"] == "127.0.0.1"
    readme = (ROOT / "dashboard/README.md").read_text(encoding="utf-8")
    assert "-m streamlit run dashboard/app.py" in readme
    assert "scripts/verify_data_free_dashboard.py" in readme
    assert "requirements-dashboard.txt" in readme
