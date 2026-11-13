# 합성 이메일 실험 대시보드 (Synthetic-only Dashboard)

Day 14 로컬 시연입니다. Overview, Synthetic Experiment, Synthetic Policy Evaluation, Methodology & Limitations 탭을 제공합니다. 두 Outcome 선택기는 번들에 포함된 합성 집계의 표시만 변경합니다.

프로젝트 루트에서 실행합니다. 로컬 검증 환경은 Windows의 Python 3.11.5입니다.

```powershell
python -m venv artifacts/day14_dashboard_env
$dashPython = ".\artifacts\day14_dashboard_env\Scripts\python.exe"
& $dashPython -m pip install -r requirements-dashboard.txt
& $dashPython -m streamlit run dashboard/app.py
```

브라우저에서 `http://127.0.0.1:8501`을 엽니다. 실행 설정은 loopback 및 headless 모드와 사용량 통계 비활성화를 지정합니다. 패키지 설치는 의존성을 내려받고, 앱 실행은 번들 fixture와 로컬 브라우저 연결을 사용합니다.

데이터 없는 테스트 트리를 만들려면 프로젝트 루트에서 다음을 실행합니다. 반복할 때는 새 출력 디렉터리를 지정합니다.

```powershell
& $dashPython -I -B scripts/verify_data_free_dashboard.py --output artifacts/day14_dashboard_check
```

합성 fixture를 별도 파일로 재생성할 수 있습니다.

```powershell
& $dashPython -B -m dashboard.synthetic_data --output artifacts/day14_regenerated.json
Get-FileHash dashboard/synthetic_fixture.json, artifacts/day14_regenerated.json -Algorithm SHA256
```

합성 지표는 시연용입니다. 실제 Holdout 정책 성과는 미평가이며 실제 발송 비용과 마진은 미설정입니다. 설계와 검증 범위는 프로젝트의 Day 14 문서에 기록했습니다.
