"""Unit tests for osaurus_client.suggest_meeting_type (NPC-0013 US-2)."""

import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

CATEGORIES = ["Daily standup", "Interview", "Regular online meeting"]
OSAURUS_CONFIG = {
    "server": "http://127.0.0.1:1337",
    "api_key": "test-key",
    "default_module": "foundation",
}


def _make_completion(content: str) -> MagicMock:
    """Build a mock openai ChatCompletion response."""
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


class TestSuggestMeetingTypeHappyPath(unittest.TestCase):

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_returns_matched_category(self, mock_openai_cls, _mock_cfg):
        """AC2.2 — valid model response matched against categories."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Interview")
        mock_openai_cls.return_value = mock_client

        result = osaurus_client.suggest_meeting_type(
            "Candidate call", "30-min loop", CATEGORIES
        )
        self.assertEqual(result, "Interview")

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_strips_whitespace_before_matching(self, mock_openai_cls, _mock_cfg):
        """AC2.2 — response with surrounding whitespace is still matched."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion(
            "  Interview  "
        )
        mock_openai_cls.return_value = mock_client

        result = osaurus_client.suggest_meeting_type("Candidate call", "", CATEGORIES)
        self.assertEqual(result, "Interview")

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_returns_none_for_unrecognised_response(self, mock_openai_cls, _mock_cfg):
        """AC2.3 — model returns a string not in categories."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Workshop")
        mock_openai_cls.return_value = mock_client

        result = osaurus_client.suggest_meeting_type("Design workshop", "", CATEGORIES)
        self.assertIsNone(result)

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_returns_none_for_empty_response(self, mock_openai_cls, _mock_cfg):
        """AC2.3 — model returns an empty string."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("")
        mock_openai_cls.return_value = mock_client

        result = osaurus_client.suggest_meeting_type("Unnamed event", "", CATEGORIES)
        self.assertIsNone(result)


