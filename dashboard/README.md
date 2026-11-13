# 대시보드 실행 및 검증

프로젝트 루트에서 실행합니다. Windows PowerShell 명령이며, 저장소의 고정 합성 집계를 사용합니다.

```powershell
python -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r requirements-dashboard.txt
& $python -m streamlit run dashboard/app.py
```

기본 주소는 `http://127.0.0.1:8501`입니다. 앱을 종료하거나 별도 터미널에서 아래 테스트를 실행합니다. 결과 디렉터리는 실행마다 새 이름을 사용합니다.

```powershell
& .\.venv\Scripts\python.exe -I -B scripts/verify_data_free_dashboard.py --output artifacts/synthetic-check
```

동결 파일을 유지하면서 합성 생성기를 검증하려면 별도 파일로 재생성한 뒤 SHA-256을 비교합니다.

```powershell
& .\.venv\Scripts\python.exe -B -m dashboard.synthetic_data --output artifacts/regenerated-fixture.json
Get-FileHash dashboard/synthetic_fixture.json, artifacts/regenerated-fixture.json -Algorithm SHA256
```
