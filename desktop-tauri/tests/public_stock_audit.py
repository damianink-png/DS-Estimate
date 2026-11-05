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
    "angle", "channel", "tee", "i-section", "unknown"
})
HOLLOW = {"round-tube", "square-hollow", "rectangular-hollow"}
DIMENSIONS = ("lengthMm", "widthMm", "heightMm", "diameterMm",
              "wallMm", "thicknessMm", "sectionAreaMm2")
CSV_COLUMNS = ("id", "verifiedShapeKey", "kind", "status", "confidence",
               *DIMENSIONS, "reason", "source", "limitations")


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
        if kind not in STOCK_KINDS or not finite:
            status = "INVALID_HINT"
            reason = reason or "Malformed stock evidence"
            kind = "unknown"
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
        if status in ("UNKNOWN", "INVALID_HINT", "UNVERIFIED"):
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
