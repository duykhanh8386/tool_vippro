import unittest

from src.task_runtime import active_run_count, create_run_context


class ActiveRunCountTests(unittest.TestCase):
    def test_counts_only_feature_runs_and_returns_to_zero_after_cleanup(self):
        self.assertEqual(active_run_count(), 0)
        context = create_run_context("test-update-guard")
        self.assertEqual(active_run_count(), 1)

        context.cleanup()
        self.assertEqual(active_run_count(), 0)


if __name__ == "__main__":
    unittest.main()
