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
    # Real original STEP: correct axis does not imply a constant stock profile.
    # Portal Frame 2-9 have 100x200 ends but 100x10 central sections.
    portal = json.loads((Path(root) / "portal-frame" / "ds_estimate_inventory.json").read_text(encoding="utf-8"))
    assert len(portal["solids"]) == 15
    for number in range(2, 10):
        solid = portal["solids"][number - 1]
        hint = solid.get("stockHint") or {}
        core = hint.get("coreSectionCandidate") or {}
        assert hint.get("kind") == "unknown", f"Portal Frame {number}: false finished stock"
        assert not hint.get("rawStockCandidate"), f"Portal Frame {number}: false purchasable flat bar"
        assert core.get("kind") == "flat-section", f"Portal Frame {number}: missing measured central section"
        assert core.get("confidence") == "geometric-core-only"
        assert math.isclose(core["widthMm"], 100, abs_tol=.02)
        assert math.isclose(core["heightMm"], 10, abs_tol=.02)
        assert math.isclose(core["lengthMm"], 4000, abs_tol=.02)
        assert math.isclose(solid["volumeMm3"], 11600000, rel_tol=1e-5)
        assert solid["volumeMm3"] > 2.8 * core["sectionPrismVolumeMm3"]
    print("PUBLIC_VARIABLE_SECTION_PASS: Portal Frame 2-9 retain unknown stock despite correct central section")

    # Earthpress 132 has a true round core but conical end material.
    s = solids[131]
    hint = s.get("stockHint") or {}
    core = hint.get("coreSectionCandidate") or {}
    assert hint.get("kind") == "unknown", "Earthpress 132: conical ends must not be auto-quoted"
    assert not hint.get("rawStockCandidate")
    assert core.get("kind") == "round-bar"
    assert core.get("confidence") == "geometric-core-only"
    assert math.isclose(core["diameterMm"], 10, abs_tol=.02)
    assert core.get("axisEvidence") == "B-Rep cylinder/edge axis"
    assert core["finishedVolumeMm3"] > core["sectionPrismVolumeMm3"] * 1.05
    print("PUBLIC_CONICAL_END_PASS: Earthpress 132 remains unknown despite measured round core")

    print("PUBLIC_STOCK_AXIS_PASS: both rotated tube cores recovered without false stock or cut time")


if __name__ == "__main__":
    check(sys.argv[1] if len(sys.argv) > 1 else "public_fabrication_output")
