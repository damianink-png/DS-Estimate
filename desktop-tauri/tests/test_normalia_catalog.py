"""Source-only nominal hardware catalogue regression; no OCCT installation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from cad_backend.normalia_catalog import normalia_catalog, catalog_summary, lookup_dimensions
from cad_backend.normalia_recognition import match_brep_signature


class NormaliaCatalogueTests(unittest.TestCase):
    def test_covers_seven_normalia_families_without_invented_purchase(self):
        info=catalog_summary()
        self.assertGreater(info['entries'],550)
        self.assertEqual(set(info['families']),
                         {'hex-head','socket-head','hex-nut','washer',
                          'dowel-pin','bearing','circlip'})
        rows=normalia_catalog()
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        self.assertTrue(all('dimensionsMm' in row and 'standard' in row
                            and row['status']=='nominal-catalogue-entry'
                            for row in rows))
        self.assertTrue(all(not row['geometricMatchingAvailable']
                            for row in rows if row['family']=='circlip'))
        self.assertTrue(all('price' not in row and 'manufacturingProcess' not in row
                            for row in rows))

    def test_common_real_iso_sizes(self):
        pairs=[
            ('washer',{'innerDiameter':8.4,'outerDiameter':16,'thickness':1.6},'M8'),
            ('washer',{'innerDiameter':10.5,'outerDiameter':20,'thickness':2},'M10'),
            ('bearing',{'innerDiameter':15,'outerDiameter':35,'width':11},'6202'),
            ('bearing',{'innerDiameter':17,'outerDiameter':40,'width':12},'6203'),
            ('hex-head',{'threadDiameter':8,'acrossFlats':13,'headHeight':5.3,'underheadLength':30},'M8x30'),
            ('socket-head',{'threadDiameter':6,'headDiameter':10,'headHeight':6,'underheadLength':25},'M6x25'),
            ('dowel-pin',{'diameter':6,'length':30},'6x30')
        ]
        for family,dims,expected in pairs:
            with self.subTest(family=family):
                names={r['designation'] for r in lookup_dimensions(family,dims)}
                self.assertIn(expected,names)

    def test_numeric_lookups_are_not_name_heuristics(self):
        self.assertEqual(lookup_dimensions('washer',{'innerDiameter':8.4,'outerDiameter':30,'thickness':1.6}),[])
        self.assertEqual(lookup_dimensions('washer',{'innerDiameter':float('nan')}),[])
        self.assertEqual(lookup_dimensions('washer',{'innerDiameter':True}),[])
        self.assertEqual(lookup_dimensions('washer',{}),[])
        self.assertEqual(lookup_dimensions('circlip',{'shaftDiameter':20}),[])

    def test_brep_family_signature_only_generates_candidates(self):
        ring=match_brep_signature({'family':'ring','innerDiameter':8.4,
                                   'outerDiameter':16,'axialLength':1.6})
        self.assertEqual([(r['family'],r['designation']) for r in ring],
                         [('washer','M8')])
        bearing=match_brep_signature({'family':'ring','innerDiameter':15,
                                      'outerDiameter':35,'axialLength':11})
        self.assertEqual([(r['family'],r['designation']) for r in bearing],
                         [('bearing','6202')])
        pin=match_brep_signature({'family':'pin','diameter':6,'axialLength':30})
        self.assertEqual([(r['family'],r['designation']) for r in pin],
                         [('dowel-pin','6x30')])
        nut=match_brep_signature({'family':'hex-nut','holeNominal':6,
                                  'acrossFlats':10,'axialLength':5.2})
        self.assertEqual([(r['family'],r['designation']) for r in nut],
                         [('hex-nut','M6')])
        self.assertEqual(match_brep_signature(
            {'family':'ring','innerDiameter':20,'outerDiameter':10,'axialLength':1.6}),[])
        self.assertEqual(match_brep_signature(
            {'family':'hex-nut','holeNominal':6,'acrossFlats':10,'axialLength':20}),[])


if __name__=='__main__':
    unittest.main()
