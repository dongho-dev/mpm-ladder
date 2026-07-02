# MPM Ladder

MPM Ladder is a small benchmark harness for measuring how much judgment a
workflow needs.

The core question is:

```text
What is the minimum executor tier that can complete this workflow reliably?
```

This applies to documentation, SOPs, CI recovery, deployments, migrations, and
mixed automation workflows. Documentation MPM is treated as one subset of the
larger Workflow MPM problem.

MPM Ladder is local-first. Customer workflow definitions, traces, run logs, and
reports can stay inside the customer's repository, CI artifact store, or
on-premises workspace. The default MVP uses plain files rather than a hosted
data plane.

## Concepts

- **MPM**: Minimum Passing Model or minimum passing executor tier.
- **Workflow MPM**: The minimum judgment tier needed to complete a whole task
  system: docs, scripts, rules, tools, gates, and agent decisions.
- **Documentation MPM**: The minimum judgment tier needed to follow a document.
- **AFR**: Actionable Failure Rate, or failures that create a useful workflow
  improvement divided by all failures.
- **cost/success**: Total model spend divided by successful attempts.
- **cost/useful-failure**: Total model spend divided by actionable failures.

## Tier Ladder

The default sample ladder is editable in `data/models.json`.

```text
T0  Oracle / frontier executor
T1  Senior executor
T2  Balanced worker
T3  Cheap worker
T4  Nano/local/script-adjacent worker
```

Workflow steps can also use non-model executors:

```text
script
rule
ci
human
```

## Quick Start

From this repository:

```powershell
python -m mpm_ladder prices --input-tokens 100000 --output-tokens 20000
python -m mpm_ladder evaluate
python -m mpm_ladder evaluate --workspace .\.mpm-ladder\workspace.json --workflow-id ci-recovery --min-pass-rate 0.9 --min-attempts 3
python -m mpm_ladder workflows
python -m mpm_ladder snapshot --workflow-id ci-recovery --note "Updated runbook"
python -m mpm_ladder report --workspace .\.mpm-ladder\workspace.json --workflow-id ci-recovery --format markdown
python -m unittest discover -s tests
```

The first command prints the cost ladder for a typical SOP/agent run. The
second command evaluates the sample CI recovery workflow and sample run logs.

To open the reusable local web dashboard:

```powershell
powershell -ExecutionPolicy Bypass -File .\dashboard\serve.ps1
```

Then open:

```text
http://127.0.0.1:8787/dashboard/index.html
```

The dashboard loads `.mpm-ladder/workspace.json`, lets you select a workflow,
and renders the semantic task definition together with the measured MPM report.

## Example Output Shape

```text
Version:      2026-07-02T000000Z
Observed MPM: T3 via gpt-5.4-mini
Reliable MPM: T0 via gpt-5.5
Target MPM:   T2 (not met)
Automation:   3/6 automated steps
Agent steps:  2/6
Human gates:  1/6
```

## Project Layout

```text
PROJECT_MEMORY.md                  Product context and design memory
dashboard/                         Reusable Korean web dashboard
data/models.json                     Model tiers and prices
data/objective_profiles.json         Objective profile presets
.mpm-ladder/workspace.json           Local workflow registry
examples/workflows/ci-recovery.json  Sample workflow definition
examples/runs/ci-recovery-runs.json  Sample benchmark attempts
mpm_ladder/                          CLI and scoring logic
tests/                               Standard-library tests
```

## What This MVP Does

1. Calculates per-run cost from input/output token profiles.
2. Compares models by cost multiplier against the cheapest candidate.
3. Aggregates pass@N, cost/success, failure labels, and AFR.
4. Finds the observed MPM from successful run logs.
5. Separates workflow automation coverage from model capability.
6. Tracks reliable MPM using minimum pass-rate and attempt thresholds.
7. Registers semantic workflows in a local workspace registry.
8. Links measurements to workflow versions and report scoring metadata.
9. Serves a local Korean dashboard that swaps workflow data through the
   workspace manifest.

## What Comes Next

- Add real executor adapters for OpenAI, Claude, local models, and shell-only
  replay.
- Store traces from actual workflow runs.
- Add per-step MPM instead of only workflow-level MPM.
- Add prompt caching and batch pricing profiles.
- Add CI templates for recurring SOP benchmark runs.
