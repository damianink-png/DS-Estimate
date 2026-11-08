"""Original STEP XCAF part-name evidence — parser safety and CAD-first routing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cad_backend.part_name_evidence import parse_part_name,compare_name_to_geometry

SRC="XCAF occurrence/product"


class StepNameEvidenceTests(unittest.TestCase):
    def test_polish_english_and_german_hardware_names(self):
        names=[
            ("Śruba sześciokątna ISO 4017 M10x95","hex-head","M10x95"),
            ("DIN 912 socket head screw M6x25","socket-head","M6x25"),
            ("Nakrętka DIN 934 M12","hex-nut","M12"),
            ("Washer ISO 7089 M8","washer","M8"),
            ("Łożysko 6203","bearing","6203"),
            ("Schmiernippel DIN 71412 M6x1","grease-nipple","M6x1"),
            ("Seger DIN 471 20","circlip",None),
            ("Kołek walcowy Ø6x30 ISO 2338","dowel-pin",None),
            ("Schraube DIN 933 M8x40","hex-head","M8x40"),
            ("Hex bolt M12x50","hex-head","M12x50"),
        ]
        for name,family,size in names:
            with self.subTest(name=name):
                info=parse_part_name(name,SRC)
                self.assertIsNotNone(info)
                self.assertEqual(info.get("normaliaFamily"),family)
                self.assertEqual(info.get("nominalDesignation"),size)
                self.assertEqual(info["status"],"name-only-unverified")
                self.assertNotIn("route",info)
                self.assertNotIn("price",info)
                self.assertNotIn("manufacturingProcess",info)

    def test_stock_blank_names_are_clues_not_measured_geometry(self):
        cases=[
            ("Profil 40x40x2x1500","profile",[40,40,2,1500]),
            ("Płyta 100x200x10","plate",[100,200,10]),
            ("Rura Ø25x1,5x500","tube",[25,1.5,500]),
            ("Weldment Frame 20x20","weldment",[20,20]),
        ]
        for label,family,dims in cases:
            with self.subTest(label=label):
                info=parse_part_name(label,SRC)
                self.assertEqual(info.get("stockFamily"),family)
                self.assertEqual(info.get("nominalDimensionsMm"),dims)
                self.assertEqual(info.get("status"),"name-only-unverified")

    def test_exporter_placeholders_and_non_original_labels_are_ignored(self):
        for name in ("COMPOUND","SOLID","1.2","Open CASCADE STEP translator 7.8 1.2",
                     "STEP translator 7.8 1.2","Bez nazwy","=>[0:1]","M10x95"):
            with self.subTest(name=name):
                self.assertIsNone(parse_part_name(name,SRC))
        self.assertIsNone(parse_part_name("Śruba ISO 4017 M10x95","missing"))
        self.assertIsNone(parse_part_name("Śruba ISO 4017 M10x95","unknown"))
        self.assertIsNone(parse_part_name(None,SRC))

    def test_holes_for_fasteners_are_not_named_fasteners(self):
        for name in ("Otwór pod śrubę M10","Bolt hole M10",
                     "Hole for washer M8","Bohrung für Schraube M12",
                     "Gniazdo nakrętki M6"):
            with self.subTest(name=name):
                self.assertIsNone(parse_part_name(name,SRC))

    def test_contradicting_standard_does_not_pick_a_family(self):
        info=parse_part_name("Śruba ISO 4032 M12",SRC)
        self.assertIn("nameConflict",info)
        self.assertNotIn("normaliaFamily",info)
        self.assertEqual(info["nominalDesignation"],"M12")

    def test_name_correlates_but_never_replaces_geometry(self):
        geometry={
            "status":"geometry-candidate",
            "families":["hex-head"],
            "catalogCandidates":[{"designation":"M10x95","family":"hex-head"}]
        }
        for name in ("Śruba sześciokątna ISO 4017 M10x95",
                     "Schraube M10x95"):
            with self.subTest(name=name):
                info=parse_part_name(name,SRC)
                check=compare_name_to_geometry(info,geometry)
                self.assertEqual(check["status"],"corroborated")
        self.assertEqual(compare_name_to_geometry(
            parse_part_name("Śruba M10x90",SRC),geometry)["status"],"conflict")
        self.assertEqual(compare_name_to_geometry(
            parse_part_name("Nakrętka M10",SRC),geometry)["status"],"conflict")
        self.assertIsNone(compare_name_to_geometry(None,geometry))
        self.assertIsNone(compare_name_to_geometry(
            parse_part_name("Śruba M10x95",SRC),{"status":"unknown"}))

    def test_grease_nipple_pitch_cannot_be_confirmed_by_smooth_brep(self):
        geometry={
            "status":"geometry-candidate",
            "families":["grease-nipple"],
            "catalogCandidates":[{"designation":"M6x1, SW7 (only geometry-family match)"}],
        }
        info=parse_part_name("Smarowniczka DIN 71412 M6x1",SRC)
        check=compare_name_to_geometry(info,geometry)
        self.assertEqual(check["status"],"family-compatible")
        self.assertIn("not modelled",check["reason"])


if __name__=="__main__":
    unittest.main()
