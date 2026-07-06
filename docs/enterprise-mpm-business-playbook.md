# Enterprise MPM Business Playbook

## 1. Product Positioning

MPM Ladder should be sold as a workflow automation maturity system, not as a
general model leaderboard.

The enterprise buyer question is:

```text
What is the cheapest, safest, auditable executor mix that can complete this
real workflow reliably?
```

The answer should combine:

- executor tier: script, rule, CI, T4, T3, T2, T1, T0, or human gate
- reliability: pass@N and blocked-step rate
- cost: cost/run, cost/success, and cost/useful-failure
- operating risk: approval gaps, unsafe tool use, environment assumptions
- improvement path: docs, rules, scripts, tools, gates, or model upgrades

The enterprise value is not "which model is best." The value is:

```text
This workflow currently needs T1 supervision.
After fixing two documentation gaps and adding one preflight script, it can run
at T3 with a human approval gate only on high-risk submissions.
```

## 2. Target Customers

### 2.1 Best Initial Customers

Start with teams that already have repeatable knowledge workflows and feel AI
automation pain in production-like environments.

| Segment | Buyer | Pain | Why MPM Fits |
| --- | --- | --- | --- |
| Software platform teams | VP Engineering, DevOps lead | CI failures, release toil, incident follow-up | Success can be judged by tests, logs, deploy state, and rollback gates |
| Internal operations | COO, automation lead | Repetitive SOP execution and exception handling | Workflows have steps, approvals, and measurable escalation |
| Customer support ops | Head of Support | Ticket triage, drafts, refunds, policy exceptions | Pass/fail can be judged against policy and CRM state |
| Compliance/security | GRC lead, security engineering | Evidence collection and control checks | Audit trails, gates, and human review are mandatory |
| Finance/revenue ops | Controller, RevOps lead | Month-end checks, CRM hygiene, invoice exceptions | Structured inputs and strict acceptance criteria exist |

### 2.2 Bad Initial Customers

Avoid workflows where quality is mostly subjective and no reliable judge exists.

Examples:

- brand copywriting
- open-ended strategy memos
- creative ideation
- exploratory market research without a rubric
- executive summaries where "good" is undefined

These can come later after the judge and human-review loop are mature.

## 3. Core Enterprise Workflow

Every enterprise MPM engagement should follow the same loop:

```text
1. Register workflow
2. Freeze inputs and environment assumptions
3. Run tiered attempts
4. Capture traces
5. Judge pass/fail and label failures
6. Reduce to metrics
7. Recommend workflow fixes
8. Re-run and compare before/after
```

The product should make each loop auditable. A customer should be able to prove:

- what workflow version was tested
- which executor tier was used
- what tools were allowed
- where the attempt failed or escalated
- whether the failure was a model issue or workflow design issue
- which change lowered cost or risk

## 4. Metric Definitions For Business Use

### 4.1 Observed MPM

The lowest executor tier that meets the reliability target.

Example:

```text
Reliability target: pass@5 >= 80%

T4: 1/5 pass = 20%
T3: 4/5 pass = 80%
T2: 5/5 pass = 100%
T1: 5/5 pass = 100%

Observed MPM: T3
```

### 4.2 Cost Per Success

```text
cost/success = total attempt cost / successful attempts
```

Example:

```text
T1 run cost: $1.20
T1 attempts: 5
T1 successes: 5
T1 cost/success: $6.00 / 5 = $1.20

T3 run cost: $0.18
T3 attempts: 5
T3 successes: 4
T3 cost/success: $0.90 / 4 = $0.225
```

Business interpretation:

```text
T3 is 81.25% cheaper per successful workflow than T1.
```

### 4.3 Escalation Rate

```text
escalation rate = attempts requiring higher tier or human gate / total attempts
```

Example:

```text
20 weekly support-refund workflows
6 required policy escalation
Escalation rate: 30%
```

If the target is 10%, the product should show which step causes escalation.

### 4.4 Actionable Failure Rate

```text
AFR = actionable failures / total failures
```

Example:

```text
Total failed attempts: 12
DOC_GAP: 4
SCRIPT_GAP: 3
TOOL_GAP: 2
AGENT_GAP: 3

Actionable failures: 9
AFR: 75%
```

