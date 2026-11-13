# Day 14 합성 전용 CI

`.github/workflows/synthetic-ci.yml`은 수동 또는 관련 경로 PR에서 실행한다. GitHub 호스트의 Ubuntu 24.04와 Python 3.11.5를 설정하고 `requirements-dashboard.txt`를 설치한다. `pip check`와 `pip freeze`로 환경과 해결된 패키지 버전을 남긴다. 권한은 `contents: read`이며 checkout 자격증명을 보존하지 않는다. 프로젝트 데이터를 받는 단계나 Secret 참조는 없다. [GitHub Actions Python 가이드](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)

로컬과 CI가 같은 명령을 사용한다. 출력에는 존재하지 않는 새 디렉터리를 지정한다.

```powershell
& $dashPython -I -B scripts/verify_data_free_dashboard.py --output artifacts/day14_dashboard_check
```

복사 허용 목록은 dashboard 코드·fixture·대시보드 README·테스트·설정·테스트 실행기 11개 파일이다. 복사 직후 파일 목록과 해시를 기록하고 해당 트리에서 격리 Python 프로세스를 시작한다. pytest는 전용 설정과 아래 두 파일만 사용한다.

- `dashboard/tests/test_synthetic_contract.py`: 고정 fixture 재생성, 입력 계약, 정책 산술, paired CI 및 Holm family.
- `dashboard/tests/test_synthetic_dashboard.py`: AppTest 초기 실행과 위젯, 세 outcome 전환, 표/Arrow 차트 payload, 단위 및 경계, 정적 import·설정·실행 명령 점검.

테스트 프로세스의 Python audit hook은 실제 데이터 경로, 비공개 입력, 분석 패키지 import 및 외부 소켓 접근 시도를 기록하고 차단한다. Windows asyncio의 내부 IPv4/IPv6 loopback 연결은 허용한다. AppTest는 Streamlit 요소와 직렬화된 차트 payload를 검증한다. Python hook은 OS·브라우저 전체 계측이 아니며 화면 픽셀과 모바일 레이아웃은 별도 브라우저 확인 대상이다. [Streamlit AppTest 문서](https://docs.streamlit.io/develop/concepts/app-testing/cheat-sheet)

현재 상태는 **CONFIGURED / LOCAL_EQUIVALENT_TESTED / CI_CONFIGURED_NOT_REMOTE_VALIDATED**다. Windows에서 동일한 시험 절차를 통과했다. Ubuntu 원격 job, 원격 checkout 및 원격 의존성 해결은 미검증이다. 현재 Publish 및 Holdout 판정은 이 CI의 범위와 독립적이다.
