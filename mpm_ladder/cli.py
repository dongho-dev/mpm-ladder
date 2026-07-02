from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODELS = ROOT / "data" / "models.json"
DEFAULT_WORKFLOW = ROOT / "examples" / "workflows" / "ci-recovery.json"
DEFAULT_RUNS = ROOT / "examples" / "runs" / "ci-recovery-runs.json"
DEFAULT_WORKSPACE = ROOT / ".mpm-ladder" / "workspace.json"
DASHBOARD_DIR = ROOT / "dashboard"
SCORING_VERSION = "0.2.0"

AUTOMATED_EXECUTORS = {"script", "rule", "ci"}
HUMAN_EXECUTORS = {"human"}


@dataclass(frozen=True)
class RunProfile:
    input_tokens: int
    output_tokens: int
    tool_cost_usd: float = 0.0


@dataclass(frozen=True)
class WorkspaceBundle:
    workspace_path: Path
    workspace_doc: dict[str, Any]
    workflow_entry: dict[str, Any]
    models_path: Path
    workflow_path: Path
    runs_path: Path
    reports_dir: Path
    models_doc: dict[str, Any]
    workflow_doc: dict[str, Any]
    runs_doc: dict[str, Any]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def resolve_path(base_path: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base_path.parent / path).resolve()


