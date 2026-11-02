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
try:
    from .rigid_match import equivalent_rigid
except ImportError:
    from rigid_match import equivalent_rigid
from pathlib import Path


def planar_plate_cutting_hint(solid, dimensions):
    """Conservative plate cut-loop measurements, not a raw-stock classifier.

    Looks for two similarly sized primary planar faces and takes outer+inner
    wire lengths from one primary face. Unsuitable B-Reps return None rather
    than fabricating a cutting contour. For machined/pocketed parts the result
    is only a *proposal* and still requires drawing verification.
    """
    dims = sorted(dimensions)
    if dims[0] <= 0 or dims[1] / dims[0] < 5:
        return None
    try:
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_WIRE
        from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
        from OCC.Core.GeomAbs import GeomAbs_Plane
        from OCC.Core.GProp import GProp_GProps
        from OCC.Core.BRepGProp import brepgprop_SurfaceProperties, brepgprop_LinearProperties

        faces = []
        ex = TopExp_Explorer(solid, TopAbs_FACE)
        while ex.More():
            face = ex.Current()
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
            brepgprop_LinearProperties(wires.Current(), length)
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
    except Exception:
        # Measurement must not prevent mass/BOM computation.
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
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone:
        raise RuntimeError("STEP read failed")
    if not reader.TransferRoots():
        raise RuntimeError("STEP transfer failed")
    shape = reader.OneShape()
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    solids = []
    originals = []
    occurrence_count = {}
    while explorer.More():
        solid = explorer.Current()
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
        # IsPartner tests shared TShape independent of TopLoc_Location.
        # No claim of equivalence for distinct B-Rep objects.
        existing = next((i for i, prev in enumerate(originals) if solid.IsPartner(prev)), None)
        method = "OCCT_IsPartner"
        if existing is None:
            for i, prev in enumerate(originals):
                if equivalent_rigid(prev, solid):
                    existing = i
                    method = "OCCT_Rigid_BRep_Cut"
                    break
        if existing is None:
            existing = len(originals)
            originals.append(solid)
        occurrence_count[existing] = occurrence_count.get(existing, 0) + 1
        cut_hint = planar_plate_cutting_hint(solid, dims)
        solids.append({
            "id": f"solid-{len(solids)+1}",
            "volumeMm3": volume,
            "areaMm2": float(ap.Mass()),
            "bboxMm": dims,
            "cuttingHint": cut_hint,
            "densityKgM3": density,
            "massKg": volume * density * 1e-9,
            "verifiedShapeKey": f"shared-tshape-{existing}",
            "verificationMethod": method,
        })
        explorer.Next()
    groups = [{"geometryId": f"shared-tshape-{i}", "quantity": count, "massKg": solids[next(j for j, s in enumerate(solids) if s["verifiedShapeKey"] == f"shared-tshape-{i}")]["massKg"]} for i, count in occurrence_count.items()]
    return {"source": str(path), "solids": solids, "groups": groups, "count": len(solids),
            "totalMassKg": sum(x["massKg"] for x in solids),
            "limitations": ["STEPControl does not preserve complete XCAF BOM metadata",
                            "Inertia-degenerate symmetric shapes may remain ungrouped; false negatives are possible",
                            "Cutting hints are proposals and require 2D drawing validation"]}

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
