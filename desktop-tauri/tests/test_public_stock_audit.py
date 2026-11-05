"""Quick regression for public welded-frame STOCK audit, not CAD classification accuracy."""
import csv
import tempfile
import unittest
from pathlib import Path

from public_stock_audit import stock_audit, write_stock_csv


class PublicStockAuditTests(unittest.TestCase):
    def test_unknown_and_candidate_never_count_as_verified(self):
        inventory = {
            'count': 5,
            'solids': [
                {'id':'a','verifiedShapeKey':'g1','stockHint':{
                    'kind':'square-hollow','confidence':'cross-section-consistent',
                    'lengthMm':1000,'widthMm':40,'heightMm':40,'wallMm':2}},
                {'id':'b','verifiedShapeKey':'g2','stockHint':{
                    'kind':'plate-candidate','confidence':'candidate',
                    'thicknessMm':10}},
                {'id':'c','verifiedShapeKey':'g3','stockHint':{
                    'kind':'unknown','reason':'Cross-section changes along part'}},
                {'id':'d','verifiedShapeKey':'g4'},
                {'id':'e','verifiedShapeKey':'g5','stockHint':{
                    'kind':'round-tube','confidence':'cross-section-consistent',
                    'diameterMm':60,'wallMm':float('nan')}},
            ]
        }
        result=stock_audit(inventory)
        self.assertEqual(result['occurrences'],5)
        self.assertEqual(result['statusCounts'],{
            'CANDIDATE':1,'GEOMETRY_ONLY':1,'INVALID_HINT':1,'MISSING_HINT':1,'UNKNOWN':1})
        self.assertEqual(result['unresolvedOccurrences'],4)
        self.assertEqual(result['geometryEvidencePct'],20)
        self.assertEqual(result['rows'][2]['reason'],'Cross-section changes along part')
        self.assertIn('NOT accuracy proof',result['purpose'])

    def test_false_positive_profile_without_dimensions_rejected(self):
        result=stock_audit({'count':3,'solids':[
            {'id':'bad-shs','stockHint':{'kind':'square-hollow',
                'confidence':'cross-section-consistent','lengthMm':1000,
                'widthMm':40,'heightMm':40,'wallMm':25,'sectionAreaMm2':200}},
            {'id':'bad-tube','stockHint':{'kind':'round-tube',
                'confidence':'cross-section-consistent','diameterMm':30,
                'wallMm':2,'lengthMm':1000}},
            {'id':'good-tube','stockHint':{'kind':'round-tube',
                'confidence':'cross-section-consistent','diameterMm':30,
                'wallMm':2,'lengthMm':1000,'sectionAreaMm2':175.93}}
        ]})
        self.assertEqual(result['statusCounts']['INVALID_HINT'],2)
        self.assertEqual(result['statusCounts']['GEOMETRY_ONLY'],1)
        self.assertEqual(result['geometryEvidencePct'],33.3)

    def test_malformed_occurrence_inventory_rejected(self):
        with self.assertRaises(ValueError):
            stock_audit({'count':2,'solids':[{'id':'1'}]})
        with self.assertRaises(ValueError):
            stock_audit({'count':0,'solids':'not an array'})

    def test_csv_keeps_unknown_reason_and_part_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            report=stock_audit({'count':1,'solids':[{
                'id':'solid-8', 'verifiedShapeKey':'g-3',
                'stockHint':{'kind':'unknown','reason':'Unsupported UPN fillet'}}]})
            output=Path(folder)/'stock.csv'
            write_stock_csv(output,report['rows'])
            with output.open(encoding='utf-8-sig',newline='') as stream:
                row=next(csv.DictReader(stream))
                self.assertEqual(row['id'],'solid-8')
                self.assertEqual(row['verifiedShapeKey'],'g-3')
                self.assertEqual(row['kind'],'unknown')
                self.assertEqual(row['reason'],'Unsupported UPN fillet')


def run_suite():
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PublicStockAuditTests)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise AssertionError('Public stock audit regressions failed')


if __name__ == '__main__':
    run_suite()
