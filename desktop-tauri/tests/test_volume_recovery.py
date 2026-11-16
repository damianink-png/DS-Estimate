"""Regression: reverse orientation must not abort a physically valid solid."""
import sys, unittest, io, json
from pathlib import Path
from contextlib import redirect_stderr
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cad_backend.step_inventory import repair_volume, report_progress
try:
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCC.Core.TopoDS import TopoDS_Solid
except ImportError:
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.TopoDS import TopoDS_Solid

class VolumeRecovery(unittest.TestCase):
    def test_reversed_box(self):
        source=BRepPrimAPI_MakeBox(10,20,30).Solid()
        shape,props=repair_volume(source.Reversed())
        self.assertAlmostEqual(props.Mass(),6000)
        self.assertAlmostEqual(props.CentreOfMass().X(),5)
    def test_positive_box(self):
        _,props=repair_volume(BRepPrimAPI_MakeBox(10,20,30).Solid())
        self.assertAlmostEqual(props.Mass(),6000)
    def test_empty_solid_is_not_given_fake_mass(self):
        self.assertIsNone(repair_volume(TopoDS_Solid()))
    def test_progress_is_separate_json_line(self):
        stream=io.StringIO()
        with redirect_stderr(stream):report_progress('Pomiar',2025,3000,'Płyta\n10')
        lines=stream.getvalue().splitlines()
        self.assertEqual(len(lines),1)
        data=json.loads(lines[0].removeprefix('DS-CAD-UI '))
        self.assertEqual(data['current'],2025)
        self.assertEqual(data['name'],'Płyta\n10')

if __name__=='__main__':unittest.main()
