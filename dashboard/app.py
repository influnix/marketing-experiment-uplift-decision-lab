"""Read-only Streamlit view of the Day 14 aggregate fixture."""

import pandas as pd
import streamlit as st

from dashboard.synthetic_contract import ARMS, N, POLICIES, UNITS, load_fixture

LABELS = {"conversion": "Conversion", "visit": "Visit", "spend": "Spend"}
RESPONSIVE_STYLES = """
<style>
  .st-key-policy_caption_top [data-testid="stCaptionContainer"],
  .st-key-policy_caption_bottom [data-testid="stCaptionContainer"] { opacity: .7; }
  .day15-table-help { display: none; }
  @media (max-width: 800px) {
    [data-testid="stRadio"] [role="radiogroup"] label {
      min-height: 44px; min-width: 44px; padding-inline: .25rem;
    }
  }
  @media (max-width: 640px) {
    [data-testid="stMainBlockContainer"] { padding-top: 3.5rem; }
    [data-testid="stMain"] :is(h1, h2, h3, p) { word-break: keep-all; }
    [data-testid="stMain"] h1 { font-size: 2rem; line-height: 1.2; }
    [data-testid="stMain"] h3 { font-size: 1.4rem; }
    [data-testid="stTabs"] [role="tablist"] {
      display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: .375rem; overflow: visible; border: 0;
    }
    [data-testid="stTabs"] [role="tab"] {
      min-width: 0; min-height: 44px; height: auto; white-space: normal;
      justify-content: center; padding: .375rem .25rem; border-radius: .375rem;
      border: 1px solid #d7e2e8; text-align: center;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
      background: #e4f2ef; color: #075e57; border-color: #087b71;
    }
    [data-testid="stTabs"] :is([data-baseweb="tab-highlight"], [data-baseweb="tab-border"]) { display: none; }
    .st-key-overview_kpis [data-testid="stHorizontalBlock"] { flex-wrap: nowrap; gap: .5rem; }
    .st-key-overview_kpis [data-testid="stColumn"] { flex: 1 1 0; min-width: 0; width: auto; }
    .st-key-overview_kpis [data-testid="stMetricValue"] { font-size: 1.5rem; }
    [data-testid="stTable"] table:has(thead th:nth-child(5)) { min-width: 30rem; }
    [data-testid="stTable"] td [data-testid="stMarkdownContainer"] p {
      white-space: nowrap; overflow-wrap: normal; word-break: normal;
    }
    [data-testid="stTable"] th [data-testid="stMarkdownContainer"] p { word-break: keep-all; }
    .day15-table-help { display: block; color: #506779; font-size: .8rem; }
  }
</style>
"""
CHART_OPTIONS = {
    "autosize": {"type": "fit-x", "contains": "padding"},
    "usermeta": {"embedOptions": {"renderer": "svg"}},
}
TABLE_SCROLL_HELP = '<div class="day15-table-help">표를 좌우로 밀어 모든 열을 볼 수 있습니다.</div>'


def value(value):
    return "—" if value is None else f"{value:.3f}"


def p_value(value):
    return "—" if value is None else f"{value:.3g}"


def interval(row):
    return "—" if row is None else f"[{value(row['low'])}, {value(row['high'])}]"


def outcome_picker(key):
    return st.radio("Outcome", tuple(LABELS), format_func=LABELS.get, horizontal=True, key=key)


def overview(meta):
    st.info("SYNTHETIC · 무작위 이메일 실험과 고정 정책 평가를 시연합니다.")
    with st.container(key="overview_kpis"):
        for column, label, metric in zip(
            st.columns(3), ("합성 표본", "무작위 배정군", "고정 정책"), (f"{N:,}", "3", "4"),
        ):
            column.metric(label, metric)
    st.write("**실험군** · " + " / ".join(ARMS))
    st.write("**표시 지표** · Conversion, Visit, Spend")
    st.write("**실제 Holdout** · NOT_EVALUATED")
    st.caption(f"Fixture · {meta['fixture_id']} | seed {meta['seed']}")


