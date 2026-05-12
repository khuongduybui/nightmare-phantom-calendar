"""Unit tests for auth.py OAuth lifecycle."""

import os
import unittest
from unittest.mock import MagicMock, mock_open, patch


class TestGetCredentials(unittest.TestCase):

    # AC2.3 — first run triggers browser flow and writes token
    @patch("auth.os.chmod")
    @patch("auth.open", new_callable=mock_open)
    @patch("auth.InstalledAppFlow")
    @patch("auth.os.path.exists")
    def test_first_run_triggers_browser_flow(
        self, mock_exists, mock_flow_cls, mock_file, mock_chmod
    ):
        # token.json absent, credentials.json present
        def exists_side_effect(path):
            if path == auth.CREDENTIALS_FILE:
                return True
            if path == auth.TOKEN_FILE:
                return False
            return False

        mock_exists.side_effect = exists_side_effect

        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = "{}"
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_cls.from_client_secrets_file.return_value = mock_flow

        result = auth.get_credentials()

        mock_flow_cls.from_client_secrets_file.assert_called_once_with(
            auth.CREDENTIALS_FILE, auth.SCOPES
        )
        mock_flow.run_local_server.assert_called_once_with(port=0)
        mock_file.assert_called_once_with(auth.TOKEN_FILE, "w")
        mock_chmod.assert_called_once_with(auth.TOKEN_FILE, 0o600)
        self.assertIs(result, mock_creds)

    # AC2.4 — valid token returns immediately, no flow or refresh
    @patch("auth.Credentials")
    @patch("auth.os.path.exists")
    def test_valid_token_no_flow(self, mock_exists, mock_creds_cls):
        mock_exists.return_value = True

        mock_creds = MagicMock()
        mock_creds.valid = True
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        with patch("auth.InstalledAppFlow") as mock_flow_cls:
            result = auth.get_credentials()

        mock_flow_cls.from_client_secrets_file.assert_not_called()
        mock_creds.refresh.assert_not_called()
        self.assertIs(result, mock_creds)

    # AC2.5 — expired token with refresh_token triggers refresh and rewrites token
    @patch("auth.os.chmod")
    @patch("auth.open", new_callable=mock_open)
    @patch("auth.Request")
    @patch("auth.Credentials")
    @patch("auth.os.path.exists")
    def test_expired_token_refreshes(
        self, mock_exists, mock_creds_cls, mock_request_cls, mock_file, mock_chmod
    ):
        mock_exists.return_value = True

        mock_creds = MagicMock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "some-refresh-token"
        mock_creds.to_json.return_value = "{}"
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        result = auth.get_credentials()

        mock_creds.refresh.assert_called_once()
        mock_file.assert_called_once_with(auth.TOKEN_FILE, "w")
        mock_chmod.assert_called_once_with(auth.TOKEN_FILE, 0o600)
        self.assertIs(result, mock_creds)

    # AC2.6 — missing credentials.json raises FileNotFoundError
    @patch("auth.os.path.exists")
    def test_missing_credentials_raises(self, mock_exists):
        mock_exists.return_value = False

        with self.assertRaises(FileNotFoundError):
            auth.get_credentials()


import auth  # noqa: E402 — imported after patches to allow module-level mocking

if __name__ == "__main__":
    unittest.main()
