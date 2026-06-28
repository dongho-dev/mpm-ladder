# Objective Profiles

This note sketches the next product layer for MPM Ladder: goal-configurable
workflow optimization.

MPM Ladder should not only answer:

```text
What is the minimum executor tier that can complete this workflow?
```

It should also answer:

```text
Given a customer's goal and constraints, what executor strategy should run this workflow?
```

That strategy may be a single model, but it will often be a route policy:

```text
script/rule/CI happy path
+ cheap worker default
+ balanced worker escalation
+ senior/oracle review for ambiguous failures
+ human gate for risky changes
```

The product should move from a static benchmark report toward a workflow
optimization engine.

## Product Thesis

Different customers optimize for different outcomes.

Some want to preserve quality while lowering model spend. Some want the fastest
acceptable completion time. Some care about total business cost, where latency,
retries, escalation, and human review matter more than raw token price. Some want
cheap failure probes that reveal documentation and automation gaps.

Therefore, MPM Ladder should support explicit objective profiles.

An objective profile is:

```text
hard constraints
+ optimization objective
+ tie breakers
+ recommended route policy
```

This is better than a simple weighted slider such as:

```text
quality 40% + cost 30% + latency 30%
```

For most enterprise workflows, quality, risk, and policy should be floors, not
soft preferences. A cheaper route that violates the quality floor is not an
optimization. It is a rejected candidate.

## Core Design Principle

Use constraints first, then optimize.

```text
1. Filter candidates by hard constraints.
2. Rank feasible candidates by the chosen objective.
3. Use tie breakers for near-equivalent candidates.
4. Emit the recommended route and rejected-candidate reasons.
```

Example:

```text
quality >= 0.90
p95_latency <= 600 seconds
human gate required for production-impacting changes
then minimize expected cost per success
```

This makes the recommendation explainable and safe enough for operational use.

## Candidate Objective Modes

### 1. `minimize_cost`

Preserve a quality floor while lowering expected cost per success.

```text
minimize expected_cost_per_success
subject to pass_rate >= min_pass_rate
```

Best for AI FinOps, internal agent platforms, and workflows where the current
frontier-model default is likely overkill.

Typical constraints:

```json
{
  "min_pass_rate": 0.90,
  "max_quality_regression": 0.02,
  "max_p95_latency_seconds": 600
}
```

### 2. `minimize_latency`

Find the fastest acceptable execution strategy.

```text
minimize expected_time_per_success
subject to pass_rate >= min_pass_rate
and cost_per_success <= max_cost_per_success_usd
```

This is useful for interactive coding assistants, customer support, alert
triage, and human-in-the-loop tools.

Cheap models are not automatically faster. A cheap worker that fails, retries,
and escalates may be slower than a balanced worker that succeeds once.

### 3. `minimize_total_business_cost`

Optimize for the full business cost, not only token spend.

```text
total_business_cost =
  model_cost
  + tool_cost
  + latency_cost
  + retry_cost
  + escalation_cost
  + human_review_cost
  + failure_penalty
```

This mode is often the most realistic enterprise default because raw token price
is only one line item. Waiting, retrying, human review, and failed automation can
cost more than inference.

Example parameters:

```json
{
  "value_of_time_usd_per_minute": 0.50,
  "human_review_usd_per_minute": 1.20,
  "failure_penalty_usd": 10.00,
  "escalation_penalty_usd": 2.00
}
```

### 4. `maximize_reliability`

Maximize success rate while staying within a cost ceiling.

```text
maximize pass_rate
subject to cost_per_success <= max_cost_per_success_usd
```

Best for deployments, migrations, security-sensitive workflows, permission
changes, financial operations, and anything with high downside risk.

In this mode, downshifting is not always correct. A T2 worker with a materially
higher pass rate may be better than a T3 worker that is cheaper but fragile.

### 5. `maximize_learning`

Use cheap failures to improve the workflow.

```text
maximize useful_failures_per_dollar
```

This is MPM Ladder's most distinctive mode.

A low-tier executor can be used as a documentation and automation robustness
probe. If a cheap worker fails because an SOP is ambiguous, a rule is missing, or
a CLI interface is brittle, the failure is useful. The goal is not to complete
the workflow immediately. The goal is to discover the weakest joints in the
workflow skeleton.

Relevant metrics:

```text
AFR = actionable_failures / failures
cost_per_useful_failure = total_cost / actionable_failures
```

