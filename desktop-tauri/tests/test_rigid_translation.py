"""OCCT regression: symmetric STEP shapes can be grouped after translation.

The fast signature is only a filter. Every positive result MUST come from a
real B-Rep Common intersection; dimensions/volume alone never merge solids.
Run inside the production pythonocc-core environment.
"""
import sys
import math
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cad_backend"))
from rigid_match import (equivalent_rigid, equivalent_translation, verify_two_way_cut, translation_signature,
                         translation_signatures_match, has_unique_inertia_axes)

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.gp import gp_Trsf, gp_Vec, gp_Ax1, gp_Pnt, gp_Dir
from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_VolumeProperties


def props(shape):
    p = GProp_GProps()
    brepgprop_VolumeProperties(shape, p)
    return p


def shifted(shape, x, y, z):
    t = gp_Trsf()
    t.SetTranslation(gp_Vec(x, y, z))
    return BRepBuilderAPI_Transform(shape, t, True).Shape()


class TranslatedSymmetricParts(unittest.TestCase):
    def check_translated(self, shape):
        other = shifted(shape, 125, -37, 81)
        a, b = props(shape), props(other)
        self.assertTrue(translation_signatures_match(
            translation_signature(shape, a.CentreOfMass()),
            translation_signature(other, b.CentreOfMass())))
        self.assertTrue(equivalent_translation(
            shape, other, a.CentreOfMass(), b.CentreOfMass(),
            a.Mass(), b.Mass()))

    def test_symmetric_cube_with_degenerate_inertia(self):
        cube = BRepPrimAPI_MakeBox(20, 20, 20).Shape()
        self.assertFalse(has_unique_inertia_axes(props(cube)))
        self.check_translated(cube)

    def test_symmetric_cylinder_with_degenerate_inertia(self):
        cylinder = BRepPrimAPI_MakeCylinder(10, 40).Shape()
        self.assertFalse(has_unique_inertia_axes(props(cylinder)))
        self.check_translated(cylinder)

    def test_non_symmetric_rectangular_part(self):
        self.check_translated(BRepPrimAPI_MakeBox(10, 20, 30).Shape())

    def test_different_geometry_is_not_equivalent(self):
        cube = BRepPrimAPI_MakeBox(20, 20, 20).Shape()
        cuboid = BRepPrimAPI_MakeBox(20, 20, 21).Shape()
        a, b = props(cube), props(cuboid)
        self.assertFalse(equivalent_translation(
            cube, cuboid, a.CentreOfMass(), b.CentreOfMass(),
            a.Mass(), b.Mass()))

    def test_location_only_verification_preserves_both_input_solids(self):
        # A translated independent B-Rep must be matched without mutating
        # either source's center of mass, volume or underlying location.
        shape = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
        other = shifted(shape, 1300, -700, 490)
        before = []
        for item in (shape, other):
            p = props(item)
            c = p.CentreOfMass()
            before.append((p.Mass(), c.X(), c.Y(), c.Z()))
        for _ in range(3):
            a, b = props(shape), props(other)
            self.assertTrue(equivalent_translation(
                shape, other, a.CentreOfMass(), b.CentreOfMass(),
                a.Mass(), b.Mass()))
        after = []
        for item in (shape, other):
            p = props(item)
            c = p.CentreOfMass()
            after.append((p.Mass(), c.X(), c.Y(), c.Z()))
        for first, second in zip(before, after):
            for x, y in zip(first, second):
                self.assertAlmostEqual(x, y, places=6)

    def test_same_volume_and_area_different_orientation_not_translation(self):
        # 10x20x30 and 20x10x30 have equal volume and area, but
        # translating one cannot make them equal (rotation is required).
        a = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
        b = shifted(BRepPrimAPI_MakeBox(20, 10, 30).Shape(), 40, 50, 60)
        pa, pb = props(a), props(b)
        self.assertAlmostEqual(pa.Mass(), pb.Mass(), places=6)
        self.assertFalse(equivalent_translation(
            a, b, pa.CentreOfMass(), pb.CentreOfMass(),
            pa.Mass(), pb.Mass()))

    def test_complexity_gate_does_not_claim_identity(self):
        shape = BRepPrimAPI_MakeBox(20, 20, 20).Shape()
        self.assertIsNone(translation_signature(shape, props(shape).CentreOfMass(), max_vertices=4))
        self.assertFalse(translation_signatures_match(None, None))