Business interpretation:

```text
Most failures are workflow improvement opportunities, not unavoidable model
noise.
```

### 4.5 Automation Coverage

```text
automation coverage = script/rule/CI steps / total workflow steps
```

Example:

```text
Total steps: 12
Script/rule/CI steps: 7
Automation coverage: 58.3%
```

The dashboard should show whether higher automation coverage lowers MPM.

## 5. Enterprise Failure Labels

Use these labels as business language, not only engineering language.

| Label | Enterprise Meaning | Typical Fix |
| --- | --- | --- |
| DOC_GAP | SOP or policy is ambiguous or missing | Rewrite step, add examples, define edge cases |
| RULE_GAP | A deterministic branch is handled by judgment | Add decision table or policy rule |
| SCRIPT_GAP | Repeated action is manual or agent-dependent | Add script, CLI command, or workflow automation |
| TOOL_GAP | Tool/API prevents reliable automation | Improve API, CLI output, retries, or error messages |
| ENV_GAP | Credentials, data, dependency, or environment is unclear | Add preflight checks and environment contract |
| AGENT_GAP | Executor made a reasoning or attention mistake | Raise tier, improve prompt, add verification |
| GATE_GAP | Approval/rollback/risk boundary is unclear | Add human gate and policy |
| TASK_INVALID | Workflow cannot be completed under current constraints | Redesign scope or remove from automation |

## 6. Concrete Example A: CI Failure Recovery

### 6.1 Business Context

Company: B2B SaaS with 80 engineers.

Current state:

- 240 CI failures per month
- 45% are flaky test reruns or simple dependency/cache issues
- 30% are small code/test fixes
- 25% require senior engineering judgment
- average engineer time per CI failure: 18 minutes
- loaded engineering cost: $110/hour

Baseline monthly cost:

```text
240 failures * 18 minutes = 4,320 minutes = 72 hours
72 hours * $110/hour = $7,920/month
```

### 6.2 Workflow Definition

```text
Workflow: ci-failure-recovery
Target MPM: T3
Reliability target: pass@10 >= 80%
Maximum unsafe-action rate: 0%
Human gate required for production deploy or broad refactor
```

Steps:

| Step | Executor Target | Success Criteria |
| --- | --- | --- |
| collect-ci-log | script | Fetch failing job log and changed files |
| classify-failure | T4/T3 | Label failure as flaky, dependency, test, code, infra, or unknown |
| run-targeted-test | script | Reproduce failure locally or in CI container |
| propose-fix | T3/T2 | Minimal patch, no unrelated diff |
| verify-targeted | CI/script | Targeted test passes |
| verify-suite | CI | Related suite passes |
| human-gate | human | Required only for broad changes |

### 6.3 Initial MPM Run

```text
Run date: 2026-06-25
Workflow version: ci-failure-recovery@v1
Attempts per tier: 10
```

| Tier | Cost/Run | Pass@10 | Cost/Success | Escalation | Main Failure |
| --- | ---: | ---: | ---: | ---: | --- |
| T4 | $0.03 | 2/10 | $0.15 | 70% | AGENT_GAP |
| T3 | $0.12 | 6/10 | $0.20 | 30% | ENV_GAP |
| T2 | $0.42 | 8/10 | $0.53 | 20% | DOC_GAP |
| T1 | $1.30 | 10/10 | $1.30 | 0% | none |

Observed MPM at 80% target:

```text
T2
```

### 6.4 Failure Breakdown

| Step | Failure Count | Labels | Interpretation |
| --- | ---: | --- | --- |
| collect-ci-log | 4 | ENV_GAP | CI token and job URL format were not documented |
| classify-failure | 3 | DOC_GAP, AGENT_GAP | Failure taxonomy lacked examples |
| run-targeted-test | 5 | SCRIPT_GAP | No stable command for package-specific tests |
| propose-fix | 2 | AGENT_GAP | T3 made broad changes |

### 6.5 Recommended Fixes

| Fix | Owner | Estimated Effort | Expected Impact |
| --- | --- | ---: | --- |
| Add `ci-log-fetch` script | DevOps | 1 day | Remove most ENV_GAP failures |
| Add failure taxonomy examples | Platform | 0.5 day | Improve T3 classification |
| Add package test resolver | Build team | 2 days | Lower SCRIPT_GAP at targeted test step |
| Add "max changed files" guard | Platform | 0.5 day | Prevent broad unsafe patches |

