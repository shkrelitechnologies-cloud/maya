import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from publishing.permission_gate import load_verified_permissions


FIELDS = [
    "site_name", "domain", "submission_url", "rules_url", "language",
    "automation_allowed", "permitted_method", "daily_limit", "reviewed_on",
    "evidence_url", "adapter_module", "adapter_class", "notes",
]


class PermissionGateTests(unittest.TestCase):
    def write_registry(self, row=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "sites.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            if row:
                writer.writerow(row)
        return path

    def valid_row(self):
        return {
            "site_name": "Example",
            "domain": "community.example",
            "submission_url": "https://community.example/submit",
            "rules_url": "https://community.example/rules",
            "language": "en",
            "automation_allowed": "yes",
            "permitted_method": "official documented API",
            "daily_limit": "2",
            "reviewed_on": "2026-11-19",
            "evidence_url": "https://community.example/automation-policy",
            "adapter_module": "publishing.adapters.community",
            "adapter_class": "CommunityAdapter",
            "notes": "Fixture only; not a real approved destination",
        }

    def test_empty_registry_has_no_eligible_sites(self):
        eligible, skipped = load_verified_permissions(
            self.write_registry(), today=date(2026, 11, 19)
        )
        self.assertEqual(eligible, [])
        self.assertEqual(skipped, [])

    def test_complete_recent_permission_is_eligible(self):
        eligible, skipped = load_verified_permissions(
            self.write_registry(self.valid_row()), today=date(2026, 11, 19)
        )
        self.assertEqual(len(eligible), 1)
        self.assertEqual(skipped, [])
        self.assertEqual(eligible[0].domain, "community.example")

    def test_permission_cell_alone_is_not_enough(self):
        row = self.valid_row()
        row["evidence_url"] = ""
        eligible, skipped = load_verified_permissions(
            self.write_registry(row), today=date(2026, 11, 19)
        )
        self.assertEqual(eligible, [])
        self.assertTrue(skipped)

    def test_stale_review_is_rejected(self):
        row = self.valid_row()
        row["reviewed_on"] = "2026-09-01"
        eligible, skipped = load_verified_permissions(
            self.write_registry(row), today=date(2026, 11, 19)
        )
        self.assertEqual(eligible, [])
        self.assertTrue(skipped)

    def test_domain_mismatch_is_rejected(self):
        row = self.valid_row()
        row["domain"] = "other.example"
        eligible, skipped = load_verified_permissions(
            self.write_registry(row), today=date(2026, 11, 19)
        )
        self.assertEqual(eligible, [])
        self.assertTrue(skipped)


if __name__ == "__main__":
    unittest.main()
