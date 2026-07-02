# MPM 래더 대시보드

이 대시보드는 고객 로컬/온프레미스 환경 안의 `workspace.json`을 읽어 여러 워크플로우를 선택하고, 각 워크플로우의 의미 정의와 측정 결과를 함께 보여주는 정적 웹 앱입니다.

## 기본 실행

```powershell
powershell -ExecutionPolicy Bypass -File .\dashboard\serve.ps1
```

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:8787/dashboard/index.html
```

기본 워크스페이스는 다음 파일입니다.

```text
.mpm-ladder/workspace.json
```

이 파일은 모델 가격표, 워크플로우 정의, 실행 로그, 리포트 디렉터리를 연결합니다.

## 데이터 교체

대시보드 상단에서 다른 `workspace.json` 경로를 넣고 `워크스페이스 불러오기`를 누르면 같은 화면에서 다른 고객/팀/저장소의 워크플로우 registry를 렌더링합니다.

URL 파라미터로도 지정할 수 있습니다.

```text
http://127.0.0.1:8787/dashboard/index.html?workspace=../.mpm-ladder/workspace.json
```

보조 기능으로 모델 JSON, 워크플로우 JSON, 실행 로그 JSON을 직접 지정할 수도 있습니다. 서버 없이 HTML 파일을 직접 열었을 때 브라우저 보안 정책 때문에 경로 로딩이 막히면 파일 선택 입력으로 세 JSON 파일을 반영하면 됩니다.
