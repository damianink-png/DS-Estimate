"""AST regression: memory profiling remains optional and cannot change geometry grouping."""
import ast
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"cad_backend"/"step_inventory.py"
source=p.read_text(encoding="utf-8")
tree=ast.parse(source)
inventory=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=="inventory")
assert any(isinstance(x,ast.FunctionDef) and x.name=="working_set_mb" for x in ast.walk(inventory))
assert source.count("'workingSetMB': working_set_mb()") == 1
assert '"workingSetMB": working_set_mb()' in source
assert "if os.name != 'nt':" in source
print("Memory profiler guards: PASS")