def experiment(rows):
    st.subheader("실험군별 관측 평균")
    st.caption("SYNTHETIC · 배정군 안의 평균과 No E-Mail 대비 차이")
    outcome = outcome_picker("experiment_outcome")
    unit = UNITS[outcome]["absolute"]
    delta_unit = UNITS[outcome]["incremental"]
    baseline = rows[0][outcome]
    chart_data = [
        {"arm": r["arm"], "estimate": round(r[outcome], 3), "gap": round(r[outcome] - baseline, 3),
         "description": f"{r['arm']} · {LABELS[outcome]} {r[outcome]:.3f} {unit}"}
        for r in rows
    ]
    st.vega_lite_chart(spec={
        **CHART_OPTIONS,
        "data": {"values": chart_data},
        "mark": {"type": "bar", "color": "#087B71", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {"field": "estimate", "type": "quantitative", "title": f"{LABELS[outcome]} ({unit})",
                  "scale": {"domain": [0, max(r["estimate"] for r in chart_data) * 1.08]},
                  "axis": {"tickCount": 6}},
            "y": {"field": "arm", "type": "nominal", "sort": list(ARMS), "title": None},
            "description": {"field": "description", "type": "nominal"},
            "tooltip": [
                {"field": "arm", "type": "nominal", "title": "배정군"},
                {"field": "estimate", "type": "quantitative", "format": ".3f", "title": f"평균 ({unit})"},
                {"field": "gap", "type": "quantitative", "format": ".3f",
                 "title": f"No E-Mail 대비 ({delta_unit})"},
            ],
        },
    }, width="stretch")
    st.html(TABLE_SCROLL_HELP)
    st.table(pd.DataFrame([
        {"배정군": r["arm"], "표본": r["n"], "Conversion (%)": value(r["conversion"]),
         "Visit (%)": value(r["visit"]), "Spend (USD/customer)": value(r["spend"])}
        for r in rows
    ]).set_index("배정군"))


def policy_evaluation(rows, n):
    st.subheader("고정 정책의 가치와 P0 대비 차이")
    with st.container(key="policy_caption_top"):
        st.caption(f"SYNTHETIC · HT IPS · 합성 평가 표본 {n:,}행 · Pointwise 95% CI")
    outcome = outcome_picker("policy_outcome")
    absolute_unit = UNITS[outcome]["absolute"]
    delta_unit = UNITS[outcome]["incremental"]
    family = "Primary3" if outcome == "conversion" else "Secondary6"
    by_key = {(r["policy"], r["kind"]): r for r in rows if r["outcome"] == outcome}
    chart_data = [
        {k: round(r[k], 3) if k != "policy" else r[k] for k in ("policy", "estimate", "low", "high")}
        for (policy, kind), r in by_key.items() if kind == "incremental"
    ]
    for row in chart_data:
        row["description"] = (f"{row['policy']} · {row['estimate']:.3f} {delta_unit} · "
                              f"95% CI [{row['low']:.3f}, {row['high']:.3f}]")
    delta_axis = f"P0 대비 차이 ({delta_unit})"
    left = min(0, *(r["low"] for r in chart_data))
    right = max(0, *(r["high"] for r in chart_data))
    margin = (right - left) * .08
    scale = {"domain": [left - margin, right + margin]}
    x = {"field": "estimate", "type": "quantitative", "title": delta_axis,
         "scale": scale, "axis": {"tickCount": 6}}
    y = {"field": "policy", "type": "nominal", "sort": ["P1", "P2", "P3"], "title": None}
    st.vega_lite_chart(spec={
        **CHART_OPTIONS,
        "data": {"values": chart_data},
        "layer": [
            {"mark": {"type": "rule", "color": "#96A8B5", "strokeDash": [4, 4]},
             "encoding": {"x": {"datum": 0, "type": "quantitative", "title": delta_axis, "scale": scale}}},
            {"mark": {"type": "rule", "color": "#087B71", "strokeWidth": 2},
             "encoding": {"y": y, "x": {**x, "field": "low"}, "x2": {"field": "high"}}},
            {"mark": {"type": "point", "filled": True, "color": "#087B71", "size": 85},
             "encoding": {"x": x, "y": y, "description": {"field": "description", "type": "nominal"}, "tooltip": [
                 {"field": "policy", "type": "nominal", "title": "정책"},
                 {"field": "estimate", "type": "quantitative", "title": delta_axis, "format": ".3f"},
                 {"field": "low", "type": "quantitative", "title": "95% CI 하한", "format": ".3f"},
                 {"field": "high", "type": "quantitative", "title": "95% CI 상한", "format": ".3f"},
             ]}},
        ],
    }, width="stretch")
    values, contrasts = [], []
    for policy, label in POLICIES.items():
        absolute = by_key[policy, "absolute"]
        delta = by_key.get((policy, "incremental"))
        values.append({"정책": f"{policy} · {label}", f"가치 ({absolute_unit})": value(absolute["estimate"]),
                       f"95% CI ({absolute_unit})": interval(absolute)})
        if delta:
            contrasts.append({"정책": policy, delta_axis: value(delta["estimate"]),
                              f"95% CI ({delta_unit})": interval(delta),
                              "Raw p": p_value(delta["p_value"]), f"Holm p ({family})": p_value(delta["p_holm"])})
    st.table(pd.DataFrame(values).set_index("정책"))
    st.html(TABLE_SCROLL_HELP)
    st.table(pd.DataFrame(contrasts).set_index("정책"))
    with st.container(key="policy_caption_bottom"):
        st.caption("정책별 추정치는 하나의 합성 표본에 대한 결과입니다. 실제 캠페인에 대한 채택 근거는 아직 없습니다.")


