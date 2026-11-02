"""OCCT regression: symmetric STEP shapes can be grouped after translation.

The fast signature is only a filter. Every positive result MUST come from a
real B-Rep Common intersection; dimensions/volume alone never merge solids.
Run inside the production pythonocc-core environment.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cad_backend"))
from rigid_match import (equivalent_translation, translation_signature,
                         translation_signatures_match, has_unique_inertia_axes)

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.gp import gp_Trsf, gp_Vec
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

    def test_complexity_gate_does_not_claim_identity(self):
        shape = BRepPrimAPI_MakeBox(20, 20, 20).Shape()
        self.assertIsNone(translation_signature(shape, props(shape).CentreOfMass(), max_vertices=4))
        self.assertFalse(translation_signatures_match(None, None))


if __name__ == "__main__":
    unittest.main()
