"""Unit tests for main.py entry point."""

import sys
import unittest
from io import StringIO
from unittest.mock import patch


class TestMainMissingCredentials(unittest.TestCase):

    # AC3.1 — FileNotFoundError from get_credentials exits 1 with readable stderr message
    @patch("main.PhantomCalendarApp")
    @patch("main.get_credentials")
    def test_missing_credentials_exits_gracefully(self, mock_get_creds, mock_app_cls):
        mock_get_creds.side_effect = FileNotFoundError(
            "credentials.json not found at /some/path/credentials.json"
        )

        captured_stderr = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with patch("sys.stderr", captured_stderr), patch("sys.argv", ["main"]):
                import main

                main.main()

        self.assertEqual(ctx.exception.code, 1)
        error_output = captured_stderr.getvalue()
        self.assertIn("credentials.json", error_output)
        self.assertIn("Error", error_output)
        # No raw traceback — just a readable message
        self.assertNotIn("Traceback", error_output)
        # App must not have been launched
        mock_app_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