def relative_path(base_path: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(base_path.parent.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def canonical_json(doc: Any) -> str:
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def document_hash(doc: Any) -> str:
    digest = hashlib.sha256(canonical_json(doc).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


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


def seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    minutes, secs = divmod(round(value), 60)
    return f"{minutes}:{secs:02d}"


def get_tier_ranks(models_doc: dict[str, Any]) -> dict[str, int]:
    return {tier["id"]: int(tier["rank"]) for tier in models_doc["tiers"]}


def model_cost(model: dict[str, Any], profile: RunProfile) -> float:
    input_cost = profile.input_tokens / 1_000_000 * float(model["input_per_mtok"])
    output_cost = profile.output_tokens / 1_000_000 * float(model["output_per_mtok"])
    return input_cost + output_cost + profile.tool_cost_usd


def profile_from_args(args: argparse.Namespace, fallback: dict[str, Any] | None = None) -> RunProfile:
    fallback = fallback or {}
    return RunProfile(
        input_tokens=int(args.input_tokens if args.input_tokens is not None else fallback.get("input_tokens", 100_000)),
        output_tokens=int(args.output_tokens if args.output_tokens is not None else fallback.get("output_tokens", 20_000)),
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


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * pct
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


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
        durations = [
            float(attempt["duration_seconds"])
            for attempt in attempts
            if attempt.get("duration_seconds") is not None
        ]
        pass_rate = passes / len(attempts) if attempts else None
        avg_duration = sum(durations) / len(durations) if durations else None
        summaries.append(
            {
                "model_id": model_id,
                "provider": model["provider"],
                "tier": model["tier"],
                "attempts": len(attempts),
                "passes": passes,
                "failures": failures,
                "pass_rate": pass_rate,
                "cost_run": cost,
                "cost_success": cost * len(attempts) / passes if passes else None,
                "expected_cost_per_success": cost / pass_rate if pass_rate else None,
                "actionable_failure_rate": actionable / failures if failures else None,
                "cost_useful_failure": cost * len(attempts) / actionable if actionable else None,
                "avg_duration_seconds": avg_duration,
                "p50_duration_seconds": percentile(durations, 0.50),
                "p95_duration_seconds": percentile(durations, 0.95),
                "expected_time_per_success": avg_duration / pass_rate if avg_duration is not None and pass_rate else None,
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


def reliable_mpm(
    summaries: list[dict[str, Any]],
    tier_ranks: dict[str, int],
    min_pass_rate: float,
    min_attempts: int,
) -> dict[str, Any] | None:
    passing = [
        summary
        for summary in summaries
        if summary["passes"] > 0
        and summary["attempts"] >= min_attempts
        and (summary["pass_rate"] or 0.0) >= min_pass_rate
    ]
    if not passing:
        return None
    return sorted(
        passing,
        key=lambda summary: (
            tier_ranks[summary["tier"]],
            summary["expected_cost_per_success"] if summary["expected_cost_per_success"] is not None else float("inf"),
            summary["cost_run"],
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


def target_met(summary: dict[str, Any] | None, target_tier: str | None, tier_ranks: dict[str, int]) -> bool | None:
    if summary is None or not target_tier:
        return None
    if target_tier not in tier_ranks:
        return None
    return tier_ranks[summary["tier"]] <= tier_ranks[target_tier]


def workflow_version(workflow_doc: dict[str, Any]) -> str:
    version = workflow_doc.get("version")
    if isinstance(version, dict):
        return str(version.get("id") or version.get("version") or "unversioned")
    return str(workflow_doc.get("version_id") or "unversioned")


def semantic_workflow(workflow_doc: dict[str, Any], workflow_hash: str) -> dict[str, Any]:
    return {
        "id": workflow_doc.get("id"),
        "name": workflow_doc.get("name"),
        "kind": workflow_doc.get("kind", "workflow"),
        "version": workflow_version(workflow_doc),
        "hash": workflow_hash,
        "domain": workflow_doc.get("domain"),
        "owner": workflow_doc.get("owner"),
        "intent": workflow_doc.get("intent"),
        "risk_class": workflow_doc.get("risk_class"),
        "target_mpm": workflow_doc.get("target_mpm"),
        "objective": workflow_doc.get("objective"),
        "inputs": workflow_doc.get("inputs", []),
        "outputs": workflow_doc.get("outputs", []),
        "success_criteria": workflow_doc.get("success_criteria", []),
        "allowed_actions": workflow_doc.get("allowed_actions", []),
        "forbidden_actions": workflow_doc.get("forbidden_actions", []),
        "human_gates": workflow_doc.get("human_gates", []),
        "failure_taxonomy": workflow_doc.get("failure_taxonomy", []),
        "steps": workflow_doc.get("steps", []),
    }


def report_warnings(
    workflow_doc: dict[str, Any],
    runs_doc: dict[str, Any],
    workflow_hash: str,
) -> list[str]:
    warnings = []
    if runs_doc.get("workflow_id") and workflow_doc.get("id") and runs_doc.get("workflow_id") != workflow_doc.get("id"):
        warnings.append(f"Run log workflow_id {runs_doc.get('workflow_id')} does not match workflow {workflow_doc.get('id')}.")
    if runs_doc.get("workflow_version") and runs_doc.get("workflow_version") != workflow_version(workflow_doc):
        warnings.append(
            f"Run log workflow_version {runs_doc.get('workflow_version')} does not match workflow {workflow_version(workflow_doc)}."
        )
    if runs_doc.get("workflow_hash") and runs_doc.get("workflow_hash") != workflow_hash:
        warnings.append("Run log workflow_hash does not match the current workflow content hash.")
    return warnings


def build_report(
    models_doc: dict[str, Any],
    workflow_doc: dict[str, Any],
    runs_doc: dict[str, Any],
    profile: RunProfile,
    min_pass_rate: float = 0.0,
    min_attempts: int = 1,
    objective_profile: str | None = None,
) -> dict[str, Any]:
    tier_ranks = get_tier_ranks(models_doc)
    summaries = summarize_model_runs(models_doc, runs_doc, profile)
    observed = observed_mpm(summaries, tier_ranks)
    reliable = reliable_mpm(summaries, tier_ranks, min_pass_rate, min_attempts)
    target_tier = workflow_doc.get("target_mpm")
    coverage = workflow_coverage(workflow_doc, tier_ranks)
    workflow_hash = document_hash(workflow_doc)
    models_hash = document_hash(models_doc)

    sorted_summaries = sorted(
        summaries,
        key=lambda summary: (
            tier_ranks[summary["tier"]],
            summary["cost_run"],
            summary["model_id"],
        ),
    )

    return {
        "schema_version": 1,
        "scoring_version": SCORING_VERSION,
        "workflow_id": workflow_doc.get("id"),
        "workflow_name": workflow_doc.get("name"),
        "workflow_version": workflow_version(workflow_doc),
        "workflow_hash": workflow_hash,
        "workflow": semantic_workflow(workflow_doc, workflow_hash),
        "measurement": {
            "run_set_id": runs_doc.get("run_set_id"),
            "measured_at": runs_doc.get("measured_at"),
            "workflow_id": runs_doc.get("workflow_id"),
            "workflow_version": runs_doc.get("workflow_version"),
            "workflow_hash": runs_doc.get("workflow_hash"),
            "models_hash": models_hash,
            "objective_profile": objective_profile or runs_doc.get("objective_profile"),
            "min_pass_rate": min_pass_rate,
            "min_attempts": min_attempts,
        },
        "profile": {
            "input_tokens": profile.input_tokens,
            "output_tokens": profile.output_tokens,
            "tool_cost_usd": profile.tool_cost_usd,
        },
        "target_mpm": target_tier,
        "target_met": target_met(observed, target_tier, tier_ranks),
        "reliable_target_met": target_met(reliable, target_tier, tier_ranks),
        "observed_mpm": observed,
        "reliable_mpm": reliable,
        "coverage": coverage,
        "model_summaries": sorted_summaries,
        "failure_totals": failure_totals(sorted_summaries),
        "warnings": report_warnings(workflow_doc, runs_doc, workflow_hash),
    }


def failure_totals(summaries: list[dict[str, Any]]) -> dict[str, int]:
    totals: Counter[str] = Counter()
    for summary in summaries:
        totals.update(summary["failure_labels"])
    return dict(sorted(totals.items()))


def print_report(report: dict[str, Any]) -> None:
    observed = report["observed_mpm"]
    reliable = report["reliable_mpm"]
    coverage = report["coverage"]
    measurement = report["measurement"]
    print("MPM Ladder Workflow Evaluation")
    print(f"Workflow: {report['workflow_name']} ({report['workflow_id']})")
    print(f"Version:  {report['workflow_version']}")
    print(f"Hash:     {report['workflow_hash']}")
    print(
        "Profile:  "
        f"{report['profile']['input_tokens']:,} input + "
        f"{report['profile']['output_tokens']:,} output tokens"
    )
    print()

    if observed:
        print(f"Observed MPM: {observed['tier']} via {observed['model_id']}")
    else:
        print("Observed MPM: none; no passing runs")
    if reliable:
        print(
            "Reliable MPM: "
            f"{reliable['tier']} via {reliable['model_id']} "
            f"({percent(measurement['min_pass_rate'])}, n>={measurement['min_attempts']})"
        )
    else:
        print(f"Reliable MPM: none ({percent(measurement['min_pass_rate'])}, n>={measurement['min_attempts']})")
    target = report.get("target_mpm") or "n/a"
    reliable_met = report.get("reliable_target_met")
    met_text = "n/a" if reliable_met is None else ("met" if reliable_met else "not met")
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
            "avg time",
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
                seconds(summary["avg_duration_seconds"]),
                percent(summary["actionable_failure_rate"]),
                money(summary["cost_useful_failure"]),
                ", ".join(f"{label}:{count}" for label, count in sorted(summary["failure_labels"].items())) or "-",
            ]
            for summary in report["model_summaries"]
        ],
    )
    if report["warnings"]:
        print()
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"- {warning}")


def render_markdown_report(report: dict[str, Any]) -> str:
    observed = report["observed_mpm"]
    reliable = report["reliable_mpm"]
    coverage = report["coverage"]
    lines = [
        f"# {report['workflow_name']} MPM Report",
        "",
        f"- Workflow id: `{report['workflow_id']}`",
        f"- Version: `{report['workflow_version']}`",
        f"- Hash: `{report['workflow_hash']}`",
        f"- Target MPM: `{report.get('target_mpm') or 'n/a'}`",
        f"- Observed MPM: `{observed['tier']} via {observed['model_id']}`" if observed else "- Observed MPM: none",
        f"- Reliable MPM: `{reliable['tier']} via {reliable['model_id']}`" if reliable else "- Reliable MPM: none",
        f"- Automation coverage: {coverage['automated_steps']}/{coverage['total_steps']} ({percent(coverage['automation_coverage'])})",
        "",
        "## Model Summary",
        "",
        "| model | tier | pass@N | cost/run | cost/success | avg time | AFR |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for summary in report["model_summaries"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    summary["model_id"],
                    summary["tier"],
                    f"{summary['passes']}/{summary['attempts']}",
                    money(summary["cost_run"]),
                    money(summary["cost_success"]),
                    seconds(summary["avg_duration_seconds"]),
                    percent(summary["actionable_failure_rate"]),
                ]
            )
            + " |"
        )
    if report["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
    lines.append("")
    return "\n".join(lines)


def load_workspace(workspace_path: Path) -> dict[str, Any]:
    return load_json(workspace_path)


def workspace_workflows(workspace_doc: dict[str, Any]) -> list[dict[str, Any]]:
    return list(workspace_doc.get("workflows", []))


def find_workflow_entry(workspace_doc: dict[str, Any], workflow_id: str | None) -> dict[str, Any]:
    workflows = workspace_workflows(workspace_doc)
    if not workflows:
        raise ValueError("Workspace does not define any workflows.")
    if workflow_id is None:
        return workflows[0]
    for workflow in workflows:
        if workflow.get("id") == workflow_id:
            return workflow
    raise ValueError(f"Unknown workflow id: {workflow_id}")


def load_workspace_bundle(
    workspace_path: Path,
    workflow_id: str | None,
    runs_path: str | None = None,
) -> WorkspaceBundle:
    workspace_doc = load_workspace(workspace_path)
    workflow_entry = find_workflow_entry(workspace_doc, workflow_id)
    models_path = resolve_path(workspace_path, workspace_doc.get("models_path", str(DEFAULT_MODELS)))
    workflow_path = resolve_path(workspace_path, workflow_entry["current_workflow_path"])
    run_path_value = runs_path or workflow_entry.get("default_runs_path")
    if not run_path_value:
        raise ValueError(f"Workflow {workflow_entry.get('id')} does not define default_runs_path.")
    resolved_runs_path = resolve_path(workspace_path, run_path_value)
    reports_dir = resolve_path(workspace_path, workflow_entry.get("reports_dir", f"reports/{workflow_entry['id']}"))
    return WorkspaceBundle(
        workspace_path=workspace_path,
        workspace_doc=workspace_doc,
        workflow_entry=workflow_entry,
        models_path=models_path,
        workflow_path=workflow_path,
        runs_path=resolved_runs_path,
        reports_dir=reports_dir,
        models_doc=load_json(models_path),
        workflow_doc=load_json(workflow_path),
        runs_doc=load_json(resolved_runs_path),
    )


def report_from_args(args: argparse.Namespace) -> tuple[dict[str, Any], WorkspaceBundle | None]:
    if args.workspace or args.workflow_id:
        workspace_path = Path(args.workspace or DEFAULT_WORKSPACE)
        bundle = load_workspace_bundle(workspace_path, args.workflow_id, args.runs)
        profile = profile_from_args(args, bundle.workflow_doc.get("run_profile", {}))
        report = build_report(
            bundle.models_doc,
            bundle.workflow_doc,
            bundle.runs_doc,
            profile,
            min_pass_rate=args.min_pass_rate,
            min_attempts=args.min_attempts,
            objective_profile=args.objective,
        )
        report["source_paths"] = {
            "workspace": str(bundle.workspace_path),
            "models": str(bundle.models_path),
            "workflow": str(bundle.workflow_path),
            "runs": str(bundle.runs_path),
        }
        return report, bundle

    models_doc = load_json(Path(args.models or DEFAULT_MODELS))
    workflow_doc = load_json(Path(args.workflow or DEFAULT_WORKFLOW))
    runs_doc = load_json(Path(args.runs or DEFAULT_RUNS))
    profile = profile_from_args(args, workflow_doc.get("run_profile", {}))
    return (
        build_report(
            models_doc,
            workflow_doc,
            runs_doc,
            profile,
            min_pass_rate=args.min_pass_rate,
            min_attempts=args.min_attempts,
            objective_profile=args.objective,
        ),
        None,
    )


def command_evaluate(args: argparse.Namespace) -> int:
    report, _bundle = report_from_args(args)

    if args.report_out:
        write_json(Path(args.report_out), report)

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_report(report)
    return 0


def command_report(args: argparse.Namespace) -> int:
    report, bundle = report_from_args(args)
    if args.output:
        output = Path(args.output)
    elif bundle:
        bundle.reports_dir.mkdir(parents=True, exist_ok=True)
        suffix = "md" if args.format == "markdown" else "json"
        output = bundle.reports_dir / f"{report['workflow_id']}-{utc_stamp()}.report.{suffix}"
    else:
        suffix = "md" if args.format == "markdown" else "json"
        output = ROOT / f"{report['workflow_id']}-{utc_stamp()}.report.{suffix}"

    if args.format == "markdown":
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown_report(report), encoding="utf-8", newline="\n")
    else:
        write_json(output, report)
    print(f"Wrote {output}")
    return 0


def command_workflows(args: argparse.Namespace) -> int:
    workspace_path = Path(args.workspace)
    workspace_doc = load_workspace(workspace_path)
    rows = []
    for workflow in workspace_workflows(workspace_doc):
        rows.append(
            [
                str(workflow.get("id", "")),
                str(workflow.get("name", "")),
                str(workflow.get("owner", "")),
                str(workflow.get("current_workflow_path", "")),
                str(workflow.get("default_runs_path", "")),
            ]
        )
    print(f"Workspace: {workspace_doc.get('name', workspace_doc.get('id', workspace_path))}")
    print_table(["id", "name", "owner", "workflow", "runs"], rows)
    return 0


def initial_workspace_doc() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "id": "local-workspace",
        "name": "Local MPM Ladder Workspace",
        "storage_mode": "local_files",
        "privacy_boundary": "customer_local",
        "models_path": "../data/models.json",
        "workflows": [
            {
                "id": "ci-recovery",
                "name": "CI recovery workflow",
                "domain": "platform-engineering",
                "owner": "platform",
                "current_workflow_path": "../examples/workflows/ci-recovery.json",
                "default_runs_path": "../examples/runs/ci-recovery-runs.json",
                "reports_dir": "reports/ci-recovery",
                "versions": [],
            }
        ],
    }


def command_init(args: argparse.Namespace) -> int:
    workspace_path = Path(args.workspace)
    if workspace_path.exists() and not args.force:
        print(f"Workspace already exists: {workspace_path}")
        return 0
    write_json(workspace_path, initial_workspace_doc())
    for dirname in ["workflows", "runs", "traces", "reports"]:
        (workspace_path.parent / dirname).mkdir(parents=True, exist_ok=True)
    print(f"Initialized workspace: {workspace_path}")
    return 0


def command_snapshot(args: argparse.Namespace) -> int:
    workspace_path = Path(args.workspace)
    workspace_doc = load_workspace(workspace_path)
    workflow_entry = find_workflow_entry(workspace_doc, args.workflow_id)
    current_path = resolve_path(workspace_path, workflow_entry["current_workflow_path"])
    version_id = args.version or utc_stamp()
    snapshot_dir = workspace_path.parent / "workflows" / workflow_entry["id"] / "versions"
    snapshot_path = snapshot_dir / f"{version_id}.workflow.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(current_path, snapshot_path)
    snapshot_hash = file_hash(snapshot_path)

    version_record = {
        "version": version_id,
        "workflow_path": relative_path(workspace_path, snapshot_path),
        "hash": snapshot_hash,
        "created_at": utc_stamp(),
        "note": args.note,
    }
    versions = workflow_entry.setdefault("versions", [])
    versions[:] = [item for item in versions if item.get("version") != version_id]
    versions.append(version_record)
    write_json(workspace_path, workspace_doc)
    print(f"Snapshotted {workflow_entry['id']} {version_id}")
    print(f"Hash: {snapshot_hash}")
    print(f"Path: {snapshot_path}")
    return 0


def command_dashboard(args: argparse.Namespace) -> int:
    port = int(args.port)
    url = f"http://127.0.0.1:{port}/dashboard/index.html?workspace=../.mpm-ladder/workspace.json"
    script = DASHBOARD_DIR / "serve.ps1"
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Port",
        str(port),
    ]
    if args.no_server:
        print(url)
        return 0
    subprocess.Popen(command)
    print(f"Dashboard: {url}")
    return 0


