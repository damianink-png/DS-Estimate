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
assert all(len(call.args) == len(helper.args.args) for call in guarded_calls), "Every group verification call must supply all required cached invariants"
print("STEP inventory budget and rigid group consistency declarations: PASS")

# A member can bypass repeated Boolean verification ONLY when OCCT confirms
# exact underlying TShape partnership with the independently verified group
# representative. Fingerprints must never be treated as equality proof.
source_text = source.read_text(encoding="utf-8")
assert "member.IsPartner(proven)" in source_text
assert "proven_partner_shapes = [originals[group_id]]" in source_text
assert source_text.count("proven_partner_shapes.append(member)") == 2
assert "member_partner_skips += 1" in source_text
assert "memberPartnerSkips" in source_text

# Slow member profiling must not alter the conservative validation contract.
assert "DS-CAD-SLOW-MEMBER" in text
assert "DS_CAD_SLOW_MEMBER_SECONDS" in text
assert "DS_CAD_SLOW_MEMBER_LIMIT" in text
assert "record_pair(time.perf_counter()-translation_started" in text
assert "record_pair(time.perf_counter()-rigid_started" in text