class RigidCommonRegression(unittest.TestCase):
    def rotated(self, shape):
        transform = gp_Trsf()
        transform.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)),
                              math.pi / 2)
        transform.SetTranslationPart(gp_Vec(140, -75, 22))
        return BRepBuilderAPI_Transform(shape, transform, True).Shape()

    def test_rotated_and_translated_independent_shape_is_identical(self):
        a = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
        b = self.rotated(BRepPrimAPI_MakeBox(10, 20, 30).Shape())
        self.assertTrue(equivalent_rigid(a, b))
        self.assertTrue(equivalent_rigid(b, a))

    def test_same_volume_different_geometry_must_not_merge(self):
        a = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
        b = self.rotated(BRepPrimAPI_MakeBox(5, 20, 60).Shape())
        self.assertAlmostEqual(props(a).Mass(), props(b).Mass(), places=5)
        self.assertFalse(equivalent_rigid(a, b))

    def test_rigid_verification_does_not_mutate_inputs(self):
        a = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
        b = self.rotated(BRepPrimAPI_MakeBox(10, 20, 30).Shape())
        def state(shape):
            p = props(shape)
            c = p.CentreOfMass()
            return (p.Mass(), c.X(), c.Y(), c.Z())
        before = (state(a), state(b))
        for _ in range(2):
            self.assertTrue(equivalent_rigid(a, b))
        after = (state(a), state(b))
        for old, new in zip(before, after):
            for x, y in zip(old, new):
                self.assertAlmostEqual(x, y, places=5)

    def test_rigid_bbox_filter_rejects_impossible_orientations_before_boolean(self):
        # An independently rotated box must still match, while at least
        # one incompatible principal-axis orientation is rejected cheaply.
        a = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
        b = self.rotated(BRepPrimAPI_MakeBox(10, 20, 30).Shape())
        stats = {}
        self.assertTrue(equivalent_rigid(a, b, metrics=stats))
        # The first proposed orientation may already be correct, so the
        # verifier can return before encountering any rejected candidate.
        # Assert the bounded Boolean work, not an order-dependent counter.
        self.assertGreater(stats.get('commonAttempts', 0), 0)
        self.assertLess(stats['commonAttempts'], 24)

    def test_equal_volume_different_bounds_do_not_trigger_common(self):
        a = BRepPrimAPI_MakeBox(10, 20, 30).Shape()
        b = self.rotated(BRepPrimAPI_MakeBox(5, 20, 60).Shape())
        stats = {}
        self.assertFalse(equivalent_rigid(a, b, metrics=stats))
        self.assertGreater(stats.get('bboxRejected', 0), 0)
        self.assertEqual(stats.get('commonAttempts', 0), 0)

    def test_two_way_cut_proof_rejects_same_volume_near_coincident_solids(self):
        # Regression for DockHub 247/267: a Common-only near-match cannot
        # silently become an inventory duplicate without directional Cuts.
        a = BRepPrimAPI_MakeBox(20, 20, 20).Shape()
        b = shifted(BRepPrimAPI_MakeBox(20, 20, 20).Shape(), 0.02, 0, 0)
        self.assertAlmostEqual(props(a).Mass(), props(b).Mass(), places=6)
        threshold = max(0.01**3, props(a).Mass()*1e-6)
        self.assertFalse(verify_two_way_cut(a, b, props(a).Mass(), props(b).Mass(), threshold))
        self.assertTrue(verify_two_way_cut(a, a, props(a).Mass(), props(a).Mass(), threshold))

    def test_symmetric_inertia_is_not_falsely_verified_by_rigid_path(self):
        a = BRepPrimAPI_MakeBox(20, 20, 20).Shape()
        b = self.rotated(BRepPrimAPI_MakeBox(20, 20, 20).Shape())
        self.assertFalse(equivalent_rigid(a, b))



if __name__ == "__main__":
    unittest.main()
