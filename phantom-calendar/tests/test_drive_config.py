"""Unit tests for drive_config.py."""

import os
import unittest
from unittest.mock import patch

VALID_YAML = """
calendars:
  personal_id: test@example.com
  msi_id: work@example.com
  daily_run_time: "18:00"
timezone: America/Chicago
default_prep_minutes: 20
baseline_event:
  id: abc123
  title: My Alarm
  time: "08:00"
recurring_meetings:
  - name: Morning Standup
    start: "09:00"
    end: "09:15"
    days: [Mon, Tue, Wed]
    prep_minutes: 10
    notes: Quick sync
meeting_type_prep:
  Daily standup: 5
  In-person (local): travel+10
locations:
  Office: 30
client_overrides:
  Acme Corp: 45
"""


class TestReadConfig(unittest.TestCase):

    @patch("drive_config.get_drive_service")
    def test_read_config_returns_valid_yaml_unchanged(self, mock_svc):
        mock_svc.return_value.files.return_value.get_media.return_value.execute.return_value = (
            VALID_YAML
        )
        with patch.object(drive_config, "bootstrap_config") as mock_bootstrap:
            result = drive_config.read_config()
        self.assertEqual(result, VALID_YAML)
        mock_bootstrap.assert_not_called()

    @patch("drive_config.bootstrap_config")
    @patch("drive_config.get_drive_service")
    def test_read_config_invalid_yaml_triggers_bootstrap(
        self, mock_svc, mock_bootstrap
    ):
        mock_svc.return_value.files.return_value.get_media.return_value.execute.return_value = (
            "not: valid: yaml: :::"
        )
        result = drive_config.read_config()
        mock_bootstrap.assert_called_once()
        self.assertEqual(result, drive_config.DEFAULT_CONFIG_YAML)

    @patch("drive_config.bootstrap_config")
    @patch("drive_config.get_drive_service")
    def test_read_config_empty_content_triggers_bootstrap(
        self, mock_svc, mock_bootstrap
    ):
        mock_svc.return_value.files.return_value.get_media.return_value.execute.return_value = (
            ""
        )
        result = drive_config.read_config()
        mock_bootstrap.assert_called_once()
        self.assertEqual(result, drive_config.DEFAULT_CONFIG_YAML)

    @patch("drive_config.bootstrap_config")
    @patch("drive_config.get_drive_service")
    def test_read_config_decodes_bytes_response(self, mock_svc, mock_bootstrap):
        mock_svc.return_value.files.return_value.get_media.return_value.execute.return_value = VALID_YAML.encode(
            "utf-8"
        )
        result = drive_config.read_config()
        self.assertIsInstance(result, str)
        mock_bootstrap.assert_not_called()


class TestBootstrapConfig(unittest.TestCase):

    @patch("drive_config.write_config")
    @patch("drive_config.get_drive_service")
    def test_bootstrap_config_writes_default_and_renames(self, mock_svc, mock_write):
        mock_svc.return_value.files.return_value.get.return_value.execute.return_value = {
            "name": "config"
        }
        drive_config.bootstrap_config()
        mock_write.assert_called_once_with(drive_config.DEFAULT_CONFIG_YAML)
        mock_svc.return_value.files.return_value.update.assert_called_once_with(
            fileId=drive_config.CONFIG_FILE_ID,
            body={"name": "config.yaml"},
        )

    @patch("drive_config.write_config")
    @patch("drive_config.get_drive_service")
    def test_bootstrap_config_skips_rename_if_already_yaml(self, mock_svc, mock_write):
        mock_svc.return_value.files.return_value.get.return_value.execute.return_value = {
            "name": "config.yaml"
        }
        drive_config.bootstrap_config()
        mock_write.assert_called_once_with(drive_config.DEFAULT_CONFIG_YAML)
        # update should NOT have been called for rename
        mock_svc.return_value.files.return_value.update.assert_not_called()


