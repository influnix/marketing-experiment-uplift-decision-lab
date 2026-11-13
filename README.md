# Marketing Experiment & Uplift Decision Lab

고정 합성 표본으로 이메일 실험과 발송 정책 평가를 시연합니다. Overview와 Synthetic Experiment에서 세 배정군과 관측 평균을 확인하고, Synthetic Policy Evaluation에서 P0~P3의 가치와 P0 대비 차이를 Conversion·Visit·Spend별로 비교할 수 있습니다. Methodology & Limitations는 추정 방법과 해석 범위를 설명합니다. 화면의 모든 성과는 **SYNTHETIC**이며 실제 Holdout과 실제 ROI는 미평가입니다.

검증한 환경은 Windows, Python 3.11.5, Streamlit 1.67.0입니다. 저장소 루트에서 실행합니다.

```powershell
python -m venv artifacts/dashboard_env
$dashPython = ".\artifacts\dashboard_env\Scripts\python.exe"
& $dashPython -m pip install -r requirements-dashboard.txt
& $dashPython -m streamlit run dashboard/app.py
```

브라우저에서 `http://127.0.0.1:8501`을 엽니다. 데이터 없는 검증은 서버 종료 후 또는 별도 PowerShell 세션에서 같은 가상환경으로 실행합니다.

```powershell
& .\artifacts\dashboard_env\Scripts\python.exe -I -B scripts/verify_data_free_dashboard.py --output artifacts/dashboard_check
```

반복할 때는 새 출력 경로를 지정합니다. [대시보드 실행·검증 가이드](dashboard/README.md) · [합성 CI 범위](docs/DAY14_SYNTHETIC_CI.md)

Fixture `day14-email-lab-synthetic-v1`(schema 1)은 seed `20261109`의 합성 표본 12,909개를 집계한 것입니다. 콘텐츠 SHA-256은 `4508bd68cd83907a835642075e14fb20c5c11c5ded794358e18397c6a5e38ba0`, 파일 SHA-256은 `9ae99ded05c4b2123a9abb5984a34de78813f8212ac886270daed77dad040b58`입니다. 로컬 재현 범위는 고정 fixture, 합성 계약과 AppTest입니다.

Day 18에서 정책 캡션 대비 수정 후 Chrome 및 Windows Playwright WebKit 각각 다섯 Viewport의 화면 회귀를 확인했고, 정책 캡션 대비는 5.6910:1이었습니다. 실제 iPhone Safari, iOS Simulator, Linux 및 원격 GitHub CI는 미검증입니다. [브라우저 검증 방법](docs/DAY15_BROWSER_QA.md)

포함된 집계의 출처는 합성 생성기입니다. 원본 고객 데이터의 출처·재배포 권리를 이 시연으로 검증할 수 없으며, 후보 코드·문서의 저작권·라이선스 검토도 대기 중입니다. 실제 Publication은 `REVIEW_REQUIRED`, 승인된 공개 파일은 0개, 실제 Export는 비활성입니다.
