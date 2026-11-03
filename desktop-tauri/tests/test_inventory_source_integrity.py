"""Prevent escaped newline comments from disabling runtime budget declarations."""
from pathlib import Path
import ast

source = Path(__file__).resolve().parents[1] / "cad_backend" / "step_inventory.py"
text = source.read_text(encoding="utf-8")
tree = ast.parse(text, filename=str(source))
fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "inventory")
assignments = {target.id for node in ast.walk(fn) if isinstance(node, (ast.Assign, ast.AnnAssign)) for target in (node.targets if isinstance(node, ast.Assign) else [node.target]) if isinstance(target, ast.Name)}
for name in ("max_translation_checks", "max_translation_seconds", "max_rigid_checks", "max_rigid_seconds"):
    assert name in assignments, f"Missing runtime budget assignment: {name}"
assert r"\\n    max_translation_seconds" not in text, "Literal escaped newline commented out assignment"
assert "for member, member_center, member_volume in group_members.get(i, ()):" in text, "Rigid matches must be checked against existing group members"
print("STEP inventory budget and rigid group consistency declarations: PASS")
