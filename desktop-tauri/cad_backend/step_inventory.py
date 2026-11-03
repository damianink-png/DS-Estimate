"""DS Estimate 2.0 STEP inventory using pythonocc-core (OCCT).

Requires pythonocc-core in a separate Python environment. This is an opt-in
CAD backend, not yet packaged into the Tauri installer.

Reads STEP once and computes per-solid B-Rep volume, area, and bounds.
Conservative duplicate detection: only the same underlying OCCT TShape is
marked verified; equal volume/bounds alone NEVER imply identical geometry.
Arbitrarily rotated but independently imported copies require a future
rigid B-Rep equivalence verifier from DS Compare.
"""
import argparse
import json
import math
import os
import sys
import time
import warnings
try:
    from .shape_index import ShapeCandidateIndex
except ImportError:
    from shape_index import ShapeCandidateIndex
try:
    from .rigid_match import (equivalent_rigid, equivalent_translation,
                              translation_signature, translation_signatures_match,
                              has_unique_inertia_axes, cached_face_area_signature)
except ImportError:
    from rigid_match import (equivalent_rigid, equivalent_translation,
                             translation_signature, translation_signatures_match,
                             has_unique_inertia_axes, cached_face_area_signature)
from pathlib import Path


def planar_plate_cutting_hint(solid, dimensions):
    """Conservative plate cut-loop measurements, not a raw-stock classifier.

    Looks for two similarly sized primary planar faces and takes outer+inner
    wire lengths from one primary face. Unsuitable B-Reps return None rather
    than fabricating a cutting contour. For machined/pocketed parts the result
    is only a *proposal* and still requires drawing verification.
    """
    dims = sorted(dimensions)
    # Bnd_Box adds a small OCCT tolerance to each extreme, and STEP import
    # rounds the bounds. A nominal 50/10 plate is then reported as
    # 50.0000002/10.0000002 = 4.99999992: use a tight relative tolerance.
    plate_aspect_threshold = 5.0
    ratio_epsilon = 1e-5
    if dims[0] <= 0 or dims[1] / dims[0] < plate_aspect_threshold - ratio_epsilon:
        return None
    try:
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopoDS import topods
        from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_WIRE
        from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
        from OCC.Core.GeomAbs import GeomAbs_Plane
        from OCC.Core.GProp import GProp_GProps
        from OCC.Core.BRepGProp import brepgprop_SurfaceProperties, brepgprop_LinearProperties

        faces = []
        ex = TopExp_Explorer(solid, TopAbs_FACE)
        while ex.More():
            face = topods.Face(ex.Current())
            if BRepAdaptor_Surface(face).GetType() == GeomAbs_Plane:
                area_props = GProp_GProps()
                brepgprop_SurfaceProperties(face, area_props)
                area = float(area_props.Mass())
                if area > 1e-5:
                    faces.append((area, face))
            ex.Next()
        faces.sort(key=lambda f: f[0], reverse=True)
        if len(faces) < 2 or abs(faces[0][0] - faces[1][0]) > max(1e-4, faces[0][0] * 0.005):
            return None
        main_face = faces[0][1]
        wires = TopExp_Explorer(main_face, TopAbs_WIRE)
        contour = 0.0
        pierces = 0
        while wires.More():
            length = GProp_GProps()
            brepgprop_LinearProperties(topods.Wire(wires.Current()), length)
            linear_mm = float(length.Mass())
            if linear_mm <= 0 or not math.isfinite(linear_mm):
                return None
            contour += linear_mm
            pierces += 1
            wires.Next()
        if pierces < 1 or not math.isfinite(contour) or contour <= 0:
            return None
        return {"kind": "plate-outline", "thicknessMm": dims[0],
                "contourMm": contour, "pierces": pierces,
                "source": "main planar face of STEP B-Rep",
                "limitations": "Main face wires may differ from stock laser/plasma toolpath; verify 2D drawing."}
    except Exception as exc:
        # Measurement must not prevent mass/BOM computation. Diagnostics are
        # opt-in because most assemblies legitimately contain non-plate solids.
        import os
        if os.environ.get("DS_CAD_DEBUG_CUTTING_HINT") == "1":
            import traceback
            import sys
            print(f"[STEP cutting hint] {type(exc).__name__}: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        return None


def inventory(path, density=7850.0):
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.TopAbs import TopAbs_SOLID
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_VolumeProperties, brepgprop_SurfaceProperties
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib_Add

    if not math.isfinite(density) or density <= 0:
        raise ValueError("Density must be positive")
    # The deprecated pythonocc wrapper functions are still supported in the
    # pinned environment. Hundreds of repetitive warnings hide useful errors.
    warnings.filterwarnings("ignore", category=DeprecationWarning,
                            message=r"Call to deprecated function (brepgprop|brepbndlib)")
    timings = {}
    t_start = time.perf_counter()
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise RuntimeError("STEP read failed")
    timings["readStepSeconds"] = round(time.perf_counter()-t_start, 3)
    if not reader.TransferRoots():
        raise RuntimeError("STEP transfer failed")
    timings["transferStepSeconds"] = round(time.perf_counter()-t_start-timings["readStepSeconds"], 3)
    shape = reader.OneShape()
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = []
    originals = []
    original_centers = []
    original_dims = []
    original_signatures = []
    original_rigid_eligible = []
    original_mass = []
    index = ShapeCandidateIndex()
    occurrence_count = {}
    # Representatives alone are insufficient: tolerant Boolean equivalence is not transitive.
    # Track every accepted occurrence so a new rigid match cannot bridge
    # two mutually non-equivalent solids in the same geometry group.
    group_members = {}
    # Cache cheap necessary invariants once per occurrence, not once per pair.
    # Do not cache Boolean equivalence by fuzzy volume/bounds fingerprints.
    member_invariants = {}
    # Lazy OCCT cache; repeated parts otherwise recalculate face areas and inertia.
    rigid_geometry_cache = {}
    member_validation_seconds = 0.0
    member_validation_calls = 0
    member_validation_pairs = 0
    member_partner_skips = 0
    member_face_area_computations = 0
    member_validation_failures = 0
    member_validation_rejections = 0
    property_seconds = 0.0
    progress_interval = max(1, int(os.environ.get('DS_CAD_PROGRESS_EVERY', '25')))
    profile = os.environ.get('DS_CAD_PROFILE', '0') == '1'
    def matches_every_group_member(group_id, shape, shape_center, shape_volume, shape_signature, shape_dims):
        """Tolerance-based equivalence is not transitive: validate each occurrence."""
        nonlocal member_validation_seconds, member_validation_calls
        nonlocal member_validation_pairs, member_face_area_computations, member_partner_skips
        nonlocal member_validation_failures, member_validation_rejections
        validation_started = time.perf_counter()
        member_validation_calls += 1
        current_face_areas = None
        # Tolerance-based Boolean matches are NOT transitive. However, OCCT
        # IsPartner is exact TShape identity (location-independent). Once a
        # candidate has passed a two-way B-Rep check against one member, all
        # occurrences sharing that member's TShape need no additional Boolean.
        # Never substitute bounding boxes, face signatures or fuzzy hashes.
        proven_partner_shapes = [originals[group_id]]
        for member, member_center, member_volume in group_members.get(group_id, ()):
            # The caller already proved this exact representative against the
            # candidate. Do not repeat the same pair's expensive B-Rep Cuts.
            if member is originals[group_id]:
                continue
            if member.IsPartner(shape):
                continue
            # The caller has independently proved candidate == representative
            # by two-way B-Rep Cuts. IsPartner means the member uses the SAME
            # underlying OCCT TShape as that representative (possibly located
            # elsewhere). It cannot introduce a new geometric discrepancy:
            # avoid repeating expensive Boolean checks for that exact identity.
            # Never extend this shortcut to equal fingerprints or merely
            # tolerance-based matches: those are not transitive.
            if any(member.IsPartner(proven) for proven in proven_partner_shapes):
                member_partner_skips += 1
                continue
            member_validation_pairs += 1
            member_signature, member_dims, member_face_areas = member_invariants[id(member)]
            # Identical translated shapes necessarily have equal axis dimensions
            # and matching centroid-relative vertices. Skip costly OCCT Cuts
            # for impossible translations.
            can_translate = (
                shape_signature is not None and member_signature is not None
                and all(abs(a-b) <= 0.01 for a,b in zip(shape_dims, member_dims))
                and translation_signatures_match(shape_signature, member_signature)
            )
            if can_translate and equivalent_translation(
                    member, shape, member_center, shape_center, member_volume, shape_volume):
                proven_partner_shapes.append(member)
                continue
            # A rigid isometry preserves the multiset of individual face areas.
            # This is a rejection-only filter; a matching signature is NEVER
            # sufficient to group parts without independent B-Rep Cuts.
            if current_face_areas is None:
                current_face_areas = cached_face_area_signature(shape, rigid_geometry_cache)
                member_face_area_computations += 1
            if member_face_areas is None:
                member_face_areas = cached_face_area_signature(member, rigid_geometry_cache)
                member_invariants[id(member)] = (member_signature, member_dims, member_face_areas)
                member_face_area_computations += 1
            if member_face_areas is None or current_face_areas is None or len(member_face_areas) != len(current_face_areas):
                member_validation_rejections += 1
                member_validation_seconds += time.perf_counter() - validation_started
                return False
            if any(abs(a-b) > max(1e-6, max(a,b)*1e-7)
                   for a,b in zip(member_face_areas, current_face_areas)):
                member_validation_rejections += 1
                member_validation_seconds += time.perf_counter() - validation_started
                return False
            if not equivalent_rigid(member, shape, cache=rigid_geometry_cache):
                member_validation_failures += 1
                member_validation_seconds += time.perf_counter() - validation_started
                return False
            proven_partner_shapes.append(member)
        member_validation_seconds += time.perf_counter() - validation_started
        return True
    attempted_translation = 0
    translation_hits = 0
    skipped_translation = 0
    skipped_complex = 0
    skipped_degenerate = 0
    attempted_rigid = 0
    skipped_rigid = 0
    partner_hits = 0
    rigid_hits = 0
    rigid_filter_metrics = {}
    signature_seconds = 0.0
    translation_verification_seconds = 0.0
    rigid_verification_seconds = 0.0
    cutting_hint_seconds = 0.0
    candidate_pairs = 0
    max_translation_checks = max(0, int(os.environ.get("DS_CAD_MAX_TRANSLATION_CHECKS", "600")))
    # Two-way Cut increased translation cost; retain a bounded comparison budget.
    # This is not a correctness override; the independent regression gate remains active.
    max_translation_seconds = max(0.0, float(os.environ.get("DS_CAD_MAX_TRANSLATION_SECONDS", "140")))
    max_rigid_checks = max(0, int(os.environ.get("DS_CAD_MAX_RIGID_CHECKS", "120")))
    max_rigid_seconds = max(0.0, float(os.environ.get("DS_CAD_MAX_RIGID_SECONDS", "140")))
    compare_start = time.perf_counter()
    while explorer.More():
        solid = explorer.Current()
        property_started = time.perf_counter()
        vp, ap = GProp_GProps(), GProp_GProps()
        brepgprop_VolumeProperties(solid, vp)
        brepgprop_SurfaceProperties(solid, ap)
        volume = float(vp.Mass())
        if not math.isfinite(volume) or volume <= 0:
            raise ValueError(f"Invalid volume for solid {len(solids)+1}")
        bounds = Bnd_Box()
        brepbndlib_Add(solid, bounds)
        xmin,ymin,zmin,xmax,ymax,zmax = bounds.Get()
        dims = [xmax-xmin,ymax-ymin,zmax-zmin]
        # Volume/area only generate candidates. Never merge by fingerprints.
        area = float(ap.Mass())
        property_seconds += time.perf_counter() - property_started
        candidates = index.candidates(volume, area)
        candidate_pairs += len(candidates)
        existing = None
        method = "OCCT_UniqueShape"
        for i in candidates:
            if solid.IsPartner(originals[i]):
                existing = i
                method = "OCCT_IsPartner"
                partner_hits += 1
                break
        center = vp.CentreOfMass()
        signature = None
        rigid_eligible = None
        if existing is None:
            stage_start = time.perf_counter()
            signature = translation_signature(solid, center)
            signature_seconds += time.perf_counter() - stage_start
            for i in candidates:
                if any(abs(a-b) > 0.01 for a, b in zip(dims, original_dims[i])):
                    continue
                if signature is None or original_signatures[i] is None:
                    skipped_complex += 1
                    continue
                if not translation_signatures_match(signature, original_signatures[i]):
                    continue
                if (attempted_translation >= max_translation_checks or
                    translation_verification_seconds > max_translation_seconds):
                    skipped_translation += 1
                    continue
                attempted_translation += 1
                stage_start = time.perf_counter()
                equivalent = equivalent_translation(originals[i], solid, original_centers[i],
                                                    center, original_mass[i], volume)
                translation_verification_seconds += time.perf_counter() - stage_start
                if equivalent:
                    if not matches_every_group_member(i, solid, center, volume, signature, dims):
                        continue
                    existing = i
                    translation_hits += 1
                    method = "OCCT_Translation_BRep_TwoWayCut"
                    break
        if existing is None and candidates:
            rigid_eligible = has_unique_inertia_axes(vp)
            for i in candidates:
                if not rigid_eligible or not original_rigid_eligible[i]:
                    skipped_degenerate += 1
                    continue
                if (attempted_rigid >= max_rigid_checks or
                    rigid_verification_seconds > max_rigid_seconds):
                    skipped_rigid += 1
                    continue
                attempted_rigid += 1
                stage_start = time.perf_counter()
                equivalent = equivalent_rigid(originals[i], solid, metrics=rigid_filter_metrics, cache=rigid_geometry_cache)
                rigid_verification_seconds += time.perf_counter() - stage_start
                if equivalent:
                    if not matches_every_group_member(i, solid, center, volume, signature, dims):
                        continue
                    existing = i
                    rigid_hits += 1
                    method = "OCCT_Rigid_BRep_TwoWayCut"
                    break
        if existing is None:
            existing = len(originals)
            originals.append(solid)
            original_centers.append(center)
            original_dims.append(dims)
            if signature is None:
                stage_start = time.perf_counter()
                signature = translation_signature(solid, center)
                signature_seconds += time.perf_counter() - stage_start
            original_signatures.append(signature)
            original_rigid_eligible.append(rigid_eligible if rigid_eligible is not None else has_unique_inertia_axes(vp))
            original_mass.append(volume)
            index.insert(existing, volume, area)
        # Face-area multisets are expensive and unnecessary for partner/translation
        # matches. Materialize them only if rigid validation actually needs them.
        member_invariants[id(solid)] = (signature if signature is not None else translation_signature(solid, center),
                                        dims, None)
        group_members.setdefault(existing, []).append((solid, center, volume))
        occurrence_count[existing] = occurrence_count.get(existing, 0) + 1
        stage_start = time.perf_counter()
        cut_hint = planar_plate_cutting_hint(solid, dims)
        cutting_hint_seconds += time.perf_counter() - stage_start
        solids.append({
            "id": f"solid-{len(solids)+1}",
            "volumeMm3": volume,
            "areaMm2": area,
            "bboxMm": dims,
            "cuttingHint": cut_hint,
            "densityKgM3": density,
            "massKg": volume * density * 1e-9,
            "verifiedShapeKey": f"shared-tshape-{existing}",
            "verificationMethod": method,
        })
        explorer.Next()
        if profile and len(solids) % progress_interval == 0:
            print('[DS-CAD-PROGRESS] ' + json.dumps({
                'processedSolids': len(solids), 'uniqueGroups': len(originals),
                'elapsedSeconds': round(time.perf_counter()-t_start, 3),
                'shapePropertySeconds': round(property_seconds, 3),
                'signatureSeconds': round(signature_seconds, 3),
                'translationVerificationSeconds': round(translation_verification_seconds, 3),
                'rigidVerificationSeconds': round(rigid_verification_seconds, 3),
                'memberValidationSeconds': round(member_validation_seconds, 3),
                'memberValidationCalls': member_validation_calls,
                'memberValidationPairs': member_validation_pairs,
                'memberPartnerSkips': member_partner_skips,
                'cuttingHintSeconds': round(cutting_hint_seconds, 3)
            }), file=sys.stderr, flush=True)
    groups = [{"geometryId": f"shared-tshape-{i}", "quantity": count,
               "massKg": original_mass[i] * density * 1e-9}
              for i, count in occurrence_count.items()]
    timings["totalSeconds"] = round(time.perf_counter()-t_start, 3)
    timings["comparisonWindowSeconds"] = round(time.perf_counter()-compare_start, 3)
    diagnostics = {"candidatePairs": candidate_pairs,
                   "signatureSeconds": round(signature_seconds, 3),
                   "translationVerificationSeconds": round(translation_verification_seconds, 3),
                   "rigidVerificationSeconds": round(rigid_verification_seconds, 3),
                   "cuttingHintSeconds": round(cutting_hint_seconds, 3),
                   "shapePropertySeconds": round(property_seconds, 3),
                   "memberValidationSeconds": round(member_validation_seconds, 3),
                   "memberValidationFailures": member_validation_failures,
                   "memberValidationRejections": member_validation_rejections,
                   "memberValidationCalls": member_validation_calls,
                   "memberValidationPairs": member_validation_pairs,
                    "memberPartnerSkips": member_partner_skips,
                   "memberFaceAreaComputations": member_face_area_computations,
                   "translationChecks": attempted_translation,
                   "translationMatches": translation_hits,
                   "translationBudgetSkippedCandidates": skipped_translation,
                   "translationComplexitySkippedCandidates": skipped_complex,
                   "rigidDegenerateSkippedCandidates": skipped_degenerate,
                   "rigidChecks": attempted_rigid, "rigidMatches": rigid_hits,
                   "rigidBBoxRejectedOrientations": rigid_filter_metrics.get("bboxRejected", 0),
                   "rigidTwoWayCutAttempts": rigid_filter_metrics.get("twoWayCutAttempts", 0),
                   "partnerMatches": partner_hits, "rigidBudgetSkippedCandidates": skipped_rigid,
                   "uniqueGeometryGroups": len(groups), **timings}
    if os.environ.get("DS_CAD_PROFILE", "0") == "1":
        print("[DS-CAD-PROFILE] " + json.dumps(diagnostics), file=sys.stderr, flush=True)
    limitations = ["STEPControl does not preserve complete XCAF BOM metadata",
                   "Uniform density is an assumption; concrete, plastics and purchased parts need per-part material review",
                   "Cutting hints are proposals and require 2D drawing validation"]
    if skipped_translation or skipped_rigid or skipped_complex or skipped_degenerate:
        limitations.append(
            f"Some duplicates may remain ungrouped: translation budget={skipped_translation}, "
            f"complex B-Rep={skipped_complex}, degenerate rigid orientation={skipped_degenerate}, "
            f"rigid budget={skipped_rigid}. These are NOT verified duplicates.")
    return {"source": str(path), "solids": solids, "groups": groups, "count": len(solids),
            "totalMassKg": sum(x["massKg"] for x in solids),
            "matchingDiagnostics": diagnostics,
            "limitations": limitations}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("step", type=Path)
    p.add_argument("--density", type=float, default=7850.0)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    data = inventory(args.step, args.density)
    output = json.dumps(data, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)

if __name__ == "__main__":
    main()