Best for SOP hardening, documentation QA, onboarding workflows, CI recovery
recipes, and agentic workflow fuzzing.

## Suggested Preset Profiles

Customers should not have to tune dozens of fields before getting value. Provide
sensible presets and allow overrides.

```json
{
  "objective_profiles": {
    "cost_saver": {
      "mode": "minimize_cost",
      "constraints": {
        "min_pass_rate": 0.90,
        "max_quality_regression": 0.02
      },
      "tie_breakers": [
        "lower_latency",
        "lower_escalation_rate",
        "higher_actionable_failure_rate"
      ]
    },
    "speed_runner": {
      "mode": "minimize_latency",
      "constraints": {
        "min_pass_rate": 0.85,
        "max_cost_per_success_usd": 3.00
      },
      "tie_breakers": [
        "lower_cost",
        "lower_retry_rate"
      ]
    },
    "reliability_first": {
      "mode": "maximize_reliability",
      "constraints": {
        "max_cost_per_success_usd": 10.00,
        "require_human_gate_for": [
          "production_impacting_change",
          "credential_change",
          "data_migration"
        ]
      },
      "tie_breakers": [
        "lower_risk",
        "lower_latency",
        "lower_cost"
      ]
    },
    "learning_probe": {
      "mode": "maximize_learning",
      "constraints": {
        "max_cost_per_run_usd": 0.20
      },
      "tie_breakers": [
        "higher_doc_gap_rate",
        "higher_rule_gap_rate",
        "higher_script_gap_rate"
      ]
    },
    "balanced_default": {
      "mode": "minimize_total_business_cost",
      "constraints": {
        "min_pass_rate": 0.88,
        "max_p95_latency_seconds": 900
      },
      "parameters": {
        "value_of_time_usd_per_minute": 0.25,
        "human_review_usd_per_minute": 1.00,
        "failure_penalty_usd": 5.00
      },
      "tie_breakers": [
        "higher_pass_rate",
        "lower_cost",
        "lower_latency"
      ]
    }
  }
}
```

## Workflow-Level Schema Sketch

A workflow can define its target objective directly.

```json
{
  "schema_version": 1,
  "id": "ci-recovery",
  "name": "CI recovery workflow",
  "target_mpm": "T2",
  "objective": {
    "profile": "cost_saver",
    "mode": "minimize_cost",
    "constraints": {
      "min_pass_rate": 0.90,
      "max_quality_regression": 0.02,
      "max_p95_latency_seconds": 600,
      "max_cost_per_success_usd": 2.00,
      "allowed_executors": [
        "script",
        "rule",
        "ci",
        "T4",
        "T3",
        "T2",
        "human"
      ],
      "require_human_gate_for": [
        "production_impacting_change"
      ]
    },
    "tie_breakers": [
      "lower_latency",
      "lower_escalation_rate",
      "higher_actionable_failure_rate"
    ]
  }
}
```

The profile can be inherited from a global profile file, then overridden at the
workflow level.

Possible file layout:

```text
data/objective_profiles.json
examples/workflows/ci-recovery.json
examples/runs/ci-recovery-runs.json
```

## Recommended Report Shape

The report should graduate from a single observed MPM line to an explainable
strategy recommendation.

```text
Objective: cost_saver

Recommended route:
  default_executor: T3 gpt-5.4-mini
  escalation_executor: T2 claude-sonnet-4.6
  oracle_executor: T0 gpt-5.5
  human_gate: production-impacting changes only

Expected:
  pass_rate: 91%
  cost/run: $0.165
  cost/success: $0.181
  p95_latency: 8m 20s
  escalation_rate: 14%
  target_met: yes

Rejected candidates:
  T4 gpt-5-nano
    reason: pass_rate below min_pass_rate

  T1 claude-opus-4.8
    reason: quality gain too small for cost increase
```

The output should explain why a route was chosen and why alternatives were
rejected. The rejection reasons are part of the product value.

## Route Policy Output

A recommended strategy can be emitted as structured policy.

```json
{
  "recommended_policy": {
    "default_executor": "T3",
    "default_model_id": "gpt-5.4-mini",
    "escalation_executor": "T2",
    "oracle_executor": "T0",
    "escalation_rules": [
      {
        "when": "unknown_failure",
        "to": "T1"
      },
      {
        "when": "same_failure_repeated_twice",
        "to": "T2"
      },
      {
        "when": "production_impacting_change",
        "to": "human"
      }
    ],
    "cache_policy": {
      "reuse_static_context": true,
      "split_dynamic_input": true,
      "disconnect_unused_tools": true
    }
  }
}
```

