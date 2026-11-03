"""Conservative rigid B-Rep equivalence for STEP solids (pythonocc-core + numpy).

Uses OCCT volume inertia principal axes to propose proper rigid transforms.
Checks candidates with OCCT Common; never groups based on similar
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


def has_unique_inertia_axes(props):
    """Cheap invariant gate: degenerate inertia cannot define principal axes.

    Such parts are still eligible for *translation* equivalence; they must
    not exhaust the expensive general rigid-match budget.
    """
    matrix = props.MatrixOfInertia()
    tensor = np.array([[matrix.Value(i, j) for j in range(1, 4)]
                       for i in range(1, 4)], dtype=float)
    eigenvalues = np.linalg.eigvalsh(tensor)
    if not np.all(np.isfinite(eigenvalues)):
        return False
    gap = min(abs(eigenvalues[0]-eigenvalues[1]),
              abs(eigenvalues[1]-eigenvalues[2]))
    return gap >= max(1e-8, max(abs(eigenvalues))*1e-7)


def translation_signature(shape, center, max_vertices=128):
    """Necessary (not sufficient) condition for translation-only equivalence.

    Coordinates relative to the volume centroid are sorted independently per
    axis. This is insensitive to STEP vertex traversal order and rounding-bin
    boundaries. A B-Rep Common check is STILL REQUIRED before merging.
    Very complex shapes are excluded from this fast path to bound OCCT time.
    """
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_VERTEX
    from OCC.Core.TopoDS import topods
    from OCC.Core.BRep import BRep_Tool

    xs, ys, zs = [], [], []
    explorer = TopExp_Explorer(shape, TopAbs_VERTEX)
    while explorer.More():
        if len(xs) >= max_vertices:
            return None
        point = BRep_Tool.Pnt(topods.Vertex(explorer.Current()))
        xs.append(point.X()-center.X())
        ys.append(point.Y()-center.Y())
        zs.append(point.Z()-center.Z())
        explorer.Next()
    return (tuple(sorted(xs)), tuple(sorted(ys)), tuple(sorted(zs)))


def translation_signatures_match(a, b, tolerance_mm=0.01):
    """Only reject impossible translations; never assert identity from signature."""
    if a is None or b is None:
        return False
    for va, vb in zip(a, b):
        if len(va) != len(vb) or any(abs(x-y) > tolerance_mm for x, y in zip(va, vb)):
            return False
    return True


def equivalent_translation(a, b, center_a, center_b, volume_a, volume_b,
                           tolerance_mm=0.01, relative_volume_tol=1e-6):
    """Verify pure translation by a REAL OCCT B-Rep Common volume operation.

    Handles symmetric fasteners/plates/cylinders for which inertia eigenvectors
    are degenerate and the general rigid matcher cannot determine orientation.
    One Common is symmetric: intersection must equal BOTH input volumes.
    This function must only run after cheap signature/complexity screening.
    """
    from OCC.Core.gp import gp_Trsf, gp_Vec
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_VolumeProperties

    if not (volume_a > 0 and volume_b > 0):
        return False
    threshold = max(tolerance_mm**3, max(volume_a, volume_b)*relative_volume_tol)
    if abs(volume_a-volume_b) > threshold:
        return False
    try:
        transform = gp_Trsf()
        transform.SetTranslation(gp_Vec(center_b, center_a))
        # A pure translation is a direct isometry. With copyGeom=False,
        # OCCT reuses the original geometry and changes only TopLoc_Location
        # rather than cloning every face/edge/curve of every STEP occurrence.
        # This is safe because Common below is read-only for the inputs.
        moved = BRepBuilderAPI_Transform(b, transform, False).Shape()
        common = BRepAlgoAPI_Common(a, moved)
        common.SetNonDestructive(True)
        common.Build()
        if not common.IsDone():
            return False
        properties = GProp_GProps()
        brepgprop_VolumeProperties(common.Shape(), properties)
        shared_volume = float(properties.Mass())
        return (np.isfinite(shared_volume) and shared_volume > 0
                and abs(volume_a-shared_volume) <= threshold
                and abs(volume_b-shared_volume) <= threshold
                and verify_two_way_cut(a, moved, volume_a, volume_b, threshold))
    except Exception:
        return False


def verify_two_way_cut(a, b, volume_a, volume_b, threshold):
    """Conservative second proof after a Common-volume candidate.

    An OCCT Common may report almost-full overlap for near-coincident but
    topologically distinct imported parts. Require BOTH directional residual
    volumes to be below the tolerance before merging inventory occurrences.
    Boolean failure is an UNKNOWN result, never proof of equivalence.
    """
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_VolumeProperties
    for left, right in ((a, b), (b, a)):
        try:
            cut = BRepAlgoAPI_Cut(left, right)
            cut.SetNonDestructive(True)
            cut.Build()
            if not cut.IsDone():
                return False
            props = GProp_GProps()
            brepgprop_VolumeProperties(cut.Shape(), props)
            residual = float(props.Mass())
            if not np.isfinite(residual) or abs(residual) > threshold:
                return False
        except Exception:
            return False
    return True


def equivalent_rigid(a, b, tolerance_mm=0.01, relative_volume_tol=1e-6, metrics=None):
    """Verify proper rigid equivalence with ONE B-Rep Common per orientation.

    For finite positive volumes, A\\B and B\\A are respectively volume(A)
    and volume(B) minus volume(A intersection B). Thus checking a Common
    volume against BOTH originals is equivalent to checking two Cut volumes,
    without computing two extra Boolean differences for every trial rotation.

    All signatures, inertia axes and transformed B-Rep bounds only reject
    impossible orientations; this function never accepts a pair without a
    real OCCT Boolean intersection. A failed or nonfinite Boolean result is
    NOT evidence of a match. The optional metrics dict tracks filter effects.
    """
    from OCC.Core.gp import gp_Trsf
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
    from OCC.Core.GProp import GProp_GProps
    from OCC.Core.BRepGProp import brepgprop_VolumeProperties
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib_Add

    def bounds(shape):
        # Failure to calculate a bounding box must never reject a match:
        # fall back to the original exact Boolean verifier.
        try:
            box = Bnd_Box()
            brepbndlib_Add(shape, box)
            return box.Get()
        except Exception:
            return None

    try:
        va, ca, axa = _properties(a)
        vb, cb, axb = _properties(b)
        if (not np.isfinite(va) or not np.isfinite(vb) or va <= 0 or vb <= 0):
            return False
        threshold = max(tolerance_mm**3, max(va, vb)*relative_volume_tol)
        if abs(va-vb) > threshold:
            return False
        if a.IsPartner(b):
            return True
        if axa is None or axb is None:
            return False  # Degenerate inertia handled by translation verifier.
        target_bounds = bounds(a)
        # An exact rigid match must have the same axis-aligned bounds AFTER
        # applying its proposed transform. This is a necessary condition,
        # not proof of identity. 0.05 mm + 1e-5*extent allows STEP tolerances.
        # Unlike a rotated source bounding-box shortcut, this measures the
        # actual transformed B-Rep, so it is safe for arbitrary orientations.
        if target_bounds is None:
            bounds_tolerance = None
        else:
            extent = max(target_bounds[i+3]-target_bounds[i] for i in range(3))
            bounds_tolerance = max(0.05, extent*1e-5, 2*tolerance_mm)
        for perm in permutations(range(3)):
            for signs in product((-1., 1.), repeat=3):
                basis = axb[:, perm] @ np.diag(signs)
                rotation = axa @ basis.T
                if np.linalg.det(rotation) < 0.999999:
                    continue
                translation = ca - rotation @ cb
                t = gp_Trsf()
                t.SetValues(
                    float(rotation[0, 0]), float(rotation[0, 1]), float(rotation[0, 2]), float(translation[0]),
                    float(rotation[1, 0]), float(rotation[1, 1]), float(rotation[1, 2]), float(translation[1]),
                    float(rotation[2, 0]), float(rotation[2, 1]), float(rotation[2, 2]), float(translation[2]))
                # A proper rigid isometry can be represented as a location.
                # False avoids cloning every face/edge of a STEP occurrence.
                moved = BRepBuilderAPI_Transform(b, t, False).Shape()
                if bounds_tolerance is not None:
                    candidate_bounds = bounds(moved)
                    if (candidate_bounds is not None and
                        any(abs(x-y) > bounds_tolerance
                            for x, y in zip(target_bounds, candidate_bounds))):
                        if metrics is not None:
                            metrics["bboxRejected"] = metrics.get("bboxRejected", 0) + 1
                        continue
                if metrics is not None:
                    metrics["commonAttempts"] = metrics.get("commonAttempts", 0) + 1
                common = BRepAlgoAPI_Common(a, moved)
                common.SetNonDestructive(True)
                common.Build()
                if not common.IsDone():
                    continue
                p = GProp_GProps()
                brepgprop_VolumeProperties(common.Shape(), p)
                shared = float(p.Mass())
                if (np.isfinite(shared) and shared > 0
                    and abs(va-shared) <= threshold
                    and abs(vb-shared) <= threshold):
                    if verify_two_way_cut(a, moved, va, vb, threshold):
                        return True
                    if metrics is not None:
                        metrics["commonOnlyRejected"] = metrics.get("commonOnlyRejected", 0) + 1
    except Exception:
        return False
    return False
