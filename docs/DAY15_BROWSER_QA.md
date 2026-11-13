# Day 15 로컬 브라우저 검증 절차

고정 Day 14 fixture를 읽는 Streamlit 1.67.0 서버를 loopback에서 띄운 뒤, Playwright 1.57.0으로 설치된 Chrome을 headless 모드에서 제어한다. 375×812, 390×844, 768×1024는 모바일 터치를 에뮬레이션한다. 1366×768, 1440×900은 마우스를 사용한다. 각 Viewport에 새 브라우저 컨텍스트를 만든다. 실제 단말과 브라우저 엔진 교차 검증은 별도다. [Playwright BrowserType](https://playwright.dev/python/docs/api/class-browsertype)

프로젝트 루트에서 실행한다. Day 14 환경과 설치된 Chrome을 사용하고, Playwright만 별도 환경에 설치한다.

```powershell
python -m venv artifacts/day15/browser-venv
$browserPython = ".\artifacts\day15\browser-venv\Scripts\python.exe"
& $browserPython -m pip install playwright==1.57.0
& $browserPython -I -B scripts/verify_dashboard_browser.py --server-python artifacts/day14/venv/Scripts/python.exe --output artifacts/day15/new_browser_run
```

기본 주소는 `http://127.0.0.1:8501`이다. 이미 사용 중이면 `--port`에 다른 로컬 포트를 지정한다. 반복 실행은 새 출력 디렉터리를 사용한다.

실행기는 허용 목록의 설정·앱·계약·fixture·검증 코드만 새 트리에 복사한다. Fixture 파일 바이트와 canonical payload의 SHA-256을 확인한 뒤, 데이터 경로·분석 패키지 import·외부 Python 소켓을 감시하는 서버를 시작한다. 브라우저는 새 세션에서 동일 loopback의 HTTP 및 WebSocket만 허용한다. 외부 요청은 페이지 경계에서 기록하고 차단한다. 브라우저 서비스 워커를 끄고 설치된 Chrome의 기존 프로필은 사용하지 않는다. 이 증거는 테스트 페이지와 Python 서버의 기록이며 OS 전체 네트워크 감시가 아니다.

검증 순서는 Overview 초기화, 실험 탭의 Conversion·Visit·Spend, 정책 탭의 동일한 세 지표, 방법론, Overview 복귀 및 새로고침이다. 각 화면에서 고정 fixture와 테이블의 행과 열을 대조하고 SVG의 축·마크·CI 범위를 확인한다. Viewport 전체와 Streamlit main의 가로 폭, 탭과 KPI의 Bounding Box, 모바일 44px 터치 영역, 표의 마지막 열까지 스크롤, CI·지수 표기의 줄바꿈, 필요한 곳의 세로 스크롤을 검사한다. 콘솔 오류, 앱 예외, HTTP 오류 및 외부 요청 시도는 실패로 기록한다.

`browser_matrix.json`에는 Viewport별 단계·단위·표·차트·레이아웃·통신과 스크린샷 SHA가 있다. PNG는 각 탭의 상단 Viewport, 차트별 캡처, 긴 표의 스크롤 위치, 모바일 방법론 하단을 포함한다. Streamlit의 내부 세로 스크롤 영역은 한 장에 합치지 않았다. 이미지 검토 기록은 자동 DOM 검사와 별도로 보존한다. [Playwright Screenshots](https://playwright.dev/python/docs/screenshots)

기존 Synthetic-only CI는 Python 3.11.5와 dashboard 의존성을 사용해 AppTest 및 fixture 계약 두 파일을 테스트한다. `contents: read`와 checkout 자격증명 미보존을 유지한다. `dashboard/**` PR 경로에는 fixture 및 UI 변경이 포함된다. `pull_request`와 `workflow_dispatch`를 유지하고 main push trigger는 원격 실행 정책이 정해질 때 별도로 결정한다. 현재 브라우저 QA는 로컬 실행이며 CI에는 Chrome과 Playwright 설치를 추가하지 않았다. [기존 CI 범위](DAY14_SYNTHETIC_CI.md)
