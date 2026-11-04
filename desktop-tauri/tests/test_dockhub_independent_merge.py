"""Independent two-direction Boolean audit of a disputed DockHub pair.

The previous pinned model (run 41546876622) placed STEP occurrences 247 and
267 into different geometry groups. The bounding-box filtered matcher (run
41560613405) grouped them. This test uses the ORIGINAL upstream STEP and
independent A\\B plus B\\A checks, not the production Common matcher.

The previous Common-only merge failed this independent audit. This regression
must reject that unproven merge; it does not certify every other DockHub pair.
"""
import argparse
import math
from itertools import permutations, product
from pathlib import Path

import numpy as np


def proof(step_path):
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_SOLID
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_VolumeProperties
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.gp import gp_Trsf
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib_Add

    reader = STEPControl_Reader()
    if reader.ReadFile(str(step_path)) != IFSelect_RetDone or not reader.TransferRoots():
        raise RuntimeError("Cannot load original DockHub STEP")
    exp = TopExp_Explorer(reader.OneShape(), TopAbs_SOLID)
    shapes = {}
    i = 0
    while exp.More() and len(shapes) < 2:
        i += 1
        if i in (247, 267):
            shapes[i] = exp.Current()
        exp.Next()
    if len(shapes) != 2:
        raise AssertionError("Missing source STEP solid 247 or 267")
    a, b = shapes[247], shapes[267]

    # Independent source-model health evidence. Do not silently heal the STEP:
    # a repair can change geometry and invalidate the pinned 247/267 comparison.
    from OCC.Core.BRepCheck import BRepCheck_Analyzer
    from OCC.Core.TopAbs import TopAbs_FACE, TopAbs_EDGE
    health = {}
    for occurrence, shape in ((247, a), (267, b)):
        def count_subshapes(kind):
            explorer = TopExp_Explorer(shape, kind)
            count = 0
            while explorer.More():
                count += 1
                explorer.Next()
            return count
        try:
            valid = bool(BRepCheck_Analyzer(shape).IsValid())
            health[str(occurrence)] = {
                "brepValid": valid,
                "isNull": bool(shape.IsNull()),
                "faces": count_subshapes(TopAbs_FACE),
                "edges": count_subshapes(TopAbs_EDGE),
            }
        except Exception as exc:
            health[str(occurrence)] = {"brepValid": None, "error": type(exc).__name__}
    print("DOCKHUB_SOURCE_BREP_HEALTH", health, flush=True)

    def props(shape):
        p = GProp_GProps()
        brepgprop_VolumeProperties(shape, p)
        c = p.CentreOfMass()
        m = p.MatrixOfInertia()
        tensor = np.array([[m.Value(i,j) for j in range(1,4)] for i in range(1,4)])
        moments, axes = np.linalg.eigh(tensor)
        return p.Mass(), np.array([c.X(),c.Y(),c.Z()]), axes, moments

    va, ca, axa, moments_a = props(a)
    vb, cb, axb, moments_b = props(b)
    print("DOCKHUB_SOURCE_INERTIA_SPECTRA", {
        "247": [float(x) for x in moments_a],
        "267": [float(x) for x in moments_b],
        "relativeDelta": [float(abs(x-y)/max(abs(x),abs(y),1e-12))
                          for x,y in zip(moments_a,moments_b)],
    }, flush=True)
    threshold = max(0.01**3, max(va,vb)*1e-6)
    if not math.isfinite(va) or not math.isfinite(vb) or abs(va-vb)>threshold:
        raise AssertionError("Volumes differ")
    for perm in permutations(range(3)):
        for signs in product((-1.,1.),repeat=3):
            basis = axb[:,perm] @ np.diag(signs)
            rotation = axa @ basis.T
            if np.linalg.det(rotation)<0.999999:
                continue
            t = ca - rotation@cb
            tr = gp_Trsf()
            tr.SetValues(float(rotation[0,0]),float(rotation[0,1]),float(rotation[0,2]),float(t[0]),
                         float(rotation[1,0]),float(rotation[1,1]),float(rotation[1,2]),float(t[1]),
                         float(rotation[2,0]),float(rotation[2,1]),float(rotation[2,2]),float(t[2]))
            moved = BRepBuilderAPI_Transform(b,tr,False).Shape()
            residuals = []
            for first,second in ((a,moved),(moved,a)):
                cut = BRepAlgoAPI_Cut(first,second)
                cut.SetNonDestructive(True)
                cut.Build()
                if not cut.IsDone():
                    residuals = []
                    break
                p = GProp_GProps()
                brepgprop_VolumeProperties(cut.Shape(),p)
                residuals.append(float(p.Mass()))
            if len(residuals)==2 and all(math.isfinite(x) and abs(x)<=threshold for x in residuals):
                raise AssertionError("DockHub 247/267 unexpectedly verified as equivalent; re-review the pinned grouping baseline")
    print("DOCKHUB_PAIR_NOT_VERIFIED_BY_TWO_WAY_CUT",
          {"occurrences":[247,267],"thresholdMm3":threshold,
           "note":"Common-only match must not be accepted; independent Cut proof unavailable"})


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("step",type=Path)
    parser.add_argument("--inventory", type=Path, help="Engine inventory to check against independent non-merge evidence")
    args = parser.parse_args()
    proof(args.step)
    if args.inventory:
        import json
        if not args.inventory.is_file():
            raise AssertionError(
                "UNVERIFIED: compiled engine inventory unavailable (e.g. ENGINE_TIMEOUT); "
                "source B-Rep check is not evidence that engine grouped the pair correctly")
        data = json.loads(args.inventory.read_text(encoding="utf-8"))
        solids = data["solids"]
        if len(solids) < 267:
            raise AssertionError("DockHub inventory missing audited occurrences")
        a = solids[246]["verifiedShapeKey"]
        b = solids[266]["verifiedShapeKey"]
        if a == b:
            raise AssertionError("DockHub 247/267 incorrectly grouped despite independent non-equivalence audit")
        print("DOCKHUB_ENGINE_GROUPS_INDEPENDENTLY_AUDITED", a, b)