class TestParseConfig(unittest.TestCase):

    def test_parse_config_all_defaults_on_empty_input(self):
        result = drive_config.parse_config("")
        self.assertEqual(len(result), 13)
        self.assertEqual(result["personal_calendar_id"], "duykbui1989@gmail.com")
        self.assertEqual(result["msi_calendar_id"], "duy.bui@motorolasolutions.com")
        self.assertEqual(result["daily_run_time"], "19:00")
        self.assertEqual(result["timezone"], "America/New_York")
        self.assertEqual(result["default_prep_minutes"], 30)
        self.assertEqual(result["baseline_event_id"], "l13abvd0p0vkphit24u6bkhuf8")
        self.assertEqual(result["baseline_event_title"], "Daily Standup Alarm")
        self.assertEqual(result["baseline_event_time"], "09:25")
        self.assertEqual(result["recurring_meetings"], [])
        self.assertEqual(result["meeting_type_prep"], {})
        self.assertEqual(result["locations"], {"Home": 0})  # Home:0 always injected
        self.assertEqual(result["client_overrides"], {})
        self.assertEqual(result["apple_exclude_calendars"], [])

    def test_parse_config_overrides_calendar_ids(self):
        result = drive_config.parse_config(VALID_YAML)
        self.assertEqual(result["personal_calendar_id"], "test@example.com")
        self.assertEqual(result["msi_calendar_id"], "work@example.com")
        self.assertEqual(result["timezone"], "America/Chicago")
        self.assertEqual(result["default_prep_minutes"], 20)

    def test_parse_config_parses_recurring_meeting(self):
        result = drive_config.parse_config(VALID_YAML)
        self.assertEqual(len(result["recurring_meetings"]), 1)
        meeting = result["recurring_meetings"][0]
        self.assertEqual(meeting["name"], "Morning Standup")
        self.assertEqual(meeting["prep_minutes"], 10)
        self.assertEqual(meeting["notes"], "Quick sync")
        self.assertEqual(meeting["days"], ["Mon", "Tue", "Wed"])

    def test_parse_config_parses_meeting_type_prep(self):
        result = drive_config.parse_config(VALID_YAML)
        self.assertEqual(result["meeting_type_prep"]["Daily standup"], 5)
        self.assertEqual(result["meeting_type_prep"]["In-person (local)"], "travel+10")

    def test_parse_config_parses_locations_and_overrides(self):
        result = drive_config.parse_config(VALID_YAML)
        self.assertEqual(result["locations"]["Office"], 30)
        self.assertEqual(result["client_overrides"]["Acme Corp"], 45)

    def test_parse_config_apple_exclude_calendars_present(self):
        yaml_str = """
calendars:
  personal_id: test@example.com
  apple_exclude_calendars:
    - "US Holidays"
    - "Birthdays"
"""
        result = drive_config.parse_config(yaml_str)
        self.assertEqual(result["apple_exclude_calendars"], ["US Holidays", "Birthdays"])

    def test_parse_config_apple_exclude_calendars_missing(self):
        result = drive_config.parse_config(VALID_YAML)
        self.assertEqual(result["apple_exclude_calendars"], [])

    def test_parse_config_apple_exclude_calendars_non_list_ignored(self):
        yaml_str = """
calendars:
  apple_exclude_calendars: "not a list"
"""
        result = drive_config.parse_config(yaml_str)
        self.assertEqual(result["apple_exclude_calendars"], [])

    def test_parse_config_apple_exclude_calendars_empty_list(self):
        yaml_str = """
calendars:
  apple_exclude_calendars: []
"""
        result = drive_config.parse_config(yaml_str)
        self.assertEqual(result["apple_exclude_calendars"], [])

    @patch.dict(os.environ, {"PHANTOM_CONFIG_FILE_ID": "custom-file-id"})
    def test_config_file_id_uses_env_var(self):
        import importlib
        import drive_config as dc_module

        importlib.reload(dc_module)
        self.assertEqual(dc_module.CONFIG_FILE_ID, "custom-file-id")


import drive_config  # noqa: E402

if __name__ == "__main__":
    unittest.main()