### 6.6 After Improvement Run

```text
Workflow version: ci-failure-recovery@v2
Attempts per tier: 10
```

| Tier | Cost/Run | Pass@10 | Cost/Success | Escalation | Main Failure |
| --- | ---: | ---: | ---: | ---: | --- |
| T4 | $0.03 | 4/10 | $0.08 | 50% | AGENT_GAP |
| T3 | $0.12 | 9/10 | $0.13 | 10% | AGENT_GAP |
| T2 | $0.42 | 10/10 | $0.42 | 0% | none |
| T1 | $1.30 | 10/10 | $1.30 | 0% | none |

New observed MPM:

```text
T3
```

Business impact:

```text
Expected eligible automation volume: 75% of 240 = 180 failures/month
T3 agent cost: 180 * $0.13 = $23.40/month
Human review time after automation: 180 * 4 minutes = 720 minutes = 12 hours
Human review cost: 12 * $110 = $1,320/month
Remaining manual failures: 60 * 18 minutes = 18 hours = $1,980/month

New monthly operating cost: $23.40 + $1,320 + $1,980 = $3,323.40
Baseline monthly cost: $7,920
Estimated savings: $4,596.60/month
Annualized savings: $55,159.20
```

Executive summary:

```text
MPM dropped from T2 to T3.
Cost/success dropped from $0.53 to $0.13 for the target tier.
The workflow is now a valid T3 automation candidate with CI verification and a
human gate for broad changes.
```

## 7. Concrete Example B: Customer Refund Policy Handling

### 7.1 Business Context

Company: subscription commerce business.

Current state:

- 3,000 refund-related tickets per month
- average support handling time: 6 minutes
- support cost: $32/hour
- 18% of tickets require policy exception review
- refund mistakes create finance leakage and customer dissatisfaction

Baseline monthly handling cost:

```text
3,000 * 6 minutes = 18,000 minutes = 300 hours
300 * $32 = $9,600/month
```

### 7.2 Workflow Definition

```text
Workflow: refund-ticket-resolution
Target MPM: T4 for standard tickets, T2 for exception classification
Reliability target: pass@20 >= 90%
Human gate: required for refunds above $250 or policy exception
```

Steps:

| Step | Executor Target | Success Criteria |
| --- | --- | --- |
| parse-ticket | T4 | Extract order ID, reason, customer request |
| fetch-order | script | Retrieve order status and refund history |
| apply-policy | rule/T4 | Match deterministic refund rule |
| draft-response | T4/T3 | Produce policy-compliant response |
| exception-check | rule/T2 | Detect high-value or ambiguous cases |
| submit-refund | human/script | Only after approval when required |

### 7.3 Initial Run

| Tier | Pass@20 | Cost/Run | Cost/Success | Human Escalation | Key Failure |
| --- | ---: | ---: | ---: | ---: | --- |
| T4 | 13/20 | $0.01 | $0.015 | 35% | RULE_GAP |
| T3 | 17/20 | $0.04 | $0.047 | 20% | GATE_GAP |
| T2 | 19/20 | $0.18 | $0.189 | 15% | DOC_GAP |
| T1 | 20/20 | $0.70 | $0.700 | 15% | none |

Observed MPM at 90% target:

```text
T2
```

### 7.4 Fixes

| Fix | Why | Expected MPM Impact |
| --- | --- | --- |
| Convert refund policy to decision table | Removes ambiguous judgment from standard cases | Standard cases can drop to T4/rule |
| Add high-value refund gate | Prevents unsafe autonomous refunds | Reduces GATE_GAP |
| Add CRM preflight for missing order data | Prevents hallucinated order assumptions | Reduces ENV_GAP |
| Add response template constraints | Keeps tone and policy language consistent | Reduces DOC_GAP |

### 7.5 After Run

| Tier | Standard Tickets Pass@20 | Exception Detection Pass@20 | Cost/Success | Human Escalation |
| --- | ---: | ---: | ---: | ---: |
| rule + T4 | 19/20 | 16/20 | $0.011 | 22% |
| rule + T3 | 20/20 | 18/20 | $0.041 | 19% |
| rule + T2 | 20/20 | 20/20 | $0.180 | 18% |

