# Project Memory

This file preserves the product context behind MPM Ladder so future work can
continue without re-deriving the core frame.

## Core Thesis

MPM Ladder is not mainly a model leaderboard. It is a workflow automation
maturity measurement system.

The central question is:

```text
What is the minimum executor tier that can complete this workflow reliably?
```

Models are used as intelligence rulers. The asset is the benchmark protocol,
not a fixed model name.

## Scope Relationship

Documentation MPM is included inside Workflow MPM.

```text
Workflow MPM
`-- Documentation MPM
```

Documentation MPM asks:

```text
What is the minimum executor intelligence needed to read and follow this doc?
```

Workflow MPM asks:

```text
What is the minimum judgment intelligence needed to complete the whole task system?
```

A workflow can include docs, scripts, CI, rule-based branches, tools,
environment assumptions, approvals, and agent judgment.

## Practical Automation Frame

Real automation is usually mixed rather than pure.

```text
rule-based preflight
+ scriptable happy path
+ agent judgment branches
+ human approval gates
+ CI verification
```

The goal is to measure which parts can be pushed down to cheaper, simpler, and
more deterministic executors.

Useful per-step executor classes:

```text
script
rule
ci
T4 nano/local-like worker
T3 cheap worker
T2 balanced worker
T1 senior executor
T0 oracle
human gate
```

## Tier Ladder

The tier names are stable concepts. Specific model names and prices are
replaceable data.

```text
T0: Oracle
    Proves feasibility, creates golden traces, handles unknown hard cases.

T1: Senior
    Handles design, review, ambiguous failures, and higher-risk changes.

T2: Balanced Worker
    Practical default execution tier for routine automation.

T3: Cheap Worker
    Documentation and workflow robustness tester.

T4: Local / Nano / Script-adjacent
    Extreme lower bound for narrow, explicit, highly automated flows.
```

The important number is not whether the best model succeeds. The important
number is the lowest tier that succeeds with acceptable reliability.

## Key Metrics

```text
MPM
Minimum Passing Model or minimum passing executor tier.

pass@N
Successful runs over N repeated attempts.

cost/run
Estimated model and tool spend per attempt.

cost/success
Total attempt cost divided by successful attempts.

AFR
Actionable Failure Rate:
failures that improve the workflow / all failures.

cost/useful-failure
Total attempt cost divided by actionable failures.

automation coverage
script/rule/CI steps divided by total workflow steps.

escalation rate
attempts that need a higher tier or human gate.
```

QA model and execution model are different roles.

```text
QA model:
Finds useful workflow defects cheaply.

Execution model:
Completes the task reliably at the lowest cost per success.
```

## Failure Labels

Failure labeling is required so MPM does not mix workflow quality with model
noise.

```text
DOC_GAP
The document is missing or ambiguous.

RULE_GAP
A deterministic branch should exist but does not.

SCRIPT_GAP
A repeated operation should be scripted but is manual or agent-dependent.

TOOL_GAP
The CLI/tool interface blocks reliable automation.

ENV_GAP
Environment, permissions, secrets, cache, or dependency assumptions are missing.

AGENT_GAP
The executor misread logs, paths, instructions, or repeated a bad action.

GATE_GAP
Approval, policy, rollback, or risk boundaries are unclear.

TASK_INVALID
The task cannot be completed under the current constraints.
```

## Operating Protocol

For a new workflow:

```text
1. Run T0/T1 to prove the task is possible.
2. Capture the successful command sequence and artifacts as a golden trace.
3. Run T2 with only the workflow instructions.
4. Run T3/T4 to find implicit assumptions and automation gaps.
5. Label failures and update docs, rules, scripts, or gates.
6. Record the observed MPM and cost metrics.
```

For an existing workflow:

```text
1. Start from the cheapest tier expected to pass.
2. Escalate only when the lower tier fails.
3. Use T1/T0 to judge whether failure is workflow signal or model noise.
4. Update the workflow when failures are actionable.
5. Re-run after model price or capability changes.
```

## Golden Trace Caution

A golden trace is one known successful route, not the only valid route.

Store:

```text
success criteria
required artifacts
commands used
allowed alternatives
forbidden risky actions
recovery branches
verification commands
environment assumptions
```

## MVP Intent

The current MVP should stay local-first and credential-free:

```text
model/tier price data
workflow definitions
benchmark run logs
price comparison CLI
workflow evaluation CLI
MPM report
unit tests
```

Provider execution adapters come later. The first durable value is scoring and
reporting, because that defines the measurement protocol.

## Near-Term Product Direction

Next useful additions:

```text
per-step MPM scoring
workflow trace schema
real run recorder
provider adapter interface
OpenAI/Anthropic/local executor adapters
script-only replay adapter
HTML/Markdown report exporter
pricing refresh command
CI benchmark template
```

The product should make this distinction clear:

```text
Documentation optimization is one input.
Workflow automation maturity is the larger product.
```
