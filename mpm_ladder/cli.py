from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODELS = ROOT / "data" / "models.json"
DEFAULT_WORKFLOW = ROOT / "examples" / "workflows" / "ci-recovery.json"
DEFAULT_RUNS = ROOT / "examples" / "runs" / "ci-recovery-runs.json"

AUTOMATED_EXECUTORS = {"script", "rule", "ci"}
HUMAN_EXECUTORS = {"human"}


@dataclass(frozen=True)
class RunProfile:
    input_tokens: int
    output_tokens: int
    tool_cost_usd: float = 0.0


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def money(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value < 0.01:
        return f"${value:.4f}"
    return f"${value:.3f}"


def ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}x"


def percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.0f}%"


def get_tier_ranks(models_doc: dict[str, Any]) -> dict[str, int]:
    return {tier["id"]: int(tier["rank"]) for tier in models_doc["tiers"]}


def model_cost(model: dict[str, Any], profile: RunProfile) -> float:
    input_cost = profile.input_tokens / 1_000_000 * float(model["input_per_mtok"])
    output_cost = profile.output_tokens / 1_000_000 * float(model["output_per_mtok"])
    return input_cost + output_cost + profile.tool_cost_usd


def profile_from_args(args: argparse.Namespace, fallback: dict[str, Any] | None = None) -> RunProfile:
    fallback = fallback or {}
    return RunProfile(
        input_tokens=int(args.input_tokens or fallback.get("input_tokens", 100_000)),
        output_tokens=int(args.output_tokens or fallback.get("output_tokens", 20_000)),
        tool_cost_usd=float(args.tool_cost_usd if args.tool_cost_usd is not None else fallback.get("tool_cost_usd", 0.0)),
    )