Operating policy:

```text
Standard tickets: rule + T4
Exception classification: T2
Refund execution above $250: human gate
```

Business impact:

```text
Standard tickets: 82% of 3,000 = 2,460/month
Automated handling time saved: 2,460 * 5 minutes = 12,300 minutes = 205 hours
Support labor saved: 205 * $32 = $6,560/month
Estimated model cost: 2,460 * $0.011 = $27.06/month
Net monthly savings before review overhead: $6,532.94
```

Executive summary:

```text
MPM did not simply choose one model.
It split the workflow: deterministic policy rules plus T4 for standard tickets,
T2 for exception classification, and human approval for financial risk.
```

## 8. Concrete Example C: Compliance Evidence Collection

### 8.1 Business Context

Company: SOC 2 Type II preparation for a 250-person SaaS company.

Current state:

- 110 recurring evidence requests per quarter
- average evidence collection time: 22 minutes
- security/compliance loaded cost: $95/hour
- high audit risk if evidence is missing, stale, or untraceable

Baseline quarterly cost:

```text
110 * 22 minutes = 2,420 minutes = 40.33 hours
40.33 * $95 = $3,831.35/quarter
```

### 8.2 Workflow Definition

```text
Workflow: compliance-evidence-collection
Target MPM: T3
Reliability target: pass@10 >= 90%
Audit requirement: every artifact must include source URL, timestamp, owner,
and control ID
Human gate: required before auditor submission
```

Steps:

| Step | Executor Target | Success Criteria |
| --- | --- | --- |
| read-control | T4 | Identify control ID and evidence requirement |
| fetch-source | script/provider | Pull evidence from GitHub, cloud, HRIS, or ticket system |
| validate-freshness | rule | Evidence timestamp is within required window |
| map-owner | rule/T4 | Assign responsible owner |
| package-evidence | T3 | Produce complete artifact bundle |
| human-review | human | Approve before external auditor submission |

### 8.3 Initial Run

| Tier | Pass@10 | Cost/Run | Cost/Success | Failure Labels |
| --- | ---: | ---: | ---: | --- |
| T4 | 3/10 | $0.02 | $0.067 | ENV_GAP, DOC_GAP |
| T3 | 6/10 | $0.09 | $0.150 | TOOL_GAP, ENV_GAP |
| T2 | 8/10 | $0.31 | $0.388 | TOOL_GAP |
| T1 | 10/10 | $1.05 | $1.050 | none |

Observed MPM at 90% target:

```text
T1
```

The issue is not model intelligence. It is connector and environment quality.

### 8.4 Fixes

| Fix | Effort | Expected Impact |
| --- | ---: | --- |
| Add source connector health checks | 1 day | Reduce ENV_GAP |
| Define evidence freshness rules per control | 0.5 day | Move validation to rule executor |
| Add artifact manifest schema | 1 day | Make judge deterministic |
| Add owner lookup table | 0.5 day | Avoid ambiguous assignment |

### 8.5 After Run

| Tier | Pass@10 | Cost/Run | Cost/Success | Human Review Findings |
| --- | ---: | ---: | ---: | --- |
| T4 | 7/10 | $0.02 | $0.029 | 2 owner mismatches |
| T3 | 10/10 | $0.09 | $0.090 | 0 critical issues |
| T2 | 10/10 | $0.31 | $0.310 | 0 critical issues |

New observed MPM:

```text
T3
```

Business impact:

```text
Automatable evidence requests: 80% of 110 = 88/quarter
Manual time after automation: 88 * 5 minutes review = 440 minutes = 7.33 hours
Manual review cost: 7.33 * $95 = $696.35
Model cost: 88 * $0.09 = $7.92
Remaining manual requests: 22 * 22 minutes = 484 minutes = 8.07 hours
Remaining manual cost: 8.07 * $95 = $766.65

New quarterly cost: $696.35 + $7.92 + $766.65 = $1,470.92
Baseline quarterly cost: $3,831.35
Quarterly savings: $2,360.43
Annualized savings: $9,441.72
```

Executive summary:

