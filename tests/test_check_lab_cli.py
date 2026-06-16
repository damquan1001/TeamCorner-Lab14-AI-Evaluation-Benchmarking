import subprocess
import sys
import unittest


class CheckLabCliTests(unittest.TestCase):
    def test_check_lab_runs_with_default_python_command(self):
        completed = subprocess.run(
            [sys.executable, "check_lab.py"],
            capture_output=True,
            encoding="utf-8",
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