def add_shared_eval_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", default=None, help="Workspace registry path. Enables workspace workflow lookup.")
    parser.add_argument("--workflow-id", help="Workflow id inside the workspace registry.")
    parser.add_argument("--models")
    parser.add_argument("--workflow")
    parser.add_argument("--runs")
    parser.add_argument("--input-tokens", type=int)
    parser.add_argument("--output-tokens", type=int)
    parser.add_argument("--tool-cost-usd", type=float)
    parser.add_argument("--objective", default=None)
    parser.add_argument("--min-pass-rate", type=float, default=0.9)
    parser.add_argument("--min-attempts", type=int, default=3)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mpm-ladder",
        description="Measure workflow MPM, cost, pass rate, automation coverage, and workflow version evidence.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prices = subparsers.add_parser("prices", help="Compare model costs for a token profile.")
    prices.add_argument("--models", default=str(DEFAULT_MODELS))
    prices.add_argument("--input-tokens", type=int, default=100_000)
    prices.add_argument("--output-tokens", type=int, default=20_000)
    prices.add_argument("--tool-cost-usd", type=float, default=0.0)
    prices.set_defaults(func=command_prices)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate a workflow against benchmark run logs.")
    add_shared_eval_args(evaluate)
    evaluate.add_argument("--format", choices=["text", "json"], default="text")
    evaluate.add_argument("--report-out", help="Optional JSON path to write the report.")
    evaluate.set_defaults(func=command_evaluate)

    report = subparsers.add_parser("report", help="Write a version-linked workflow report.")
    add_shared_eval_args(report)
    report.add_argument("--format", choices=["json", "markdown"], default="json")
    report.add_argument("--output", help="Output report path. Defaults under the workflow reports_dir.")
    report.set_defaults(func=command_report)

    workflows = subparsers.add_parser("workflows", help="List workflows in a workspace registry.")
    workflows.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    workflows.set_defaults(func=command_workflows)

    init = subparsers.add_parser("init", help="Initialize a local file-based MPM Ladder workspace.")
    init.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    snapshot = subparsers.add_parser("snapshot", help="Snapshot a semantic workflow definition into workspace versions.")
    snapshot.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    snapshot.add_argument("--workflow-id", default="ci-recovery")
    snapshot.add_argument("--version")
    snapshot.add_argument("--note")
    snapshot.set_defaults(func=command_snapshot)

    dashboard = subparsers.add_parser("dashboard", help="Print or start the local dashboard URL.")
    dashboard.add_argument("--port", type=int, default=8787)
    dashboard.add_argument("--no-server", action="store_true")
    dashboard.set_defaults(func=command_dashboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))
