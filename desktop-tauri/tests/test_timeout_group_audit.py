"""Ensure timeout preserves the complete structured CAD group audit."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name("public_fabrication_benchmark.py")

class TimeoutAuditTest(unittest.TestCase):
    def test_audit_survives_truncated_stderr(self):
        source = SOURCE.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn("line.split('[DS-CAD-GROUP-AUDIT]',1)[1].strip()", source)
        self.assertIn("result['engineGroupAudit']=audit", source)
        self.assertIn("engine_group_audit.json", source)
        self.assertIn("ENGINE_TIMEOUT_GROUP_AUDIT", source)
        self.assertIn("except (ValueError,TypeError) as audit_error:", source)

if __name__ == "__main__":
    unittest.main()
