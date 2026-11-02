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
from pathlib import Path

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
        if existing is None:
            existing = len(originals)
            originals.append(solid)
        occurrence_count[existing] = occurrence_count.get(existing, 0) + 1
        solids.append({
            "id": f"solid-{len(solids)+1}",
            "volumeMm3": volume,
            "areaMm2": float(ap.Mass()),
            "bboxMm": dims,
            "densityKgM3": density,
            "massKg": volume * density * 1e-9,
            "verifiedShapeKey": f"shared-tshape-{existing}",
            "verificationMethod": "OCCT_IsPartner",
        })
        explorer.Next()
    groups = [{"geometryId": f"shared-tshape-{i}", "quantity": count, "massKg": solids[next(j for j, s in enumerate(solids) if s["verifiedShapeKey"] == f"shared-tshape-{i}")]["massKg"]} for i, count in occurrence_count.items()]
    return {"source": str(path), "solids": solids, "groups": groups, "count": len(solids),
            "totalMassKg": sum(x["massKg"] for x in solids),
            "limitations": ["STEPControl does not preserve complete XCAF BOM metadata",
                            "Distinct B-Rep solids with identical geometry are not yet verified",
                            "The UI is not yet wired to this Python backend"]}

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