```text
The workflow looked like it required T1.
After making evidence schemas and connector preflights explicit, it became a T3
workflow with mandatory human review before auditor submission.
```

## 9. Product Requirements For The Enterprise Version

### 9.1 Workflow Registry

Required fields:

```json
{
  "id": "ci-failure-recovery",
  "name": "CI Failure Recovery",
  "owner": "platform-engineering",
  "risk_level": "medium",
  "target_mpm": "T3",
  "reliability_target": {
    "metric": "pass_at_n",
    "n": 10,
    "minimum": 0.8
  },
  "human_gates": [
    "production-deploy",
    "broad-refactor"
  ],
  "success_criteria": [
    "targeted test passes",
    "no unrelated diff",
    "trace includes commands and artifacts"
  ]
}
```

### 9.2 Tiered Execution Matrix

The matrix should support:

- executor tier
- model ID or non-model executor
- adapter kind
- allowed tools
- timeout
- max cost
- repeats
- risk policy

Example:

```json
{
  "worker": "t3-ci-fixer",
  "tier": "T3",
  "adapter": "codex",
  "model_id": "gpt-5.4-mini",
  "attempts": 10,
  "timeout_seconds": 900,
  "max_cost_usd": 2.0,
  "allowed_tools": ["shell", "git-diff", "test-runner"],
  "forbidden_actions": ["push", "deploy", "delete-production-data"]
}
```

### 9.3 Trace Contract

Every attempt must record:

- workflow version
- input snapshot hash
- executor tier
- model and adapter
- tool calls
- step events
- artifacts produced
- status
- failure label
- blocked step
- judge rationale
- cost estimate
- duration
- human override if any

Minimum trace event:

```json
{
  "step_id": "run-targeted-test",
  "executor": "script",
  "status": "blocked",
  "failure_label": "SCRIPT_GAP",
  "note": "No deterministic command mapped package to test target"
}
```

### 9.4 Judge Layer

Enterprise deployments need both deterministic and human-assisted judging.

Judge types:

| Judge Type | Use Case |
| --- | --- |
| deterministic | unit tests, schema validation, policy decision table |
| artifact validator | required files, fields, manifests, timestamps |
| static analyzer | unrelated diff, unsafe command, PII leakage |
| LLM judge | qualitative but rubric-bound review |
| human reviewer | high-risk approval, audit override |

The system should never hide judge type. A dashboard row should say:

```text
Pass: yes
Judge: deterministic + human reviewer
Human override: none
```

### 9.5 Dashboard Views

Required dashboard sections:

1. Executive summary
2. Observed MPM vs target MPM
3. Cost/success by tier
4. Pass@N by tier
5. Step bottlenecks
6. Failure label breakdown
7. Before/after comparison
8. Recommended workflow fixes
9. Risk gates and unsafe action count
10. Trace/artifact links

Example dashboard headline:

```text
CI Failure Recovery
Observed MPM dropped from T2 to T3 after v2 workflow fixes.
Cost/success dropped 75.5%.
Escalation rate dropped from 30% to 10%.
No unsafe actions observed.
```

### 9.6 Security And Compliance Requirements

Enterprise MPM must support:

- local-first execution
- private artifact storage
- secrets redaction
- tool allowlists
- forbidden-action policies
- role-based access
- audit logs
- retention policies
- PII detection hooks
- explicit human gates
- environment snapshotting

The product should assume many customers cannot send production logs or customer
data to a hosted model by default.

## 10. Implementation Plan For This Repository

### Phase 1: Enterprise Playbook And Metrics

Goal:

```text
Make the business framing concrete enough that each later implementation PR can
map to one measurable enterprise outcome.
```

PR candidates:

1. Add enterprise playbook document.
2. Add example enterprise workflows under `examples/workflows/enterprise/`.
3. Add example run logs with before/after MPM numbers.
4. Add report fields for reliability target and human gate count.
5. Add tests for cost/success and MPM before/after comparison.

### Phase 2: Workflow Intake And Registry

Goal:

```text
Turn business workflows into versioned MPM workflow definitions.
```

Implementation tasks:

- add workflow metadata: owner, risk level, environment, data sensitivity
- add reliability target fields
- add human gate declarations
- add validation rules for enterprise fields
- add scaffold template for enterprise workflows

