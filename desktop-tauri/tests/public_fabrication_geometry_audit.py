"""Independent evidence for the reviewed public CAD baseline.

Does not call the production duplicate matcher. Checks every grouped EarthPress
occurrence against its representative with two Boolean differences, trying
proper centroid/inertia-axis alignments. StepGen mass uses a separate
STEPControl import, tighter integration and a full triangle-volume integral.
"""
import argparse
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / 'cad_backend'))
import cad_measure as cad
from assembly_names import load_occurrences
from human_assembly_benchmark import triangle_volume

try:
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCC.Core.gp import gp_Trsf
except ImportError:
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.gp import gp_Trsf


def properties(shape):
    p = cad.GProp_GProps()
    cad.volume_props(shape, p)
    center = np.array(p.CentreOfMass().Coord())
    matrix = p.MatrixOfInertia()
    _, axes = np.linalg.eigh([[matrix.Value(i, j) for j in range(1, 4)] for i in range(1, 4)])
    return float(p.Mass()), center, axes


def prove_pair(a, b, pa, pb):
    va, ca, axa = pa
    vb, cb, axb = pb
    threshold = max(1e-6, max(va, vb) * 1e-6)
    assert abs(va - vb) <= threshold, ('unequal volumes', va, vb)
    rotations = [np.eye(3)]
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1., 1.), repeat=3):
            rotation = axa @ (axb[:, perm] @ np.diag(signs)).T
            if np.linalg.det(rotation) > .999999:
                rotations.append(rotation)
    ba = cad.bounds(a)
    dims_a = np.array(ba[3:]) - ba[:3]
    for rotation in rotations:
        translation = ca - rotation @ cb
        transform = gp_Trsf()
        transform.SetValues(*[float(x) for row, t in zip(rotation, translation) for x in (*row, t)])
        moved = BRepBuilderAPI_Transform(b, transform, False).Shape()
        bb = cad.bounds(moved)
        if np.max(np.abs(dims_a - (np.array(bb[3:]) - bb[:3]))) > .01:
            continue
        residuals = []
        for first, second in ((a, moved), (moved, a)):
            difference = BRepAlgoAPI_Cut(first, second)
            difference.SetNonDestructive(True)
            difference.Build()
            if not difference.IsDone():
                break
            residuals.append(cad.volume(difference.Shape()))
        if len(residuals) == 2 and all(math.isfinite(v) and v <= threshold for v in residuals):
            return {'residualsMm3': residuals, 'thresholdMm3': threshold}
    raise AssertionError('No independent two-way Boolean proof for grouped occurrences')


def audit(root):
    folder = root / 'stepgen-frame'
    data = json.loads((folder / 'ds_estimate_inventory.json').read_text(encoding='utf8'))
    reader = cad.STEPControl_Reader()
    assert reader.ReadFile(str(folder / 'stepgen-frame.step')) == cad.IFSelect_RetDone
    assert reader.TransferRoots()
    shape = reader.OneShape()
    mesh_volume, triangles = triangle_volume(shape)
    mesh_mass = mesh_volume * 7850e-9
    tighter = cad.GProp_GProps()
    try:
        from OCC.Core.BRepGProp import brepgprop_VolumeProperties
        brepgprop_VolumeProperties(shape, tighter, 1e-9)
    except ImportError:
        from OCP.BRepGProp import BRepGProp
        BRepGProp.VolumeProperties_s(shape, tighter, Eps=1e-9)
    integrated_mass = float(tighter.Mass()) * 7850e-9
    program_mass = data['totalMassKg']
    assert abs(program_mass - integrated_mass) < .0001
    assert abs(program_mass - mesh_mass) / mesh_mass < .0001
    result = {'stepgen': {'programMassKg': program_mass, 'independentIntegralKg': integrated_mass,
                         'meshMassKg': mesh_mass, 'triangles': triangles}}
    folder = root / 'earthpress'
    data = json.loads((folder / 'ds_estimate_inventory.json').read_text(encoding='utf8'))
    occurrences = load_occurrences(folder / 'A-assembly.step')
    assert len(occurrences) == len(data['solids']) == 251
    groups = {}
    for i, row in enumerate(data['solids']):
        groups.setdefault(row['verifiedShapeKey'], []).append(i)
    shapes = [o['shape'] for o in occurrences]
    props = [properties(s) for s in shapes]
    proofs = []
    for key, indices in groups.items():
        first = indices[0]
        for second in indices[1:]:
            proof = prove_pair(shapes[first], shapes[second], props[first], props[second])
            proofs.append({'group': key, 'occurrences': [first + 1, second + 1], **proof})
        print('AUDIT_GROUP', key, len(indices), flush=True)
    result['earthpress'] = {'groups': len(groups), 'verifiedPairs': len(proofs), 'proofs': proofs}
    result['status'] = 'PASS'
    (root / 'independent_geometry_audit.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print(json.dumps({'status': 'PASS', 'stepgen': result['stepgen'],
                      'earthpress': {'groups': len(groups), 'verifiedPairs': len(proofs)}}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    audit(parser.parse_args().root)