def price_rows(models_doc: dict[str, Any], profile: RunProfile) -> list[dict[str, Any]]:
    rows = []
    for model in models_doc["models"]:
        cost = model_cost(model, profile)
        rows.append(
            {
                "id": model["id"],
                "provider": model["provider"],
                "tier": model["tier"],
                "input_per_mtok": float(model["input_per_mtok"]),
                "output_per_mtok": float(model["output_per_mtok"]),
                "cost": cost,
            }
        )
    rows.sort(key=lambda row: (row["cost"], row["tier"], row["id"]))
    cheapest = rows[0]["cost"] if rows else 0.0
    for row in rows:
        row["multiple"] = row["cost"] / cheapest if cheapest else None
    return rows


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    print(" | ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))


def command_prices(args: argparse.Namespace) -> int:
    models_doc = load_json(Path(args.models))
    profile = profile_from_args(args)
    rows = price_rows(models_doc, profile)

    print("MPM Ladder Price Comparison")
    print(f"Profile: {profile.input_tokens:,} input tokens + {profile.output_tokens:,} output tokens")
    if profile.tool_cost_usd:
        print(f"Tool cost per run: {money(profile.tool_cost_usd)}")
    print()
    print_table(
        ["model", "provider", "tier", "input/MTok", "output/MTok", "cost/run", "multiple"],
        [
            [
                row["id"],
                row["provider"],
                row["tier"],
                money(row["input_per_mtok"]),
                money(row["output_per_mtok"]),
                money(row["cost"]),
                ratio(row["multiple"]),
            ]
            for row in rows
        ],
    )
    return 0


def group_attempts(runs_doc: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for attempt in runs_doc.get("attempts", []):
        grouped[attempt["model_id"]].append(attempt)
    return dict(grouped)


def attempt_is_pass(attempt: dict[str, Any]) -> bool:
    return str(attempt.get("status", "")).lower() in {"pass", "passed", "success", "succeeded"}


def attempt_is_failure(attempt: dict[str, Any]) -> bool:
    return str(attempt.get("status", "")).lower() in {"fail", "failed", "error", "timeout"}


def summarize_model_runs(
    models_doc: dict[str, Any],
    runs_doc: dict[str, Any],
    profile: RunProfile,
) -> list[dict[str, Any]]:
    models_by_id = {model["id"]: model for model in models_doc["models"]}
    grouped = group_attempts(runs_doc)
    summaries = []

    for model_id, attempts in sorted(grouped.items()):
        if model_id not in models_by_id:
            raise ValueError(f"Run log references unknown model: {model_id}")
        model = models_by_id[model_id]
        cost = model_cost(model, profile)
        passes = sum(1 for attempt in attempts if attempt_is_pass(attempt))
        failures = sum(1 for attempt in attempts if attempt_is_failure(attempt))
        actionable = sum(1 for attempt in attempts if attempt_is_failure(attempt) and bool(attempt.get("actionable")))
        labels = Counter(
            str(attempt.get("failure_label", "UNLABELED"))
            for attempt in attempts
            if attempt_is_failure(attempt)
        )
        summaries.append(
            {
                "model_id": model_id,
                "provider": model["provider"],
                "tier": model["tier"],
                "attempts": len(attempts),
                "passes": passes,
                "failures": failures,
                "pass_rate": passes / len(attempts) if attempts else None,
                "cost_run": cost,
                "cost_success": cost * len(attempts) / passes if passes else None,
                "actionable_failure_rate": actionable / failures if failures else None,
                "cost_useful_failure": cost * len(attempts) / actionable if actionable else None,
                "failure_labels": dict(labels),
            }
        )
    return summaries


def observed_mpm(
    summaries: list[dict[str, Any]],
    tier_ranks: dict[str, int],
) -> dict[str, Any] | None:
    passing = [summary for summary in summaries if summary["passes"] > 0]
    if not passing:
        return None
    return sorted(
        passing,
        key=lambda summary: (
            tier_ranks[summary["tier"]],
            summary["cost_run"],
            -summary["pass_rate"],
            summary["model_id"],
        ),
    )[0]


def workflow_coverage(workflow_doc: dict[str, Any], tier_ranks: dict[str, int]) -> dict[str, Any]:
    steps = workflow_doc.get("steps", [])
    automated = 0
    agent = 0
    human = 0
    unknown = 0
    required_tiers = []

    for step in steps:
        executor = str(step.get("executor", "")).lower()
        raw_executor = str(step.get("executor", ""))
        if executor in AUTOMATED_EXECUTORS:
            automated += 1
        elif executor in HUMAN_EXECUTORS:
            human += 1
        elif raw_executor in tier_ranks:
            agent += 1
            required_tiers.append(raw_executor)
        else:
            unknown += 1

    highest_tier = None
    if required_tiers:
        highest_tier = sorted(required_tiers, key=lambda tier: tier_ranks[tier], reverse=True)[0]

    total = len(steps)
    return {
        "total_steps": total,
        "automated_steps": automated,
        "agent_steps": agent,
        "human_gates": human,
        "unknown_steps": unknown,
        "automation_coverage": automated / total if total else None,
        "design_required_tier": highest_tier,
    }


def target_met(observed: dict[str, Any] | None, target_tier: str | None, tier_ranks: dict[str, int]) -> bool | None:
    if observed is None or not target_tier:
        return None
    if target_tier not in tier_ranks:
        return None
    return tier_ranks[observed["tier"]] <= tier_ranks[target_tier]


def build_report(
    models_doc: dict[str, Any],
    workflow_doc: dict[str, Any],
    runs_doc: dict[str, Any],
    profile: RunProfile,
) -> dict[str, Any]:
    tier_ranks = get_tier_ranks(models_doc)
    summaries = summarize_model_runs(models_doc, runs_doc, profile)
    mpm = observed_mpm(summaries, tier_ranks)
    target_tier = workflow_doc.get("target_mpm")
    coverage = workflow_coverage(workflow_doc, tier_ranks)
    return {
        "workflow_id": workflow_doc.get("id"),
        "workflow_name": workflow_doc.get("name"),
        "profile": {
            "input_tokens": profile.input_tokens,
            "output_tokens": profile.output_tokens,
            "tool_cost_usd": profile.tool_cost_usd,
        },
        "target_mpm": target_tier,
        "target_met": target_met(mpm, target_tier, tier_ranks),
        "observed_mpm": mpm,
        "coverage": coverage,
        "model_summaries": sorted(
            summaries,
            key=lambda summary: (
                tier_ranks[summary["tier"]],
                summary["cost_run"],
                summary["model_id"],
            ),
        ),
    }


def print_report(report: dict[str, Any]) -> None:
    observed = report["observed_mpm"]
    coverage = report["coverage"]
    print("MPM Ladder Evaluation")
    print(f"Workflow: {report['workflow_name']} ({report['workflow_id']})")
    print(
        "Profile: "
        f"{report['profile']['input_tokens']:,} input + "
        f"{report['profile']['output_tokens']:,} output tokens"
    )
    print()

    if observed:
        print(f"Observed MPM: {observed['tier']} via {observed['model_id']}")
    else:
        print("Observed MPM: none; no passing runs")
    target = report.get("target_mpm") or "n/a"
    met = report.get("target_met")
    met_text = "n/a" if met is None else ("met" if met else "not met")
    print(f"Target MPM:   {target} ({met_text})")
    print(f"Design tier:  {coverage['design_required_tier'] or 'none'}")
    print(
        "Automation:   "
        f"{coverage['automated_steps']}/{coverage['total_steps']} steps "
        f"({percent(coverage['automation_coverage'])})"
    )
    print(f"Agent steps:  {coverage['agent_steps']}/{coverage['total_steps']}")
    print(f"Human gates:  {coverage['human_gates']}/{coverage['total_steps']}")
    print()

    print_table(
        [
            "model",
            "tier",
            "pass@N",
            "cost/run",
            "cost/success",
            "AFR",
            "cost/useful-failure",
            "failure labels",
        ],
        [
            [
                summary["model_id"],
                summary["tier"],
                f"{summary['passes']}/{summary['attempts']}",
                money(summary["cost_run"]),
                money(summary["cost_success"]),
                percent(summary["actionable_failure_rate"]),
                money(summary["cost_useful_failure"]),
                ", ".join(f"{label}:{count}" for label, count in sorted(summary["failure_labels"].items())) or "-",
            ]
            for summary in report["model_summaries"]
        ],
    )


def command_evaluate(args: argparse.Namespace) -> int:
    models_doc = load_json(Path(args.models))
    workflow_doc = load_json(Path(args.workflow))
    runs_doc = load_json(Path(args.runs))
    profile = profile_from_args(args, workflow_doc.get("run_profile", {}))
    report = build_report(models_doc, workflow_doc, runs_doc, profile)

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_report(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mpm-ladder",
        description="Measure workflow MPM, cost, pass rate, and automation coverage.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prices = subparsers.add_parser("prices", help="Compare model costs for a token profile.")
    prices.add_argument("--models", default=str(DEFAULT_MODELS))
    prices.add_argument("--input-tokens", type=int, default=100_000)
    prices.add_argument("--output-tokens", type=int, default=20_000)
    prices.add_argument("--tool-cost-usd", type=float, default=0.0)
    prices.set_defaults(func=command_prices)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate a workflow against benchmark run logs.")
    evaluate.add_argument("--models", default=str(DEFAULT_MODELS))
    evaluate.add_argument("--workflow", default=str(DEFAULT_WORKFLOW))
    evaluate.add_argument("--runs", default=str(DEFAULT_RUNS))
    evaluate.add_argument("--input-tokens", type=int)
    evaluate.add_argument("--output-tokens", type=int)
    evaluate.add_argument("--tool-cost-usd", type=float)
    evaluate.add_argument("--format", choices=["text", "json"], default="text")
    evaluate.set_defaults(func=command_evaluate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
