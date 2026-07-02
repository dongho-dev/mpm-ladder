# MPM Ladder

[English](README.en.md)

워크플로우별 Minimum Pass Model(MPM)을 측정하고, 더 낮은 모델에서도 통과하도록 개선 과정을 추적하는 CLI입니다.

MPM Ladder의 핵심 질문은 다음입니다.

```text
이 워크플로우를 안정적으로 완료할 수 있는 최소 실행자 tier는 무엇인가?
```

이 질문은 문서, SOP, CI 복구, 배포, 마이그레이션, 혼합 자동화 워크플로우에 적용됩니다. Documentation MPM은 더 큰 Workflow MPM 문제의 한 부분입니다.

MPM Ladder는 local-first 제품입니다. 고객의 워크플로우 정의, trace, run log, report는 고객 repository, CI artifact store, 온프레미스 workspace 안에 남길 수 있습니다. 현재 MVP는 hosted data plane 대신 plain file 기반 workspace를 기본값으로 사용합니다.

## 핵심 개념

- **MPM**: Minimum Passing Model 또는 최소 통과 실행자 tier.
- **Workflow MPM**: docs, scripts, rules, tools, gates, agent decisions를 포함한 전체 작업 시스템을 완료하는 데 필요한 최소 판단 tier.
- **Documentation MPM**: 문서를 읽고 따르는 데 필요한 최소 판단 tier.
- **AFR**: Actionable Failure Rate. 유용한 workflow 개선으로 이어지는 실패 비율.
- **cost/success**: 전체 model spend를 성공 attempt 수로 나눈 값.
- **cost/useful-failure**: 전체 model spend를 actionable failure 수로 나눈 값.

## Tier Ladder

기본 샘플 ladder는 `data/models.json`에서 수정할 수 있습니다.

```text
T0  Oracle / frontier executor
T1  Senior executor
T2  Balanced worker
T3  Cheap worker
T4  Nano/local/script-adjacent worker
```

워크플로우 단계는 non-model executor도 사용할 수 있습니다.

```text
script
rule
ci
human
```

## 빠른 시작

```powershell
python -m mpm_ladder prices --input-tokens 100000 --output-tokens 20000
python -m mpm_ladder evaluate
python -m mpm_ladder evaluate --workspace .\.mpm-ladder\workspace.json --workflow-id ci-recovery --min-pass-rate 0.9 --min-attempts 3
python -m mpm_ladder workflows
python -m mpm_ladder snapshot --workflow-id ci-recovery --note "Updated runbook"
python -m mpm_ladder report --workspace .\.mpm-ladder\workspace.json --workflow-id ci-recovery --format markdown
python -m unittest discover -s tests
```

첫 번째 명령은 일반적인 SOP/agent run의 비용 ladder를 출력합니다. 두 번째 명령은 샘플 CI recovery workflow와 샘플 run log를 평가합니다.

## 로컬 대시보드

```powershell
powershell -ExecutionPolicy Bypass -File .\dashboard\serve.ps1
```

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:8787/dashboard/index.html
```

대시보드는 `.mpm-ladder/workspace.json`을 읽고, workflow를 선택한 뒤 semantic task definition과 측정된 MPM report를 함께 보여줍니다.

## 출력 예시

```text
Version:      2026-07-02T000000Z
Observed MPM: T3 via gpt-5.4-mini
Reliable MPM: T0 via gpt-5.5
Target MPM:   T2 (not met)
Automation:   3/6 automated steps
Agent steps:  2/6
Human gates:  1/6
```

## 프로젝트 구조

```text
PROJECT_MEMORY.md                  제품 맥락과 설계 메모
dashboard/                         재사용 가능한 한국어 웹 대시보드
data/models.json                   모델 tier와 가격
data/objective_profiles.json       objective profile preset
.mpm-ladder/workspace.json         로컬 workflow registry
examples/workflows/ci-recovery.json  샘플 workflow 정의
examples/runs/ci-recovery-runs.json  샘플 benchmark attempts
mpm_ladder/                        CLI와 scoring logic
tests/                             표준 라이브러리 테스트
```

## 현재 MVP 기능

1. 입력/출력 token profile 기반 per-run cost 계산.
2. 가장 저렴한 후보 대비 모델별 cost multiplier 비교.
3. pass@N, cost/success, failure labels, AFR 집계.
4. 성공 run log에서 observed MPM 계산.
5. workflow automation coverage와 model capability 분리.
6. minimum pass-rate와 attempt threshold 기반 reliable MPM 계산.
7. semantic workflow를 local workspace registry에 등록.
8. 측정 결과를 workflow version과 report scoring metadata에 연결.
9. workspace manifest를 통해 데이터를 교체하는 local Korean dashboard 제공.

## 다음 단계

- 실제 executor adapter 추가: OpenAI, Claude, local model, shell-only replay.
- 실제 workflow run trace 저장.
- workflow-level MPM뿐 아니라 per-step MPM 추가.
- prompt caching과 batch pricing profile 추가.
- 반복 SOP benchmark run을 위한 CI template 추가.
