"""Conservative rigid B-Rep equivalence for STEP solids (pythonocc-core + numpy).

Uses OCCT volume inertia principal axes to propose proper rigid transforms.
Checks candidates with OCCT Common and Cut; never groups based on similar
volume/bounds alone. Returns False for ambiguous or failed geometry operations.
"""
from itertools import permutations, product
import numpy as np


def _properties(shape):
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_VolumeProperties
    props = GProp_GProps()
    brepgprop_VolumeProperties(shape, props)
    center = props.CentreOfMass()
    inertia = props.MatrixOfInertia()
    tensor = np.array([[inertia.Value(i, j) for j in range(1, 4)] for i in range(1, 4)], dtype=float)
    eigenvalues, axes = np.linalg.eigh(tensor)
    # Degenerate eigenvalues: orientation cannot be determined reliably.
    if min(abs(eigenvalues[i]-eigenvalues[j]) for i,j in ((0,1),(1,2),(0,2))) < max(1e-8, max(abs(eigenvalues))*1e-7):
        return props.Mass(), np.array([center.X(),center.Y(),center.Z()]), None
    return props.Mass(), np.array([center.X(),center.Y(),center.Z()]), axes


def equivalent_rigid(a, b, tolerance_mm=0.01, relative_volume_tol=1e-6):
    """True only when a rigid transform makes the solids materially equivalent."""
    from OCC.Core.gp import gp_Trsf
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_VolumeProperties

    try:
        va, ca, axa = _properties(a)
        vb, cb, axb = _properties(b)
        if va <= 0 or vb <= 0 or abs(va-vb) > max(tolerance_mm**3, max(va,vb)*relative_volume_tol):
            return False
        if a.IsPartner(b):
            return True
        if axa is None or axb is None:
            return False  # Symmetric/degenerate inertia: require a different verifier.
        threshold = max(tolerance_mm**3, max(va,vb)*relative_volume_tol)
        for perm in permutations(range(3)):
            for signs in product((-1.,1.), repeat=3):
                basis = axb[:,perm] @ np.diag(signs)
                rotation = axa @ basis.T
                if np.linalg.det(rotation) < 0.999999:
                    continue
                translation = ca - rotation @ cb
                t = gp_Trsf()
                t.SetValues(
                    float(rotation[0,0]),float(rotation[0,1]),float(rotation[0,2]),float(translation[0]),
                    float(rotation[1,0]),float(rotation[1,1]),float(rotation[1,2]),float(translation[1]),
                    float(rotation[2,0]),float(rotation[2,1]),float(rotation[2,2]),float(translation[2]))
                moved = BRepBuilderAPI_Transform(b,t,True).Shape()
                # Symmetric difference volume must be near zero in BOTH directions.
                differences = []
                for first,second in ((a,moved),(moved,a)):
                    cut = BRepAlgoAPI_Cut(first,second)
                    cut.Build()
                    if not cut.IsDone():
                        raise RuntimeError("B-Rep cut failed")
                    p = GProp_GProps()
                    brepgprop_VolumeProperties(cut.Shape(),p)
                    differences.append(abs(p.Mass()))
                if max(differences) <= threshold:
                    return True
    except Exception:
        return False
    return False
