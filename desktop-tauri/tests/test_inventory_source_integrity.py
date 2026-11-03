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
# Validate the AST rather than an exact call spelling: the helper accepts
# additional precomputed invariants as the engine is optimized.
helper = next((node for node in ast.walk(fn) if isinstance(node, ast.FunctionDef)
               and node.name == "matches_every_group_member"), None)
assert helper is not None, "Missing all-member geometry verification helper"
guarded_calls = [
    node for node in ast.walk(fn)
    if isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name)
    and node.func.id == "matches_every_group_member"
]
assert len(guarded_calls) == 2, "Both translation and rigid paths must verify all group members"
assert all(len(call.args) >= 4 for call in guarded_calls), "Group verification requires group, solid, center and volume"
print("STEP inventory budget and rigid group consistency declarations: PASS")