Acceptance criteria:

```text
python -B -m mpm_ladder scaffold --template enterprise-ci
python -B -m mpm_ladder validate --workflow examples/workflows/enterprise/ci-failure-recovery.json
```

### Phase 3: Before/After Comparison

Goal:

```text
Show whether workflow improvements lowered MPM, cost/success, and escalation.
```

Implementation tasks:

- compare workflow versions
- show tier delta
- show cost/success delta
- show escalation-rate delta
- show failure-label delta
- add markdown and dashboard sections

Acceptance criteria:

```text
python -B -m mpm_ladder compare \
  --baseline-runs examples/runs/enterprise/ci-v1-runs.json \
  --candidate-runs examples/runs/enterprise/ci-v2-runs.json
```

Expected output:

```text
Observed MPM: T2 -> T3
Cost/success: $0.53 -> $0.13
Escalation: 30% -> 10%
Top resolved label: ENV_GAP
```

### Phase 4: Risk Gates

Goal:

```text
Prevent autonomous execution from crossing enterprise risk boundaries.
```

Implementation tasks:

- add gate definitions to workflow schema
- add gate events to trace schema
- add unsafe-action counter
- add dashboard gate summary
- add validation failures when high-risk steps lack a gate

Acceptance criteria:

```text
Risk level high + no human gate => validate fails.
Trace with forbidden deploy action => report unsafe_action_count > 0.
```

### Phase 5: Real Adapter Boundary

Goal:

```text
Keep adapters responsible only for executing attempts and emitting traces.
Scoring, judging, comparison, and dashboards stay in core.
```

Implementation tasks:

- define adapter protocol
- add shell adapter
- add Codex adapter wrapper around existing real benchmark runner
- add provider adapter placeholder
- add local-only execution mode

Acceptance criteria:

```text
Adapter emits trace JSON.
Replay can rebuild runs from adapter traces.
Dashboard renders without knowing which adapter produced the trace.
```

## 11. First Sellable Package: MPM Audit

The easiest first commercial package is not a full SaaS. It is a fixed-scope MPM
Audit.

Package:

```text
Duration: 2 weeks
Workflows assessed: 3
Attempts per workflow: 5 to 10 per tier
Deliverables: MPM report, failure label breakdown, automation plan, before/after
optional re-run
```

Example pricing:

```text
Starter MPM Audit: $7,500
3 workflows, local execution, static dashboard

Team MPM Audit: $18,000
5 workflows, before/after rerun, executive ROI report

Enterprise Pilot: $45,000
10 workflows, connector setup, risk gates, private deployment review
```

Buyer-facing deliverable:

```text
Workflow portfolio:
- CI failure recovery: T2 -> T3 opportunity, $55k/year estimated savings
- Refund handling: rule+T4 standard path, $78k/year estimated savings
- Compliance evidence: T1 -> T3 opportunity, $9.4k/year estimated savings

Total identified savings: $142.4k/year
Primary blockers: ENV_GAP, SCRIPT_GAP, GATE_GAP
Recommended automation investment: 8 engineering days
Estimated payback period: under 1 month
```

## 12. Product North Star

The north-star claim should be:

```text
MPM Ladder shows how to lower the intelligence tier required to run a business
workflow safely.
```

The product is working when a customer can say:

```text
Before MPM, we guessed which workflows needed expensive agents or humans.
After MPM, we know which steps need scripts, rules, better docs, better tools,
or human gates. We lowered operating cost without hiding risk.
```

## 13. Immediate Next PRs

After this playbook, the next implementation PRs should be:

1. Add enterprise workflow examples for CI recovery, refund handling, and
   compliance evidence collection.
2. Add before/after example runs that reproduce the numeric cases in this
   document.
3. Extend report output with escalation rate and unsafe action count.
4. Extend dashboard with "recommended workflow fixes" grouped by failure label.
5. Add `scaffold --template enterprise` for a customer-ready workflow intake.

Stop condition for the first implementation milestone:

```text
A user can run one command and generate an enterprise-style dashboard showing:
- observed MPM
- target MPM
- pass@N
- cost/success
- escalation rate
- step bottlenecks
- failure labels
- recommended fixes
- before/after deltas
```
