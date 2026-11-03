"""Independent two-direction Boolean proof for a newly grouped DockHub pair.

The previous pinned model (run 41546876622) placed STEP occurrences 247 and
267 into different geometry groups. The bounding-box filtered matcher (run
41560613405) grouped them. This test uses the ORIGINAL upstream STEP and
independent A\\B plus B\\A checks, not the production Common matcher.

It is an intentionally narrow audit: passing does not prove that every
other grouping in DockHub is correct.
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

    def props(shape):
        p = GProp_GProps()
        brepgprop_VolumeProperties(shape, p)
        c = p.CentreOfMass()
        m = p.MatrixOfInertia()
        tensor = np.array([[m.Value(i,j) for j in range(1,4)] for i in range(1,4)])
        _, axes = np.linalg.eigh(tensor)
        return p.Mass(), np.array([c.X(),c.Y(),c.Z()]), axes

    va, ca, axa = props(a)
    vb, cb, axb = props(b)
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
                print("DOCKHUB_PAIR_INDEPENDENT_CUT_PASS",
                      {"occurrences":[247,267],"volumesMm3":[va,vb],
                       "cutResidualsMm3":residuals,"thresholdMm3":threshold})
                return
    raise AssertionError("DockHub 247/267 cannot be independently verified by two B-Rep Cuts")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("step",type=Path)
    proof(parser.parse_args().step)
