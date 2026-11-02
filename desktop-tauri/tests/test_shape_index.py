"""Standard library unit tests for the safe CAD signature candidate filter."""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'cad_backend'))
from shape_index import ShapeCandidateIndex


class ShapeCandidateTests(unittest.TestCase):
    def test_nearby_volumes_and_areas_are_candidates_but_not_proof(self):
        idx = ShapeCandidateIndex()
        idx.insert(0, 10000, 1500)
        idx.insert(1, 10001, 1500)
        self.assertEqual(idx.candidates(10000.002, 1500.001), [0])
        self.assertEqual(idx.candidates(50000, 1500), [])
        self.assertEqual(idx.candidates(10000, 2400), [])

    def test_rotation_does_not_affect_signature(self):
        idx = ShapeCandidateIndex()
        idx.insert(0, 780000, 22000)
        self.assertEqual(idx.candidates(780000, 22000), [0])

    def test_neighbor_buckets_avoid_edge_false_negatives(self):
        idx = ShapeCandidateIndex()
        scale = idx.scale
        border = math.exp((int(math.log(100000)*scale) + 0.49)/scale)
        idx.insert(0, border, 50000)
        nearby = border*(1+0.7e-6)
        self.assertIn(0, idx.candidates(nearby,50000))

    def test_reject_bad_measures_and_duplicate_groups(self):
        idx=ShapeCandidateIndex()
        for v,a in ((0,1),(1,0),(-1,1),(float('nan'),1),(1,float('inf'))):
            with self.assertRaises(ValueError):
                idx.insert(0,v,a)
        idx.insert(0,12,24)
        with self.assertRaises(ValueError):
            idx.insert(0,12,24)

if __name__=='__main__':
    unittest.main()
