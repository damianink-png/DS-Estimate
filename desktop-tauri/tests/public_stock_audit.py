"""Diagnostic-only audit of raw-stock detection on REAL assembly inventories.

Does not use CAD mass/grouping as ground truth and does not claim that a
recognized section is a correct procurement item. Unknown stays unknown.
"""
from collections import Counter
import csv
import math


STOCK_KINDS = frozenset({
    "plate-candidate", "flat-section", "square-bar", "rectangular-bar",
    "round-bar", "round-tube", "square-hollow", "rectangular-hollow",
    "angle", "channel", "tee", "i-section", "zee", "hat", "polygon-bar", "unknown"
})
REQUIRED_DIMENSIONS = {
    "plate-candidate": ("thicknessMm", "widthMm", "lengthMm"),
    "flat-section": ("widthMm", "heightMm", "lengthMm", "sectionAreaMm2"),
    "square-bar": ("widthMm", "heightMm", "lengthMm", "sectionAreaMm2"),
    "rectangular-bar": ("widthMm", "heightMm", "lengthMm", "sectionAreaMm2"),
    "round-bar": ("diameterMm", "lengthMm", "sectionAreaMm2"),
    "round-tube": ("diameterMm", "wallMm", "lengthMm", "sectionAreaMm2"),
    "square-hollow": ("widthMm", "heightMm", "wallMm", "lengthMm", "sectionAreaMm2"),
    "rectangular-hollow": ("widthMm", "heightMm", "wallMm", "lengthMm", "sectionAreaMm2"),
    "angle": ("lengthMm", "sectionAreaMm2"),
    "channel": ("lengthMm", "sectionAreaMm2"),
    "tee": ("lengthMm", "sectionAreaMm2"),
    "zee": ("lengthMm", "sectionAreaMm2"),
    "hat": ("lengthMm", "sectionAreaMm2"),
    "i-section": ("lengthMm", "sectionAreaMm2"),
    "polygon-bar": ("widthMm", "heightMm", "lengthMm", "sectionAreaMm2"),
}
DIMENSIONS = ("lengthMm", "widthMm", "heightMm", "diameterMm",
              "wallMm", "thicknessMm", "sectionAreaMm2")
CSV_COLUMNS = ("id", "verifiedShapeKey", "kind", "status", "confidence",
               *DIMENSIONS, "reason", "source", "limitations")


def _section_area_consistent(kind, hint):
    """Reject contradictory measured section areas, not catalogue guesses.

    Only analytically exact circle/rectangle stock sections are checked.
    Structural rolled profiles and plate candidates have no such simple
    area formula; do not pretend their bounding boxes prove anything.
    """
    if kind not in ("round-bar", "round-tube", "square-bar",
                    "rectangular-bar", "flat-section",
                    "square-hollow", "rectangular-hollow"):
        return True
    try:
        area = hint["sectionAreaMm2"]
        if kind == "round-bar":
            expected = math.pi * hint["diameterMm"] ** 2 / 4
        elif kind == "round-tube":
            d, wall = hint["diameterMm"], hint["wallMm"]
            expected = math.pi * (d * wall - wall * wall)
        else:
            w, h = hint["widthMm"], hint["heightMm"]
            expected = w * h
            if kind in ("square-hollow", "rectangular-hollow"):
                wall = hint["wallMm"]
                expected -= (w - 2 * wall) * (h - 2 * wall)
        return (math.isfinite(expected) and expected > 0
                and abs(area - expected) <= max(0.05, expected * 0.02))
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def stock_audit(inventory):
    solids = inventory.get("solids")
    if not isinstance(solids, list) or inventory.get("count") != len(solids):
        raise ValueError("Invalid STEP occurrence inventory")
    rows = []
    statuses = Counter()
    types = Counter()
    reasons = Counter()
    for idx, solid in enumerate(solids):
        raw = solid.get("stockHint") if isinstance(solid, dict) else None
        hint = raw if isinstance(raw, dict) else {}
        kind = hint.get("kind", "unknown")
        reason = str(hint.get("reason") or "")
        confidence = str(hint.get("confidence") or "")
        finite = all(
            type(hint.get(name)) in (int, float)
            and math.isfinite(hint[name]) and hint[name] > 0
            for name in DIMENSIONS if name in hint
        )
        required = REQUIRED_DIMENSIONS.get(kind, ())
        missing_required = any(name not in hint for name in required)
        bad_wall = (kind in ("round-tube", "square-hollow", "rectangular-hollow")
                    and type(hint.get("wallMm")) in (int, float)
                    and type(hint.get("diameterMm", hint.get("heightMm"))) in (int, float)
                    and hint["wallMm"] * 2 >= hint.get("diameterMm", hint.get("heightMm")))
        if raw is None:
            status = "MISSING_HINT"
            reason = "Compiled engine provided no stockHint for this STEP solid"
            kind = "unknown"
        elif (not isinstance(raw, dict) or not isinstance(kind, str)
              or kind not in STOCK_KINDS or not finite or missing_required
              or bad_wall or (kind not in ("square-hollow", "rectangular-hollow")
                       and not _section_area_consistent(kind, hint))):
            status = "INVALID_HINT"
            reason = reason or "Malformed stock evidence"
            kind = "unknown"
        elif (kind in ("square-hollow", "rectangular-hollow")
              and not _section_area_consistent(kind, hint)):
            # Sharp-corner rectangle arithmetic cannot validate radiused SHS/RHS.
            # Keep measured B-Rep area and the actual section type, but withhold
            # geometry certification until independent corner geometry is checked.
            status = "UNVERIFIED"
            reason = "Measured hollow-section area differs from sharp-corner formula; rounded corners require B-Rep verification"
        elif kind == "unknown":
            status = "UNKNOWN"
            reason = reason or "No classifier evidence"
        elif kind == "plate-candidate" or confidence == "candidate":
            status = "CANDIDATE"
        elif confidence == "cross-section-consistent":
            status = "GEOMETRY_ONLY"
        else:
            status = "UNVERIFIED"
            reason = reason or "No recognized confidence field"
        # A shape/section category alone NEVER validates material, stock
        # purchase length, weld prep or catalogue designation.
        row = {
            "id": solid.get("id", f"index-{idx}") if isinstance(solid, dict) else f"index-{idx}",
            "verifiedShapeKey": solid.get("verifiedShapeKey", "") if isinstance(solid, dict) else "",
            "kind": kind, "status": status, "confidence": confidence,
            "reason": reason, "source": str(hint.get("source", "")),
            "limitations": str(hint.get("limitations", ""))
        }
        for name in DIMENSIONS:
            row[name] = hint.get(name, "")
        rows.append(row)
        statuses[status] += 1
        types[kind] += 1
        if status in ("UNKNOWN", "INVALID_HINT", "UNVERIFIED", "MISSING_HINT"):
            reasons[reason] += 1
    count = len(rows)
    return {
        "purpose": "diagnostic-only (NOT accuracy proof)",
        "occurrences": count,
        "statusCounts": dict(sorted(statuses.items())),
        "kindCounts": dict(sorted(types.items())),
        "unresolvedOccurrences": count - statuses["GEOMETRY_ONLY"],
        "geometryEvidencePct": round(100*statuses["GEOMETRY_ONLY"]/count, 1) if count else 0,
        "unresolvedReasons": dict(reasons.most_common()),
        "limitations": [
            "A STEP assembly may contain fused solids and cannot recover unmodelled weld parts",
            "No automatic independent match to PDF/BOM part numbers",
            "Recognition is not a verified steel catalogue name or purchasing decision",
        ],
        "rows": rows,
    }


def write_stock_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in CSV_COLUMNS})
