"""Compiled-CAD evidence from ORIGINAL public STEP: axis, not a projection guess.

Do not confuse a measured cylindrical core with a purchasable raw stock tube.
The complete solid has extra end geometry; neither saw time nor raw mass may
be inferred solely from the 40/34 mm coaxial section.
"""
import json
import math
import sys
from pathlib import Path


def check(root):
    source = Path(root) / "earthpress" / "ds_estimate_inventory.json"
    inventory = json.loads(source.read_text(encoding="utf-8"))
    solids = inventory["solids"]
    assert len(solids) == 251, "Earthpress STEP solids lost"
    for number in (10, 11):
        s = solids[number - 1]
        hint = s.get("stockHint") or {}
        core = hint.get("coreSectionCandidate") or {}
        assert hint.get("kind") == "unknown", (
            f"Earthpress {number}: finished part must not become ready-made raw stock")
        assert not hint.get("rawStockCandidate"), (
            f"Earthpress {number}: detected extra volume is not material removal")
        assert core.get("kind") == "round-tube", (
            f"Earthpress {number}: oblique 40/34 tube axis not recovered: {hint}")
        assert core.get("confidence") == "geometric-core-only", (
            f"Earthpress {number}: unsupported procurement confidence")
        assert math.isclose(core["diameterMm"], 40, abs_tol=.02)
        assert math.isclose(core["wallMm"], 3, abs_tol=.02)
        assert core.get("supportingSections") == 5
        assert core["finishedVolumeMm3"] > core["sectionPrismVolumeMm3"] * 1.02
        assert core.get("axisEvidence") == "B-Rep cylinder/edge axis"
        print("PUBLIC_STOCK_AXIS_PASS", json.dumps({
            "solid": number, "finishVolumeMm3": round(s["volumeMm3"], 2),
            "coreSection": "round-tube", "diameterMm": core["diameterMm"],
            "wallMm": core["wallMm"],
            "blankClassification": hint["kind"],
            "cutTimeCertified": False
        }))
    print("PUBLIC_STOCK_AXIS_PASS: both rotated tube cores recovered without false stock or cut time")


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "public_fabrication_output")