class TestSuggestMeetingTypeParameters(unittest.TestCase):

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_uses_model_from_config(self, mock_openai_cls, _mock_cfg):
        """AC2.1 — model name comes from osaurus.yaml default_module."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Interview")
        mock_openai_cls.return_value = mock_client

        osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "foundation")

    @patch(
        "osaurus_client._load_config",
        return_value={**OSAURUS_CONFIG, "default_module": "mymodel"},
    )
    @patch("osaurus_client.OpenAI")
    def test_uses_model_from_config_when_overridden(self, mock_openai_cls, _mock_cfg):
        """AC2.1 — respects non-default value in default_module field."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Interview")
        mock_openai_cls.return_value = mock_client

        osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "mymodel")

    @patch(
        "osaurus_client._load_config",
        return_value={**OSAURUS_CONFIG, "default_module": None},
    )
    @patch("osaurus_client.OpenAI")
    def test_falls_back_to_foundation_when_default_module_absent(
        self, mock_openai_cls, _mock_cfg
    ):
        """AC2.1 — falls back to 'foundation' when default_module is None/absent."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Interview")
        mock_openai_cls.return_value = mock_client

        osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "foundation")

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_uses_temperature_zero_and_max_tokens_32(self, mock_openai_cls, _mock_cfg):
        """AC2.1 — temperature=0 and max_tokens=32."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Interview")
        mock_openai_cls.return_value = mock_client

        osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["temperature"], 0)
        self.assertEqual(call_kwargs["max_tokens"], 32)

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_timeout_forwarded_to_client(self, mock_openai_cls, _mock_cfg):
        """AC2.1 — timeout parameter passed to OpenAI constructor."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Interview")
        mock_openai_cls.return_value = mock_client

        osaurus_client.suggest_meeting_type("Call", "", CATEGORIES, timeout=1.5)
        mock_openai_cls.assert_called_once()
        _, ctor_kwargs = mock_openai_cls.call_args
        self.assertEqual(ctor_kwargs["timeout"], 1.5)


class TestSuggestMeetingTypeNoRetry(unittest.TestCase):

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_openai_client_called_exactly_once_on_success(
        self, mock_openai_cls, _mock_cfg
    ):
        """AC2.5 — exactly one completion call on success."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Interview")
        mock_openai_cls.return_value = mock_client

        osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_openai_client_called_exactly_once_on_failure(
        self, mock_openai_cls, _mock_cfg
    ):
        """AC2.5 — exactly one completion call even when an exception is raised (no retry)."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("refused")
        mock_openai_cls.return_value = mock_client

        result = osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        self.assertIsNone(result)
        self.assertEqual(mock_client.chat.completions.create.call_count, 1)


class TestSuggestMeetingTypeExceptions(unittest.TestCase):

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_connection_error_returns_none(self, mock_openai_cls, _mock_cfg):
        """AC2.4 — ConnectionError → None."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("refused")
        mock_openai_cls.return_value = mock_client

        result = osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        self.assertIsNone(result)

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_timeout_error_returns_none(self, mock_openai_cls, _mock_cfg):
        """AC2.4 — TimeoutError → None."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = TimeoutError("timed out")
        mock_openai_cls.return_value = mock_client

        result = osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        self.assertIsNone(result)

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_generic_exception_returns_none(self, mock_openai_cls, _mock_cfg):
        """AC2.4 — generic Exception → None."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("unexpected")
        mock_openai_cls.return_value = mock_client

        result = osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        self.assertIsNone(result)

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_failure_writes_exactly_one_stderr_line(self, mock_openai_cls, _mock_cfg):
        """AC2.6 — exactly one log record emitted on failure."""

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("refused")
        mock_openai_cls.return_value = mock_client

        with self.assertLogs("osaurus_client", level="WARNING") as log_ctx:
            osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)

        self.assertEqual(len(log_ctx.records), 1)

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_stderr_does_not_contain_api_key(self, mock_openai_cls, _mock_cfg):
        """AC2.6, AC2.13 — api_key must not appear in stderr output."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("refused")
        mock_openai_cls.return_value = mock_client

        captured = StringIO()
        with patch("sys.stderr", captured):
            osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)

        self.assertNotIn("test-key", captured.getvalue())

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_stderr_does_not_contain_title_or_description(
        self, mock_openai_cls, _mock_cfg
    ):
        """AC2.6, AC2.15 — event title and description must not appear in stderr."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("boom")
        mock_openai_cls.return_value = mock_client

        captured = StringIO()
        with patch("sys.stderr", captured):
            osaurus_client.suggest_meeting_type(
                "Super secret meeting title", "confidential details here", CATEGORIES
            )

        self.assertNotIn("Super secret meeting title", captured.getvalue())
        self.assertNotIn("confidential details here", captured.getvalue())


class TestSuggestMeetingTypeYamlFailure(unittest.TestCase):

    @patch("osaurus_client._load_config", side_effect=FileNotFoundError("no file"))
    def test_missing_yaml_returns_none(self, _mock_cfg):
        """AC2.7 — missing osaurus.yaml → None."""
        result = osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        self.assertIsNone(result)

    @patch("osaurus_client._load_config", side_effect=Exception("bad yaml"))
    def test_unparseable_yaml_returns_none(self, _mock_cfg):
        """AC2.7 — unparseable osaurus.yaml → None."""
        result = osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        self.assertIsNone(result)

    @patch("osaurus_client._load_config", side_effect=FileNotFoundError("no file"))
    def test_yaml_failure_writes_stderr(self, _mock_cfg):
        """AC2.6, AC2.7 — osaurus.yaml failure logs exactly one warning record."""
        with self.assertLogs("osaurus_client", level="WARNING") as log_ctx:
            osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)

        self.assertEqual(len(log_ctx.records), 1)
        self.assertEqual(log_ctx.records[0].levelname, "WARNING")


class TestNoLiveNetworkCalls(unittest.TestCase):
    """AC2.8 — All tests must use mocks; no live HTTP traffic."""

    @patch("osaurus_client._load_config", return_value=OSAURUS_CONFIG)
    @patch("osaurus_client.OpenAI")
    def test_openai_constructor_always_mocked(self, mock_openai_cls, _mock_cfg):
        """Confirm OpenAI() is always the mock, never the real class."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_completion("Interview")
        mock_openai_cls.return_value = mock_client

        osaurus_client.suggest_meeting_type("Call", "", CATEGORIES)
        mock_openai_cls.assert_called_once()


import osaurus_client  # noqa: E402

if __name__ == "__main__":
    unittest.main()
