# Day 14 합성 대시보드 설계

Day 14는 합성 무작위 실험과 고정 정책의 추정·표시 경로를 검증한다. Overview, Synthetic Experiment, Synthetic Policy Evaluation, Methodology & Limitations 탭에 SYNTHETIC 출처를 표시한다. Outcome 선택기는 저장된 집계를 전환한다. 절대 가치와 P0 대비 차이를 별도 표로 배치해 %와 pp를 구분했다. 차트는 작은 화면에서도 행 이름을 읽을 수 있도록 가로 배치했고, P0 대비 차이에는 점과 CI를 표시했다.

## Fixture 계약

| 항목 | 값 |
|---|---|
| Fixture ID | `day14-email-lab-synthetic-v1` |
| Schema / generator | `1` / `python-mt19937-cent-v1` |
| Seed / 표본 | `20261109` / 12,909 |
| Source | SYNTHETIC |
| 행 배정 | No E-Mail, Mens E-Mail, Womens E-Mail에 독립 균등 배정 |
| Conversion / Visit | 0.10/0.16/0.13과 0.20/0.26/0.23. 한 행에서 같은 균등 난수를 사용해 구매가 방문에 포함된다. |
| Spend | 구매 시 평균 50 USD인 지수분포를 센트 단위로 반올림. 미구매는 0 USD. |
| 정책 | P0 No E-Mail All, P1 Mens E-Mail All, P2 Womens E-Mail All, P3 Uniform Random |
| 단위 | 전환·방문 절대 수준은 %, 차이는 percentage point(pp). 매출은 USD/customer. |

Day 11의 개념적 설계를 참고하되 Day 14는 표준 라이브러리의 MT19937과 센트 단위 매출을 사용하는 별도 표본이다. 이전 집계 파일이나 Release Runner는 생성기 입력에서 제외한다. 행 식별자를 만들지 않고 배정군별 수·합·제곱합만 누적한다. 앱은 같은 디렉터리의 고정 JSON 한 개에서 3개 군 집계와 정책 절대·증분 집계 21행을 읽는다. 정렬된 compact JSON payload의 SHA-256을 코드에 고정하고 metadata도 검증한다. 생성 시각은 별도 실행 metadata에 기록한다. Git은 이 JSON에 LF를 적용하도록 설정한다.

## 추정 및 해석

배정군 내 관측 평균과 No E-Mail 대비 ITT 차이를 확인한다. 정책 가치는 알려진 배정 확률 `1/3`을 분모로 하는 Horvitz–Thompson IPS로 추정한다. 각 행의 score는 `q(A) * Y / (1/3)`이다. P3의 절대 score는 관측 outcome과 같고, P3 절대 가치는 P0~P2 추정값의 평균이다. P0 대비 추정량은 같은 행의 두 score 차이를 먼저 계산해 공분산을 보존한다.

표준오차는 IID 표본분산을 사용하고 정규근사 양측 검정과 pointwise 95% CI를 보고한다. Holm 보정은 conversion 대비 3개(Primary3), visit·spend 대비 6개(Secondary6)를 별도로 적용한다. CI는 동시 신뢰구간이 아니다. P0 자체는 기준이라 대비 검정을 만들지 않는다. 단일 합성 표본이며 실제 실험의 표본 오차나 매출 꼬리의 타당성을 검증하지 않는다. 실제 비용·마진은 미설정이고, Holdout은 미평가이며, T-Learner INCONCLUSIVE와 calibration METHOD_NOT_VALIDATED를 유지한다.

## 실행 경계

앱은 로컬 설정을 통해 loopback으로 바인딩하고 Streamlit 사용량 통계를 끈다. 차트 데이터는 로컬 Arrow payload로 내장된다. 파일이나 경로 선택, 고객별 데이터, 실제 승인·정책 실행과 데이터 전송은 앱 기능의 범위 밖이다. 앱과 테스트의 입력 경계는 [합성 CI 문서](DAY14_SYNTHETIC_CI.md)에 기록했다. 실행 명령은 [대시보드 가이드](../dashboard/README.md)에 있다.