This connects MPM Ladder to enterprise inference optimization:

```text
better defaults
+ better routing
+ better caching
+ better visibility
```

The benchmark produces the evidence. The route policy turns that evidence into
an operational decision.

## Metrics to Add

Current metrics such as pass rate, cost per success, AFR, and automation coverage
should remain. Objective profiles need several additional fields.

```text
average_latency_seconds
p50_latency_seconds
p95_latency_seconds
retry_rate
escalation_rate
human_gate_rate
expected_cost_per_success
expected_time_per_success
expected_total_business_cost
quality_regression
risk_adjusted_success_rate
```

Initial formulas can stay simple.

```text
expected_cost_per_success = average_cost_per_attempt / pass_rate
```

```text
expected_time_per_success = average_duration_seconds / pass_rate
```

```text
expected_total_business_cost =
  expected_cost_per_success
  + expected_time_per_success * value_of_time_usd_per_second
  + escalation_rate * escalation_penalty_usd
  + human_gate_rate * human_review_cost_usd
  + failure_rate * failure_penalty_usd
```

Later versions can add confidence intervals and workflow-specific risk models.

## Reliability Thresholds

The current MVP can identify the lowest tier with at least one passing run. That
is useful for exploration, but it is too weak for operational recommendations.

A production-grade MPM should require reliability thresholds.

```text
observed_mpm: lowest tier with any passing run
reliable_mpm: lowest tier that satisfies min_pass_rate and min_attempts
recommended_executor: best feasible candidate for the selected objective
```

Suggested fields:

```json
{
  "min_attempts": 5,
  "min_pass_rate": 0.90,
  "confidence_level": 0.80,
  "risk_class": "medium"
}
```

The language should separate discovery from recommendation:

```text
Observed MPM says what passed.
Reliable MPM says what passed enough.
Recommended policy says what should run.
```

## Per-Step Objective Scoring

Workflow-level MPM can hide where optimization actually happens. Per-step scoring
should eventually produce a table like this:

```text
step               current executor  observed MPM  recommendation
preflight          script            script        keep
run-checks         ci                ci            keep
classify-failure   T2                T3            downshift after log taxonomy cleanup
known-recovery     rule              script        turn recipe into script
unknown-debug      T1                T1            keep senior escalation
gate               human             human         keep policy gate
```

This is where the product becomes actionable. The customer can see which parts
of the workflow should be scripted, ruled, cached, downshifted, escalated, or
left behind a human gate.

## CLI Direction

Possible commands:

```powershell
python -m mpm_ladder evaluate --objective cost_saver
python -m mpm_ladder evaluate --objective speed_runner
python -m mpm_ladder evaluate --objective learning_probe
python -m mpm_ladder optimize --workflow examples/workflows/ci-recovery.json --runs examples/runs/ci-recovery-runs.json
python -m mpm_ladder optimize --format json
```

Possible output modes:

```text
text report
json report
markdown report
route-policy json
```

## Implementation Path

### v0.2

```text
1. Add data/objective_profiles.json.
2. Add objective loading and workflow-level overrides.
3. Add min_pass_rate and min_attempts to MPM selection.
4. Add expected_cost_per_success and expected_time_per_success.
5. Add objective-based candidate ranking.
6. Print rejected-candidate reasons.
7. Add tests for cost_saver, speed_runner, and learning_probe.
```

### v0.3

```text
1. Add route policy output.
2. Add escalation-aware scoring.
3. Add p50/p95 latency metrics.
4. Add per-step MPM scoring.
5. Add Markdown report exporter.
```

### v0.4

```text
1. Add real run recorder.
2. Add provider adapter interface.
3. Add script-only replay adapter.
4. Add prompt cache and batch price profiles.
5. Add CI benchmark template.
```

## Non-Goals for the First Version

Avoid building a complex global optimizer before the measurement protocol is
stable.

Avoid hiding decisions behind a vague blended score.

Avoid treating model price as the only cost.

Avoid claiming that the cheapest passing tier is safe for production without a
reliability threshold.

Avoid making the product a model leaderboard. Model names and prices are
replaceable data. The durable asset is the workflow measurement and routing
protocol.

## One-Line Positioning

```text
Find the cheapest, fastest, or safest executor strategy that still meets the workflow quality target.
```

Or, more operationally:

```text
Measure how far an AI workflow can be downshifted without losing reliability.
```
