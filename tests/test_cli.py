import unittest

from mpm_ladder.cli import (
    RunProfile,
    build_report,
    get_tier_ranks,
    model_cost,
    observed_mpm,
    summarize_model_runs,
    workflow_coverage,
)


class MpmLadderTests(unittest.TestCase):
    def setUp(self):
        self.models = {
            "tiers": [
                {"id": "T4", "rank": 0},
                {"id": "T3", "rank": 1},
                {"id": "T2", "rank": 2},
            ],
            "models": [
                {
                    "id": "nano",
                    "provider": "Test",
                    "tier": "T4",
                    "input_per_mtok": 0.05,
                    "output_per_mtok": 0.4,
                },
                {
                    "id": "cheap",
                    "provider": "Test",
                    "tier": "T3",
                    "input_per_mtok": 1.0,
                    "output_per_mtok": 5.0,
                },
                {
                    "id": "balanced",
                    "provider": "Test",
                    "tier": "T2",
                    "input_per_mtok": 3.0,
                    "output_per_mtok": 15.0,
                },
            ],
        }

    def test_model_cost_uses_input_output_and_tool_cost(self):
        profile = RunProfile(input_tokens=100_000, output_tokens=20_000, tool_cost_usd=0.25)
        cost = model_cost(self.models["models"][0], profile)
        self.assertAlmostEqual(cost, 0.263)

    def test_observed_mpm_selects_lowest_passing_tier(self):
        profile = RunProfile(input_tokens=100_000, output_tokens=20_000)
        runs = {
            "attempts": [
                {"model_id": "nano", "status": "fail", "failure_label": "MODEL_ERROR"},
                {"model_id": "cheap", "status": "pass"},
                {"model_id": "balanced", "status": "pass"},
            ]
        }
        summaries = summarize_model_runs(self.models, runs, profile)
        mpm = observed_mpm(summaries, get_tier_ranks(self.models))
        self.assertEqual(mpm["model_id"], "cheap")
        self.assertEqual(mpm["tier"], "T3")

    def test_workflow_coverage_separates_script_agent_and_human(self):
        workflow = {
            "steps": [
                {"executor": "script"},
                {"executor": "rule"},
                {"executor": "T2"},
                {"executor": "human"},
            ]
        }
        coverage = workflow_coverage(workflow, get_tier_ranks(self.models))
        self.assertEqual(coverage["automated_steps"], 2)
        self.assertEqual(coverage["agent_steps"], 1)
        self.assertEqual(coverage["human_gates"], 1)
        self.assertAlmostEqual(coverage["automation_coverage"], 0.5)

    def test_report_marks_lower_observed_tier_as_target_met(self):
        profile = RunProfile(input_tokens=100_000, output_tokens=20_000)
        workflow = {
            "id": "sample",
            "name": "Sample",
            "target_mpm": "T2",
            "steps": [{"executor": "script"}, {"executor": "T2"}],
        }
        runs = {
            "attempts": [
                {"model_id": "cheap", "status": "pass"},
                {"model_id": "balanced", "status": "pass"},
            ]
        }
        report = build_report(self.models, workflow, runs, profile)
        self.assertEqual(report["observed_mpm"]["tier"], "T3")
        self.assertTrue(report["target_met"])


if __name__ == "__main__":
    unittest.main()
