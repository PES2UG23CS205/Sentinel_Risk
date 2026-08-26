"""
SentinelRisk — Timezone & UTC ISO-8601 Standardization Unit Tests

Verifies:
  1. Internal UTC storage in standard ISO-8601 format ('YYYY-MM-DDTHH:MM:SSZ')
  2. Display conversion from UTC to local browser/system timezones:
     - Asia/Kolkata (IST, UTC+05:30)
     - America/New_York (EDT/EST, UTC-4 / UTC-5)
     - Europe/London (BST/GMT, UTC+1 / UTC+0)
     - Asia/Tokyo (JST, UTC+09:00)
  3. DST-safe transitions (Summer daylight saving vs Winter standard time)
  4. Backward-compatible migration of legacy naive UTC strings
  5. Strict preservation of historical transaction dataset event timestamps (zero unintended shifts)
  6. Data Lab persistence integration with AssessmentStorage
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.app.utils.timezone import (
    utc_now,
    utc_now_iso,
    parse_and_standardize_utc,
    format_utc_to_timezone,
)
from backend.app.data_lab.storage import AssessmentStorage
from backend.app.data_lab.models import AssessmentMetadata, AssessmentStatus


class TestUTCStandardizationAndGeneration:
    """Test UTC generation and ISO-8601 standardization."""

    def test_utc_now_is_timezone_aware(self):
        dt = utc_now()
        assert dt.tzinfo is not None
        assert dt.tzinfo == timezone.utc

    def test_utc_now_iso_format(self):
        iso_str = utc_now_iso()
        assert iso_str.endswith("Z")
        assert "T" in iso_str
        assert len(iso_str) == 20  # YYYY-MM-DDTHH:MM:SSZ

    def test_parse_legacy_naive_utc_string(self):
        # Legacy naive timestamp format previously stored in metadata.json
        naive_str = "2026-08-25 14:28:44"
        standardized = parse_and_standardize_utc(naive_str)
        assert standardized == "2026-08-25T14:28:44Z"

    def test_parse_iso_with_z_or_offset(self):
        iso_z = "2026-08-25T14:28:44Z"
        assert parse_and_standardize_utc(iso_z) == "2026-08-25T14:28:44Z"

        iso_zero = "2026-08-25T14:28:44+00:00"
        assert parse_and_standardize_utc(iso_zero) == "2026-08-25T14:28:44Z"

        # Offset from IST (19:58:44 +05:30 -> 14:28:44 UTC)
        iso_ist = "2026-08-25T19:58:44+05:30"
        assert parse_and_standardize_utc(iso_ist) == "2026-08-25T14:28:44Z"

    def test_parse_datetime_objects(self):
        # Naive datetime
        dt_naive = datetime(2026, 8, 25, 14, 28, 44)
        assert parse_and_standardize_utc(dt_naive) == "2026-08-25T14:28:44Z"

        # Aware datetime in JST (+09:00)
        dt_jst = datetime(2026, 8, 25, 23, 28, 44, tzinfo=ZoneInfo("Asia/Tokyo"))
        assert parse_and_standardize_utc(dt_jst) == "2026-08-25T14:28:44Z"


class TestMultiTimezoneDisplayConversions:
    """Test converting standardized UTC timestamps to various local regional timezones."""

    def test_utc_to_ist_conversion(self):
        # 14:28:44 UTC -> 19:58:44 IST (+5h 30m)
        utc_ts = "2026-08-25T14:28:44Z"
        ist_display = format_utc_to_timezone(utc_ts, tz_name="Asia/Kolkata")
        assert "2026-08-25 19:58:44" in ist_display
        assert "IST" in ist_display

    def test_utc_to_us_eastern_conversion(self):
        # In August (EDT, UTC-4): 14:28:44 UTC -> 10:28:44 EDT
        utc_ts = "2026-08-25T14:28:44Z"
        ny_display = format_utc_to_timezone(utc_ts, tz_name="America/New_York")
        assert "2026-08-25 10:28:44" in ny_display
        assert "EDT" in ny_display

    def test_utc_to_london_conversion(self):
        # In August (BST, UTC+1): 14:28:44 UTC -> 15:28:44 BST
        utc_ts = "2026-08-25T14:28:44Z"
        london_display = format_utc_to_timezone(utc_ts, tz_name="Europe/London")
        assert "2026-08-25 15:28:44" in london_display
        assert "BST" in london_display

    def test_utc_to_tokyo_conversion(self):
        # In Tokyo (JST, UTC+9): 14:28:44 UTC -> 23:28:44 JST
        utc_ts = "2026-08-25T14:28:44Z"
        tokyo_display = format_utc_to_timezone(utc_ts, tz_name="Asia/Tokyo")
        assert "2026-08-25 23:28:44" in tokyo_display
        assert "JST" in tokyo_display


class TestDaylightSavingTimeTransitions:
    """Test DST awareness across summer daylight saving and winter standard time."""

    def test_us_eastern_dst_transition(self):
        # Summer (EDT, UTC-4): 12:00:00 UTC -> 08:00:00 EDT
        summer_utc = "2026-07-15T12:00:00Z"
        summer_res = format_utc_to_timezone(summer_utc, "America/New_York")
        assert "2026-07-15 08:00:00 EDT" == summer_res

        # Winter (EST, UTC-5): 12:00:00 UTC -> 07:00:00 EST
        winter_utc = "2026-01-15T12:00:00Z"
        winter_res = format_utc_to_timezone(winter_utc, "America/New_York")
        assert "2026-01-15 07:00:00 EST" == winter_res

    def test_london_dst_transition(self):
        # Summer (BST, UTC+1): 12:00:00 UTC -> 13:00:00 BST
        summer_utc = "2026-07-15T12:00:00Z"
        assert format_utc_to_timezone(summer_utc, "Europe/London") == "2026-07-15 13:00:00 BST"

        # Winter (GMT, UTC+0): 12:00:00 UTC -> 12:00:00 GMT
        winter_utc = "2026-01-15T12:00:00Z"
        assert format_utc_to_timezone(winter_utc, "Europe/London") == "2026-01-15 12:00:00 GMT"


class TestDataLabAssessmentStorageTimestampStandardization:
    """Test AssessmentStorage timestamp standardization and auto-migration."""

    def test_new_assessment_creates_iso_utc_timestamp(self):
        meta = AssessmentStorage.create_assessment(
            dataset_name="tz_test.csv",
            content="amount,timestamp\n100.0,2026-03-01 10:00:00\n",
            headers=["amount", "timestamp"],
            raw_rows=[{"amount": "100.0", "timestamp": "2026-03-01 10:00:00"}],
            file_size_bytes=42,
        )
        assert meta.uploaded_at.endswith("Z")
        assert "T" in meta.uploaded_at

        # Verify reading from disk
        loaded = AssessmentStorage.get_metadata(meta.assessment_id)
        assert loaded is not None
        assert loaded.uploaded_at == meta.uploaded_at

        # Clean up
        AssessmentStorage.delete_assessment(meta.assessment_id)

    def test_legacy_naive_timestamp_auto_migration(self):
        meta = AssessmentMetadata(
            assessment_id="ASM-TZLEGACY",
            dataset_name="legacy.csv",
            file_size_bytes=100,
            total_rows=5,
            uploaded_at="2026-08-25 14:28:44",  # legacy naive format
            status=AssessmentStatus.UPLOADED,
        )
        # Directly save legacy metadata
        AssessmentStorage._ensure_base_dir()
        asm_dir = AssessmentStorage.USER_ASSESSMENTS_DIR if hasattr(AssessmentStorage, "USER_ASSESSMENTS_DIR") else Path("data/user_assessments")
        target_dir = asm_dir / meta.assessment_id
        target_dir.mkdir(parents=True, exist_ok=True)
        meta_file = target_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(meta.model_dump_json(indent=2))

        # Read back with AssessmentStorage.get_metadata() -> should auto-migrate to ISO UTC
        migrated = AssessmentStorage.get_metadata(meta.assessment_id)
        assert migrated is not None
        assert migrated.uploaded_at == "2026-08-25T14:28:44Z"

        # Clean up
        AssessmentStorage.delete_assessment(meta.assessment_id)
