# Marketing Experiment & Uplift Decision Lab

**이메일 캠페인은 누구에게 보내야 하며, 발송 정책을 바꿀 만큼 충분한 근거가 있는가?**

이 프로젝트는 이메일 캠페인의 효과를 실험으로 확인하고, 그 결과를 발송 정책 결정으로 연결하는 과정을 보여 줍니다. 합성 전용 Streamlit 대시보드에서 세 실험군의 반응과 네 가지 고정 정책의 가치를 비교하고, 추정치의 불확실성까지 확인할 수 있습니다.

## 평균 효과에서 발송 결정까지

이메일을 받은 집단의 전환율이 평균적으로 높더라도, 특정 고객에게만 보내는 편이 더 나은지는 별도의 질문입니다. 구매 가능성이 높은 고객은 이메일을 받지 않아도 구매할 수 있습니다. 타기팅에 필요한 정보는 이메일을 보내 **추가로** 발생하는 구매입니다.

| 판단 단계 | 확인하는 근거 |
|---|---|
| 캠페인에 평균 효과가 있는가? | 무작위 배정군의 평균 차이(ITT)로 비발송 대비 효과를 추정합니다. |
| 효과가 고객마다 달라지는가? | 사전에 정의한 고객군의 효과 차이를 확인하고, T-Learner 같은 Uplift 모델이 그 차이를 표본 밖에서도 설명하는지 검토합니다. |
| 발송 방식을 바꿀 만한가? | 평가 전에 정책을 고정하고, 실험의 배정 확률을 반영한 정책 가치와 신뢰구간을 비교합니다. |

이 저장소에서 직접 재현할 수 있는 범위는 **합성 실험군 비교와 P0~P3 정책 평가**입니다. 고객군별 이질성 검정과 Uplift 모델은 실제 타기팅을 판단할 때 필요한 연구 단계로 설명합니다. [분석 방법](docs/METHODOLOGY.md)

## 대시보드에서 확인할 수 있는 것

- **Overview / Synthetic Experiment** — 합성 표본 12,909개와 세 무작위 배정군의 전환율, 방문율, 고객당 매출.
- **Synthetic Policy Evaluation** — 전원 비발송(P0), 두 가지 전원 발송(P1·P2), 균등 무작위(P3)의 추정 가치와 P0 대비 차이. Conversion·Visit·Spend를 바꿔 보고 95% 신뢰구간과 Holm 보정 p-value를 확인할 수 있습니다.
- **Methodology & Limitations** — 실험군 평균과 정책 가치 추정 방식, 비교 범위와 해석의 한계.

예를 들어 이 합성 표본에서 Mens 이메일 전원 발송(P1)의 전환 정책 가치는 전원 비발송보다 **5.647%p 높게 추정**됐습니다(개별 95% CI 4.132~7.162%p). 이 결과로 합성 조건에서 정책 비교가 어떻게 작동하는지 확인할 수 있습니다. 실제 고객별 타기팅 효과, Holdout 정책 가치, 비용을 반영한 ROI는 미평가입니다. [합성 결과와 한계](docs/RESULTS_AND_LIMITATIONS.md)

## 실행

검증 환경은 Python 3.11.5와 Streamlit 1.67.0입니다. 저장소 루트에서 실행합니다.

```powershell
python -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r requirements-dashboard.txt
& $python -m streamlit run dashboard/app.py
```

브라우저에서 `http://127.0.0.1:8501`을 엽니다. 서버를 종료하거나 별도 터미널에서 합성 테스트를 실행할 수 있습니다.

```powershell
& .\.venv\Scripts\python.exe -I -B scripts/verify_data_free_dashboard.py --output artifacts/synthetic-check
```

합성 계약과 화면 테스트 13개는 [최초 원격 검증](https://github.com/influnix/marketing-experiment-uplift-decision-lab/actions/runs/43347917156)에서 통과했습니다. 실행마다 검증된 커밋과 결과는 [GitHub Actions](https://github.com/influnix/marketing-experiment-uplift-decision-lab/actions)에서 확인할 수 있습니다. [재현 가이드](docs/REPRODUCIBILITY.md)

이 시연으로 비교할 수 있는 것은 정해진 네 정책의 합성 성과입니다. 실제 발송 변경을 판단하려면 타기팅 정책을 사전에 고정하고 독립 평가에서 추가 효과를 확인한 뒤, 발송 비용과 매출 마진을 함께 고려해야 합니다.
