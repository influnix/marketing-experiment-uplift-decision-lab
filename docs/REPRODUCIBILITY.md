# 실행과 재현 범위

설치와 첫 실행은 [프로젝트 빠른 시작](../README.md#실행)을 따릅니다. Streamlit의 네 화면은 저장소 안의 고정 합성 집계만 읽습니다. Windows 및 Ubuntu에서 Python 3.11.5로 검증했습니다. 앱·테스트의 직접 의존성은 `requirements-dashboard.txt`에 고정돼 있습니다. 원격 CI의 설치 단계에서 전이 의존성의 실제 버전을 기록합니다.

## 고정 합성 집계

| 항목 | 값 |
|---|---|
| ID / 스키마 | `day14-email-lab-synthetic-v1` / 1 |
| 생성기 / seed | `python-mt19937-cent-v1` / `20261109` |
| 표본 / 출처 | 12,909 / SYNTHETIC |
| 콘텐츠 SHA-256 | `4508bd68cd83907a835642075e14fb20c5c11c5ded794358e18397c6a5e38ba0` |
| 파일 SHA-256 | `9ae99ded05c4b2123a9abb5984a34de78813f8212ac886270daed77dad040b58` |

저장 파일에는 세 실험군과 정책 비교의 집계만 있습니다. 앱 로더가 데이터 계약과 canonical JSON 콘텐츠 SHA를 확인하고, 테스트는 생성기의 결과를 동결된 파일과 바이트 단위로 비교합니다. 파일의 LF 줄바꿈은 Git 속성으로 고정합니다.

## 데이터 없는 테스트

[상세 실행 가이드](../dashboard/README.md)에 테스트와 별도 fixture 재생성 명령이 있습니다. 테스트 실행기는 지정 파일만 별도 디렉터리로 복사해 고정 계약, 정책 산술과 Holm 보정, Streamlit AppTest, 세 지표의 표·차트 값 및 단위를 검사합니다. 분석 패키지 import, 금지 데이터 경로 접근과 외부 소켓 접근을 테스트 프로세스의 Python audit hook에서 점검합니다. 이 검사 범위는 OS 전체를 감시하지 않습니다.

[Synthetic dashboard](https://github.com/influnix/marketing-experiment-uplift-decision-lab/actions/workflows/synthetic-ci.yml)는 Ubuntu에서 같은 합성 테스트 두 파일만 실행합니다. 설정은 읽기 전용 권한을 사용하며 관련 경로의 PR 또는 수동 실행을 지원합니다. Push 자체는 트리거가 아닙니다.

## 브라우저 검증

기존 QA는 Chrome과 Windows Playwright WebKit에서 375×812, 390×844, 768×1024, 1366×768, 1440×900의 다섯 크기를 확인했습니다. 탭과 선택기, 표 스크롤, 수치 및 CI 표시를 검사했습니다. 정책 상·하단 캡션은 두 엔진의 세 지표와 다섯 크기에서 5.691:1 대비가 측정됐습니다. 실제 iPhone Safari와 앱 전체 접근성은 별도 검증 범위입니다.

선택 사항으로 Windows에서 로컬 브라우저 검사를 반복할 수 있습니다. 아래 명령은 앱 환경 `.venv`와 설치된 Chrome을 사용합니다. WebKit을 실행하려면 별도 환경에서 `-m playwright install webkit`으로 엔진을 설치하고 마지막 명령의 `--engine chromium`을 `--engine webkit`으로 바꿉니다. 출력 경로는 엔진별로 새 경로를 지정합니다.

```powershell
python -m venv artifacts/browser-env
$browserPython = ".\artifacts\browser-env\Scripts\python.exe"
& $browserPython -m pip install playwright==1.57.0
& $browserPython -I -B scripts/verify_dashboard_browser.py --engine chromium --server-python .venv/Scripts/python.exe --output artifacts/browser-check
```

재현할 수 있는 범위는 합성 앱과 그 검증입니다. 실제 실험 데이터, 고객별 모델, 비용 가정, Holdout 평가 결과는 제공되지 않습니다.