def methodology():
    st.subheader("설계와 해석 범위")
    st.caption("SYNTHETIC · 하나의 고정 표본으로 추정 및 표시 경로 검증")
    st.markdown(
        "**3군 무작위 실험과 ITT.** 실험군 평균의 차이는 배정 기준 ITT입니다. "
        "정책 가치는 모두에게 특정 이메일을 보내거나 균등 무작위로 보내는 규칙의 평균 성과를 추정합니다.\n\n"
        "**HT IPS.** 관측 행동에서의 정책 확률을 알려진 배정 확률 1/3으로 나눈 가중치를 결과에 곱해 평균합니다. "
        "P0 대비 차이의 표준오차는 같은 행의 점수 차이로 계산해 두 정책 간 공분산을 반영합니다.\n\n"
        "**불확실성.** 정규근사의 pointwise 95% CI는 개별 비교의 구간입니다. "
        "양측 검정의 Holm 보정은 conversion 3개와 visit/spend 6개를 별도 family로 처리합니다. "
        "표시된 CI는 동시 신뢰구간이 아닙니다.\n\n"
        "**실제 평가 상태.** 발송 비용과 마진은 미설정입니다. 실제 Holdout은 NOT_EVALUATED, "
        "T-Learner는 INCONCLUSIVE, calibration은 METHOD_NOT_VALIDATED입니다."
    )


def main():
    st.set_page_config(page_title="Email Experiment Lab · SYNTHETIC", page_icon="✉️", layout="centered")
    st.html(RESPONSIVE_STYLES)
    fixture = load_fixture()
    meta = fixture["metadata"]
    st.caption("MARKETING EXPERIMENT & UPLIFT DECISION LAB  /  SYNTHETIC")
    st.title("이메일 실험과 정책 평가")
    st.write("고정 합성 표본으로 실험군의 평균과 발송 정책의 증분 가치를 비교합니다.")
    pages = st.tabs(("Overview", "Synthetic Experiment", "Synthetic Policy Evaluation", "Methodology & Limitations"))
    with pages[0]:
        overview(meta)
    with pages[1]:
        experiment(fixture["arm_results"])
    with pages[2]:
        policy_evaluation(fixture["policy_results"], meta["n"])
    with pages[3]:
        methodology()


if __name__ == "__main__":
    main()
