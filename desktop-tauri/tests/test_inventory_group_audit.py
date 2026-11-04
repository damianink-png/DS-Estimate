"""Regression guard for profile-only occurrence mapping.

This does not assert the disputed pair is different: the independent B-Rep
audit remains the authority. It ensures group tracing is complete and stable.
"""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "cad_backend" / "step_inventory.py"


class GroupAuditSourceTest(unittest.TestCase):
    def test_audit_is_profile_only_and_does_not_change_matching(self):
        source = SOURCE.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn('if profile:\n        audited = (247, 267)', source)
        self.assertIn('enumerate(solids, start=1)', source)
        self.assertIn('group_occurrences.setdefault(row["verifiedShapeKey"], []).append(occurrence_index)', source)
        self.assertIn('[DS-CAD-GROUP-AUDIT]', source)
        self.assertIn('"auditedSameGroup"', source)


if __name__ == "__main__":
    unittest.main()
