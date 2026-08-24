import unittest

from analysis.pier_decision_report import build_report, render_markdown


def make_row(cohort, maturity, language, passed=True):
    return {
        "cohort": cohort,
        "task_family": "optimistic-concurrency",
        "project_maturity": maturity,
        "language": language,
        "passed": passed,
        "input_tokens": 1000,
        "cached_input_tokens": 500,
        "output_tokens": 200,
        "cost_usd": 0.001,
        "agent_steps": 3,
        "agent_seconds": 10.0,
        "finished_at": "2026-08-24T00:00:00Z",
        "agent_version": "2.4.6",
        "model": "openrouter/example/model",
    }


class PierDecisionReportTests(unittest.TestCase):
    def test_examples_are_separate_from_balanced_primary(self):
        rows = [
            make_row("primary", "brownfield", "javascript"),
            make_row("primary", "brownfield", "typescript"),
            make_row("primary", "greenfield", "javascript"),
            make_row("primary", "greenfield", "typescript"),
            make_row("example", "brownfield", "python"),
            make_row("example", "brownfield", "go"),
        ]

        report = build_report(rows)

        self.assertEqual((4, 4), (report["primary"]["runs"], report["primary"]["passed"]))
        self.assertEqual(
            (6, 6),
            (report["all_published"]["runs"], report["all_published"]["passed"]),
        )
        examples = {row["language"]: row for row in report["polyglot_examples"]}
        self.assertEqual({"python", "go"}, set(examples))
        self.assertEqual("none", examples["python"]["typecheck_config"])
        self.assertEqual("default", examples["go"]["typecheck_config"])
        self.assertTrue(
            all(row["interpretation"] == "illustrative_single_run" for row in examples.values())
        )

        markdown = render_markdown(report)
        self.assertIn("All 6 published attempts passed", markdown)
        self.assertIn("Python and Go examples", markdown)
        self.assertIn("not a four-language ranking", markdown)


if __name__ == "__main__":
    unittest.main()
