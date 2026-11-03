"""Source-level guard for partial profiling on early failed group matches."""
from pathlib import Path
import ast
source=Path(__file__).resolve().parents[1]/"cad_backend"/"step_inventory.py"
tree=ast.parse(source.read_text(encoding="utf-8"))
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="inventory")
helper=next(n for n in ast.walk(fn) if isinstance(n,ast.FunctionDef) and n.name=="matches_every_group_member")
returns=[n for n in ast.walk(helper) if isinstance(n,ast.Return)]
assert len(returns)==4, f"Unexpected validation return paths: {len(returns)}"
for ret in returns:
    if isinstance(ret.value,ast.Constant) and ret.value.value is False:
        block=next((node for node in ast.walk(helper) if isinstance(node,(ast.If,ast.For)) and ret in node.body),None)
        assert block is not None, "Cannot locate rejection path"
        before=block.body[:block.body.index(ret)]
        assert any(isinstance(n,ast.AugAssign) and isinstance(n.target,ast.Name) and n.target.id=="member_validation_seconds" for n in before), "Rejection path loses elapsed time"
assert "DS-CAD-PROGRESS" in source.read_text(encoding="utf-8")
print("Partial progress and rejection timing guards: PASS")
