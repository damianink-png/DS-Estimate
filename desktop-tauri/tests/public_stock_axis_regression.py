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
        surfaces = hint.get("finishedBrepSurfaceEvidence") or {}
        assert surfaces.get("source") == "original STEP B-Rep face adaptors", (
            f"Earthpress {number}: no original-face surface evidence")
        assert surfaces.get("cylinderFaceCount", 0) >= 2, (
            f"Earthpress {number}: missing measured inner/outer cylinders")
        radii = [face["radiusMm"] for face in surfaces["cylinders"]]
        assert any(math.isclose(r, 20, abs_tol=.02) for r in radii)
        assert any(math.isclose(r, 17, abs_tol=.02) for r in radii)
        assert all(len(face["axis"]) == 3 for face in surfaces["cylinders"])
        print("PUBLIC_ORIGINAL_BREP_CYLINDER_PASS", json.dumps({
            "solid": number, "radiiMm": radii, "axes": [f["axis"] for f in surfaces["cylinders"]]}))
        print("PUBLIC_STOCK_AXIS_PASS", json.dumps({
            "solid": number, "finishVolumeMm3": round(s["volumeMm3"], 2),
            "coreSection": "round-tube", "diameterMm": core["diameterMm"],
            "wallMm": core["wallMm"],
            "blankClassification": hint["kind"],
            "cutTimeCertified": False
        }))

    # Six genuine rounded-corner SHS members are currently rejected by the
    # audit's sharp-corner area formula. Record exact original STEP evidence;
    # do not weaken the global 2% geometric tolerance to mask this.
    shs = []
    for number in range(1, 7):
        solid = solids[number - 1]
        hint = solid.get("stockHint") or {}
        shs.append({
            "solid": number,
            "status": hint.get("kind"),
            "section": hint.get("section") or hint.get("coreSectionCandidate"),
            "reason": hint.get("reason"),
        })
    print("PUBLIC_ROUNDED_SHS_EVIDENCE", json.dumps(shs, ensure_ascii=False))
    assert len(shs) == 6
    # Independent strict numerical evidence from the ORIGINAL STEP.
    # Never increase the generic 2% tolerance to hide rounded corners.
    for number in range(1, 7):
        hint = solids[number - 1].get("stockHint") or {}
        assert hint.get("kind") == "square-hollow", (
            f"Earthpress {number}: SHS detection regressed")
        assert hint.get("confidence") == "cross-section-consistent"
        width, height, wall = hint["widthMm"], hint["heightMm"], hint["wallMm"]
        measured = hint["sectionAreaMm2"]
        assert math.isclose(width, height, abs_tol=0.02)
        assert math.isclose(wall, 3, abs_tol=0.02)
        assert any(math.isclose(width, w, abs_tol=0.02) for w in (50, 60))
        sharp = width * height - (width - 2 * wall) * (height - 2 * wall)
        difference = (sharp - measured) / sharp
        assert 0.03 < difference < 0.05, (
            f"Earthpress {number}: B-Rep rounded area changed: "
            f"measured={measured}, sharp={sharp}")
        assert not hint.get("rawStockCandidate"), (
            f"Earthpress {number}: measured section cannot certify procurement")
        print("PUBLIC_ROUNDED_SHS_AREA_PASS", json.dumps({
            "solid": number, "widthMm": width, "wallMm": wall,
            "measuredAreaMm2": measured, "sharpCornerAreaMm2": sharp,
            "relativeDifferencePct": round(difference * 100, 3),
            "procurementCertified": False
        }))

    # Verify the AUDIT outcome on the same compiled original STEP inventory,
    # not merely the raw engine hints. Rounded corners must not be treated as
    # malformed, nor may a geometry-only result certify purchasable stock.
    from public_stock_audit import stock_audit
    audited = stock_audit(inventory)
    # Earthpress 12/13: real ORIGINAL STEP proves a thin plate along its
    # measured local frame. Five flat sections plus end removal must not
    # demote it to an invalid unquoted bar. No saw/milling assumption.
    for number in (12,13):
        hint=solids[number-1].get('stockHint') or {}
        row=audited['rows'][number-1]
        assert hint.get('kind')=='plate-candidate', (
            f'Earthpress {number}: elongated finished plate lost after face evidence')
        assert hint.get('confidence')=='candidate'
        assert row['status']=='CANDIDATE', (
            f'Earthpress {number}: malformed plate hint after local frame recovery: {row}')
        assert math.isclose(hint['thicknessMm'],10,abs_tol=.02)
        assert math.isclose(hint['widthMm'],60,abs_tol=.02)
        assert math.isclose(hint['lengthMm'],565.0857866,abs_tol=.03)
        assert (hint.get('rawStockCandidate') or {}).get('kind')=='flat-section'
        assert hint['rawStockCandidate']['removedVolumeMm3']>0
        assert 'cutTimeH' not in hint
    print('PUBLIC_END_TRIMMED_PLATE_PASS: Earthpress 12/13 remain plate candidates in measured local frame; no machining quote')

    for number in range(1, 7):
        row = audited["rows"][number - 1]
        assert row["status"] == "UNVERIFIED", (
            f"Earthpress {number}: rounded SHS audit status {row['status']}")
        assert row["kind"] == "square-hollow"
        assert "rounded corners" in row["reason"]
        assert math.isclose(row["sectionAreaMm2"],
                            solids[number - 1]["stockHint"]["sectionAreaMm2"],
                            abs_tol=1e-6)
    assert audited["statusCounts"].get("GEOMETRY_ONLY", 0) <= 84, (
        "Unverified rounded sections must not increase certified geometry")
    print("PUBLIC_ROUNDED_SHS_AUDIT_PASS: six original SHS remain UNVERIFIED, not INVALID or certified")

    # Independent occurrence-to-occurrence consistency on original rounded SHS:
    # the same physical section measured at different assembly placements must
    # retain its area. This is not a sharp-corner formula or procurement proof.
    shs_areas = {}
    for number in range(1, 7):
        hint = solids[number - 1]["stockHint"]
        width = round(hint["widthMm"])
        shs_areas.setdefault(width, []).append(hint["sectionAreaMm2"])
    assert set(shs_areas) == {50, 60}
    assert len(shs_areas[50]) == 4 and len(shs_areas[60]) == 2
    for width, areas in shs_areas.items():
        assert max(areas) - min(areas) < 1e-5, (
            f"Earthpress SHS {width}: identical section areas disagree across placements")
    print("PUBLIC_ROUNDED_SHS_REPEATABILITY_PASS", json.dumps({
        "sections": {str(k): {"occurrences": len(v), "measuredAreaMm2": round(v[0], 6)}
                     for k, v in sorted(shs_areas.items())},
        "toleranceRelaxed": False, "procurementCertified": False
    }))

    # Repeatable geometric identity is not manufacturing evidence. Check the
    # original compiled STEP occurrence keys for the unresolved fastener-like
    # solids, without inferring purchase stock, saw time, or milling time.
    fastener_occurrences = (88, 89, 90, 91, 92, 93, 99, 106, 109, 122, 125, 131, 135, 141)
    unresolved = []
    for number in fastener_occurrences:
        solid = solids[number - 1]
        hint = solid.get("stockHint") or {}
        assert math.isfinite(solid["volumeMm3"]) and solid["volumeMm3"] > 0, (
            f"Earthpress {number}: invalid B-Rep volume")
        assert hint.get("kind") == "unknown", (
            f"Earthpress {number}: unexpected stock classification requires review")
        assert not hint.get("rawStockCandidate"), (
            f"Earthpress {number}: unproven purchasable blank")
        # The independent diagnostic must preserve unresolved status for each
        # original STEP occurrence, not silently promote rotational features
        # to a stock type merely because a cylindrical surface was detected.
        audit_row = audited["rows"][number - 1]
        assert audit_row["status"] == "UNKNOWN", (
            f"Earthpress {number}: fastener geometry incorrectly certified: {audit_row}")
        assert audit_row["kind"] == "unknown", (
            f"Earthpress {number}: unsupported procurement geometry")
        assert audit_row["verifiedShapeKey"] == solid.get("verifiedShapeKey", ""), (
            f"Earthpress {number}: occurrence geometry key lost in audit")
        unresolved.append({"solid": number, "volumeMm3": round(solid["volumeMm3"], 4),
                           "shapeKey": solid.get("verifiedShapeKey", ""),
                           "stock": "unknown"})
    print("PUBLIC_FASTENER_GEOMETRY_GUARD_PASS", json.dumps({
        "sampleOccurrences": len(unresolved), "solids": unresolved,
        "cuttingTimeInferred": False, "manufacturingProcessInferred": False
    }))

    # Original B-Rep face measurements for fastener-like occurrences.  This is
    # a diagnostic census, not a fastener catalogue or an operation classifier.
    # Keep identity and measurements separate: equal volume is not proof of
    # identical geometry, and a cylinder is not proof of purchased hardware.
    face_samples = []
    for item in unresolved:
        number = item["solid"]
        hint = solids[number - 1].get("stockHint") or {}
        evidence = hint.get("finishedBrepSurfaceEvidence") or {}
        cylinders = evidence.get("cylinders") or []
        cones = evidence.get("cones") or []
        if evidence:
            assert evidence.get("source") == "original STEP B-Rep face adaptors", (
                f"Earthpress {number}: surface data must originate in STEP faces")
            assert evidence.get("cylinderFaceCount", 0) >= len(cylinders)
            assert evidence.get("coneFaceCount", 0) >= len(cones)
            for face in cylinders:
                assert math.isfinite(face["radiusMm"]) and face["radiusMm"] > 0
                assert len(face["axis"]) == 3
                assert math.isclose(sum(v * v for v in face["axis"]), 1, abs_tol=1e-5)
            for face in cones:
                assert math.isfinite(face["referenceRadiusMm"])
                assert math.isfinite(face["semiAngleRad"])
                assert len(face["axis"]) == 3
        face_samples.append({
            "solid": number, "shapeKey": item["shapeKey"],
            "evidencePresent": bool(evidence),
            "cylinderFaceCount": evidence.get("cylinderFaceCount", 0),
            "coneFaceCount": evidence.get("coneFaceCount", 0),
            "cylinders": cylinders, "cones": cones,
            "blankCertified": False, "manufacturingCertified": False,
        })
    print("PUBLIC_FASTENER_ORIGINAL_BREP_SURFACE_CENSUS", json.dumps({
        "sampleOccurrences": len(face_samples),
        "distinctGeometryKeys": len({item["shapeKey"] for item in face_samples}),
        "withMeasuredSurfaces": sum(item["evidencePresent"] for item in face_samples),
        "samples": face_samples,
    }))

    # Three equal-volume fastener-like geometries repeat in two placements.
    # Equal B-Rep volume alone MUST NOT merge different shape identities.
    # This checks original compiled STEP occurrence keys, not a guessed BOM.
    repeat_keys = [solids[n - 1].get("verifiedShapeKey") for n in (88, 89, 90, 91, 92, 93)]
    repeat_volumes = [solids[n - 1]["volumeMm3"] for n in (88, 89, 90, 91, 92, 93)]
    assert all(repeat_keys), "Earthpress 88-93: missing verified geometry identity"
    assert repeat_keys[:3] == repeat_keys[3:], (
        "Earthpress 88-93: repeated original B-Rep identities changed")
    assert len(set(repeat_keys[:3])) == 3, (
        "Earthpress 88-90: distinct equal-volume geometries were merged")
    assert max(repeat_volumes) - min(repeat_volumes) < 1e-3, (
        "Earthpress 88-93: original B-Rep volumes unexpectedly changed")
    print("PUBLIC_EQUAL_VOLUME_DISTINCT_GEOMETRY_PASS", json.dumps({
        "occurrences": 6, "distinctGeometryKeys": 3,
        "sameVolumeDoesNotImplySameShape": True,
        "stockAndManufacturingRemainUnknown": True
    }))

    # Whole-assembly unresolved geometry census from the compiled ORIGINAL STEP.
    # This protects against silently dropping unresolved occurrences while
    # keeping shape identity separate from volume and from manufacturing.
    unknown_rows = [row for row in audited["rows"] if row["status"] == "UNKNOWN"]
    assert len(unknown_rows) == 75, (
        f"Earthpress: expected 75 unresolved original solids, got {len(unknown_rows)}")
    unknown_keys = [row["verifiedShapeKey"] for row in unknown_rows]
    assert all(unknown_keys), "Earthpress: unresolved geometry identity missing"
    assert len(set(unknown_keys)) == 37, (
        "Earthpress: original 75 unresolved occurrences no longer form 37 distinct shapes")
    # Inspect actual planar face normals of unresolved finished B-Rep solids.
    # Bevel faces are geometric evidence, NOT proof of plate stock or milling.
    planar_faces = 0
    planar_solids = 0
    for solid, row in zip(solids, audited["rows"]):
        if row["status"] != "UNKNOWN":
            continue
        evidence = (solid.get("stockHint") or {}).get("finishedBrepSurfaceEvidence") or {}
        planes = evidence.get("planes") or []
        assert evidence.get("planeFaceCount", 0) >= len(planes)
        for plane in planes:
            normal = plane["normal"]
            assert len(normal) == 3 and all(math.isfinite(v) for v in normal)
            assert math.isclose(sum(v*v for v in normal), 1.0, abs_tol=2e-6)
            assert math.isfinite(plane["areaMm2"]) and plane["areaMm2"] > 0, (
                "Original B-Rep planar face must have a positive measured area")
            assert math.isfinite(plane["signedOffsetMm"]), (
                "Original B-Rep planar face must have a finite signed offset")
        planar_faces += evidence.get("planeFaceCount", 0)
        planar_solids += bool(planes)
    assert planar_solids > 0, "Original STEP unresolved solids have no planar B-Rep evidence"
    print("PUBLIC_ORIGINAL_BREP_PLANE_CENSUS_PASS", json.dumps({
        "unresolvedSolidsWithPlaneEvidence": planar_solids,
        "measuredPlaneFaces": planar_faces,
        "stockCertified": False, "bevelMachiningInferred": False
    }))

    print("PUBLIC_UNKNOWN_GEOMETRY_CENSUS_PASS", json.dumps({
        "unresolvedOccurrences": len(unknown_rows),
        "distinctVerifiedShapes": len(set(unknown_keys)),
        "manufacturingInferred": False, "cutTimeInferred": False
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
